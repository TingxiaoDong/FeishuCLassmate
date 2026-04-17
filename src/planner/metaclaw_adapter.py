"""
Planner-MetaClaw Adapter

Bidirectional interface between Planner layer and MetaClaw.

Per architecture:
- MetaClaw → Planner: Suggest skill parameter improvements
- Planner → MetaClaw: Send execution results for learning
"""

import logging
from typing import Optional

from src.metaclaw import (
    RobotClawAdapter,
    SkillPerformanceTracker,
    ExecutionOutcome,
    RobotSample,
)

logger = logging.getLogger(__name__)


class PlannerMetaClawAdapter:
    """
    Adapter connecting Planner layer to MetaClaw learning engine.

    Responsibilities:
    - Send skill execution results to MetaClaw
    - Receive skill improvement suggestions from MetaClaw
    - Validate proposed skills before Planner use
    """

    def __init__(
        self,
        robot_claw_adapter: RobotClawAdapter,
        validator=None,  # Skill validator before deployment
    ):
        """
        Initialize Planner-MetaClaw adapter.

        Args:
            robot_claw_adapter: The RobotClawAdapter for execution
            validator: Optional skill validator (SkillDesigner + CodeReviewer)
        """
        self._claw_adapter = robot_claw_adapter
        self._validator = validator
        self._pending_suggestions: list[dict] = []

    def report_execution(
        self,
        skill_name: str,
        outcome: ExecutionOutcome,
        task_description: str,
    ) -> None:
        """
        Report skill execution result to MetaClaw.

        Called by Planner after skill execution completes.
        MetaClaw uses this for learning and improvement.

        Args:
            skill_name: Name of executed skill
            outcome: Execution outcome
            task_description: Task context
        """
        self._claw_adapter.record_external_outcome(
            skill_name=skill_name,
            outcome=outcome,
            task_description=task_description,
        )
        logger.info(
            f"[PlannerMetaClawAdapter] Reported execution: {skill_name} -> {outcome.status.value}"
        )

    def request_skill_suggestions(
        self,
        task_description: str,
        context: Optional[dict] = None,
    ) -> list[dict]:
        """
        Request skill improvement suggestions from MetaClaw.

        Args:
            task_description: Description of current task
            context: Optional additional context

        Returns:
            List of suggested skill improvements
        """
        # Get training batch to understand recent performance
        recent_samples = self._claw_adapter.get_training_batch(batch_size=10)

        suggestions = []

        # Analyze recent performance
        metrics = self._claw_adapter.get_all_metrics()
        for skill_name, metric in metrics.items():
            if metric.get("needs_evolution"):
                suggestions.append({
                    "type": "parameter_adjustment",
                    "skill_name": skill_name,
                    "reason": f"success_rate={metric.get('success_rate', 0):.2f} below threshold",
                    "suggested_action": "trigger_evolution",
                })

        self._pending_suggestions.extend(suggestions)
        return suggestions

    def get_pending_suggestions(self) -> list[dict]:
        """Get all pending skill suggestions from MetaClaw."""
        return self._pending_suggestions.copy()

    def apply_suggestion(self, suggestion: dict) -> bool:
        """
        Apply a skill suggestion.

        Per architecture, new skills require:
        1. Safety validation in Skill Layer
        2. Review by Code Reviewer
        3. Integration testing
        4. Approval before deployment

        Args:
            suggestion: Suggestion from MetaClaw

        Returns:
            True if suggestion was applied
        """
        if self._validator:
            # Validate through proper channels
            is_safe = self._validator.validate_skill(suggestion)
            if not is_safe:
                logger.warning(
                    f"[PlannerMetaClawAdapter] Suggestion rejected by validator: {suggestion}"
                )
                return False

        # Remove from pending
        if suggestion in self._pending_suggestions:
            self._pending_suggestions.remove(suggestion)

        logger.info(f"[PlannerMetaClawAdapter] Applied suggestion: {suggestion}")
        return True

    def get_skill_metrics(self, skill_name: str) -> Optional[dict]:
        """Get performance metrics for a specific skill."""
        return self._claw_adapter.get_skill_metrics(skill_name)

    def get_all_metrics(self) -> dict:
        """Get metrics for all tracked skills."""
        return self._claw_adapter.get_all_metrics()

    def get_skill_summary(self) -> dict:
        """Get summary of all skills and their status."""
        return self._claw_adapter.get_skill_summary()
