"""
RobotClawAdapter - Bridge between MetaClaw and the Robot Control System.

This adapter enables MetaClaw's continual learning framework to:
1. Receive robot execution outcomes for experience replay
2. Trigger skill evolution when performance degrades
3. Update skill parameters based on learned policies

MetaClaw's role is LEARNING, not direct robot control.
All execution still flows through the Robot API layer.
"""

import logging
import os
from typing import Optional, Callable

from src.robot_api.robot_api import RobotAPI
from src.metaclaw.skill_executor import SkillExecutor
from src.metaclaw.performance_tracker import SkillPerformanceTracker
from src.metaclaw.interfaces import ExecutionOutcome, RobotSample

logger = logging.getLogger(__name__)


class RobotClawAdapter:
    """
    Meta-level controller bridging MetaClaw with robot execution.

    This adapter does NOT execute robot commands directly.
    It coordinates the learning pipeline around the SkillExecutor.
    """

    def __init__(
        self,
        robot_api: RobotAPI,
        skill_executor: SkillExecutor,
        performance_tracker: SkillPerformanceTracker,
        skill_manager=None,  # MetaClaw's SkillManager
        skill_evolver=None,   # MetaClaw's SkillEvolver
        memory_manager=None,   # MetaClaw's MemoryManager
        evolve_threshold: float = 0.4,
    ):
        """
        Initialize RobotClawAdapter.

        Args:
            robot_api: RobotAPI instance for execution
            skill_executor: SkillExecutor for validated skill execution
            performance_tracker: Tracks skill performance
            skill_manager: MetaClaw SkillManager (optional)
            skill_evolver: MetaClaw SkillEvolver (optional)
            memory_manager: MetaClaw MemoryManager (optional)
            evolve_threshold: Success rate below which to trigger evolution
        """
        self._robot_api = robot_api
        self._skill_executor = skill_executor
        self._performance_tracker = performance_tracker
        self._skill_manager = skill_manager
        self._skill_evolver = skill_evolver
        self._memory_manager = memory_manager
        self._evolve_threshold = evolve_threshold

        # Callbacks for skill evolution
        self._on_skill_evolved: Optional[Callable] = None

        # Track evolution state
        self._evolution_in_progress = False
        self._last_evolution_time = 0.0

    def execute_skill(
        self,
        skill_name: str,
        parameters: dict,
        task_description: str = "",
    ) -> ExecutionOutcome:
        """
        Execute a skill with full tracking for MetaClaw learning.

        This is the main entry point for skill execution.
        All outcomes are recorded for learning.

        Args:
            skill_name: Name of skill to execute
            parameters: Skill parameters
            task_description: Task context for learning

        Returns:
            ExecutionOutcome with full details
        """
        # Execute via SkillExecutor (validates preconditions, checks safety)
        outcome = self._skill_executor.execute(
            skill_name=skill_name,
            parameters=parameters,
            task_description=task_description,
        )

        # Record outcome for learning
        self._performance_tracker.record_execution(
            outcome=outcome,
            task_description=task_description,
        )

        # Check if skill needs evolution
        if self._should_trigger_evolution(skill_name):
            self._trigger_skill_evolution(skill_name)

        return outcome

    def _should_trigger_evolution(self, skill_name: str) -> bool:
        """Check if skill evolution should be triggered."""
        if self._skill_evolver is None:
            return False

        if self._evolution_in_progress:
            return False

        return self._performance_tracker.should_evolve_skill(
            skill_name,
            threshold=self._evolve_threshold,
        )

    def _trigger_skill_evolution(self, skill_name: str) -> None:
        """
        Trigger skill evolution via MetaClaw's SkillEvolver.

        This analyzes failed samples and generates improved skills.
        """
        import time

        if self._evolution_in_progress:
            return

        self._evolution_in_progress = True
        logger.info(f"[RobotClawAdapter] Triggering skill evolution for: {skill_name}")

        try:
            # Get failed samples for analysis
            failed_samples = self._performance_tracker.get_failed_samples(skill_name)

            if not failed_samples:
                logger.info(f"[RobotClawAdapter] No failed samples for {skill_name}, skipping evolution")
                return

            # Get current skills from MetaClaw
            current_skills = {}
            if self._skill_manager:
                current_skills = self._skill_manager.skills

            # Run evolution
            if hasattr(self._skill_evolver, 'evolve'):
                # Run async evolution in a sync context
                import asyncio
                loop = asyncio.new_event_loop()
                try:
                    new_skills = loop.run_until_complete(
                        self._skill_evolver.evolve(failed_samples, current_skills)
                    )
                finally:
                    loop.close()

                if new_skills and self._skill_manager:
                    # Add evolved skills
                    self._skill_manager.add_skills(new_skills)
                    logger.info(
                        f"[RobotClawAdapter] Added {len(new_skills)} evolved skills: "
                        f"{[s.get('name') for s in new_skills]}"
                    )

                    # Fire callback
                    if self._on_skill_evolved:
                        self._on_skill_evolved(skill_name, new_skills)

                self._last_evolution_time = time.time()
        except Exception as e:
            logger.error(f"[RobotClawAdapter] Skill evolution failed: {e}", exc_info=True)
        finally:
            self._evolution_in_progress = False

    def set_on_skill_evolved(self, callback: Callable) -> None:
        """Set callback to be called when a skill is evolved."""
        self._on_skill_evolved = callback

    def get_skill_metrics(self, skill_name: str) -> Optional[dict]:
        """Get performance metrics for a skill."""
        record = self._performance_tracker.get_skill_metrics(skill_name)
        return record.to_dict() if record else None

    def get_all_metrics(self) -> dict:
        """Get metrics for all skills."""
        return {
            name: record.to_dict()
            for name, record in self._performance_tracker.get_all_metrics().items()
        }

    def get_training_batch(self, batch_size: int = 32) -> list[RobotSample]:
        """Get a batch of samples for MetaClaw RL training."""
        return self._performance_tracker.get_batch_for_training(batch_size)

    def record_external_outcome(
        self,
        skill_name: str,
        outcome: ExecutionOutcome,
        task_description: str,
    ) -> None:
        """
        Record an execution outcome from an external source.

        Useful when the skill was executed outside this adapter
        but we still want to track it for learning.
        """
        self._performance_tracker.record_execution(
            outcome=outcome,
            task_description=task_description,
        )

        if self._should_trigger_evolution(skill_name):
            self._trigger_skill_evolution(skill_name)

    def validate_skill(self, skill_name: str, parameters: dict) -> tuple[bool, list[str], list[str]]:
        """
        Validate skill preconditions without executing.

        Returns:
            Tuple of (all_valid, satisfied_preconditions, failed_preconditions)
        """
        return self._skill_executor.validate_only(skill_name, parameters)

    def get_skill_summary(self) -> dict:
        """Get summary of all skills and their status."""
        return self._performance_tracker.get_skill_summary()

    @property
    def is_evolution_in_progress(self) -> bool:
        """Check if skill evolution is currently running."""
        return self._evolution_in_progress


def create_robot_claw_adapter(
    robot_api: RobotAPI,
    metaclaw_skill_manager=None,
    metaclaw_skill_evolver=None,
    metaclaw_memory_manager=None,
    storage_dir: Optional[str] = None,
) -> RobotClawAdapter:
    """
    Factory function to create a fully configured RobotClawAdapter.

    Args:
        robot_api: RobotAPI instance
        metaclaw_skill_manager: MetaClaw SkillManager (optional)
        metaclaw_skill_evolver: MetaClaw SkillEvolver (optional)
        metaclaw_memory_manager: MetaClaw MemoryManager (optional)
        storage_dir: Directory for persisting performance data

    Returns:
        Configured RobotClawAdapter instance
    """
    # Create skill executor
    skill_executor = SkillExecutor(robot_api)

    # Create performance tracker
    performance_tracker = SkillPerformanceTracker(storage_dir=storage_dir)

    # Create adapter
    adapter = RobotClawAdapter(
        robot_api=robot_api,
        skill_executor=skill_executor,
        performance_tracker=performance_tracker,
        skill_manager=metaclaw_skill_manager,
        skill_evolver=metaclaw_skill_evolver,
        memory_manager=metaclaw_memory_manager,
    )

    return adapter
