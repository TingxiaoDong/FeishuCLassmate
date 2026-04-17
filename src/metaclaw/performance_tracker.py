"""
Skill Performance Tracker for MetaClaw integration.

Tracks execution metrics for each skill and provides data
for the skill evolution pipeline.
"""

import json
import logging
import time
from pathlib import Path
from typing import Optional

from src.metaclaw.interfaces import (
    ExecutionOutcome,
    ExecutionStatus,
    SkillPerformanceRecord,
    RobotSample,
)

logger = logging.getLogger(__name__)


class SkillPerformanceTracker:
    """
    Tracks skill performance metrics over time.

    Maintains:
    - Per-skill aggregated metrics
    - Raw execution samples for RL training
    - History for skill evolution decisions
    """

    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize the performance tracker.

        Args:
            storage_dir: Directory to persist performance data.
                        If None, data is not persisted.
        """
        self._storage_dir = Path(storage_dir) if storage_dir else None
        self._performance: dict[str, SkillPerformanceRecord] = {}
        self._samples: list[RobotSample] = []
        self._evolve_threshold = 0.4  # Success rate threshold for evolution

        if self._storage_dir:
            self._storage_dir.mkdir(parents=True, exist_ok=True)
            self._load_existing_data()

    def record_execution(
        self,
        outcome: ExecutionOutcome,
        task_description: str,
        reward: Optional[float] = None,
    ) -> RobotSample:
        """
        Record a skill execution outcome.

        Args:
            outcome: The execution outcome
            task_description: Description of the task
            reward: Optional explicit reward. If None, computed from outcome.

        Returns:
            RobotSample ready for MetaClaw training
        """
        # Compute reward if not provided
        if reward is None:
            reward = self._compute_reward(outcome)

        # Create sample for MetaClaw
        sample = RobotSample(
            task_description=task_description,
            skill_name=outcome.skill_name,
            outcome=outcome,
            reward=reward,
        )

        # Update aggregated metrics
        if outcome.skill_name not in self._performance:
            self._performance[outcome.skill_name] = SkillPerformanceRecord(
                skill_name=outcome.skill_name
            )
        self._performance[outcome.skill_name].update(outcome)

        # Store sample
        self._samples.append(sample)

        # Persist if storage dir configured
        if self._storage_dir:
            self._persist_sample(sample)
            self._persist_metrics()

        logger.info(
            f"[SkillPerformanceTracker] recorded execution: "
            f"skill={outcome.skill_name} status={outcome.status.value} reward={reward:.2f}"
        )

        return sample

    def _compute_reward(self, outcome: ExecutionOutcome) -> float:
        """
        Compute reward value from execution outcome.

        Reward structure:
        - 1.0: Full success
        - 0.5: Partial success (some effects achieved)
        - 0.0: Failure (precondition failed)
        - -1.0: Safety violation
        """
        if outcome.status == ExecutionStatus.SUCCESS:
            # Full success - check if all effects achieved
            if not outcome.effects_not_achieved:
                return 1.0
            else:
                # Partial success
                achieved_ratio = (
                    len(outcome.effects_achieved) /
                    (len(outcome.effects_achieved) + len(outcome.effects_not_achieved))
                )
                return 0.5 + (0.5 * achieved_ratio)

        elif outcome.status == ExecutionStatus.SAFETY_VIOLATION:
            # Safety violations are heavily penalized
            if outcome.safety_violations:
                max_severity = max(v.severity for v in outcome.safety_violations)
                # If robot recovered safely, reduce penalty
                if all(v.recovered for v in outcome.safety_violations):
                    return -0.5 * max_severity
                return -1.0 * max_severity
            return -0.5

        elif outcome.status == ExecutionStatus.PRECONDITION_FAILED:
            return 0.0

        else:  # FAILURE
            return 0.0

    def should_evolve_skill(self, skill_name: str, threshold: Optional[float] = None) -> bool:
        """
        Determine if a skill should be evolved based on recent performance.

        Args:
            skill_name: Name of the skill
            threshold: Optional override for success rate threshold

        Returns:
            True if skill success rate is below threshold
        """
        if threshold is None:
            threshold = self._evolve_threshold

        record = self._performance.get(skill_name)
        if record is None:
            return False

        if record.total_executions < 5:
            # Not enough data to decide
            return False

        return record.success_rate < threshold

    def get_failed_samples(self, skill_name: str, max_samples: int = 10) -> list[RobotSample]:
        """
        Get failed execution samples for a skill.

        Used by SkillEvolver to analyze failure patterns.

        Args:
            skill_name: Name of the skill
            max_samples: Maximum number of samples to return

        Returns:
            List of failed RobotSample objects
        """
        failed = [
            s for s in self._samples
            if s.skill_name == skill_name and s.reward <= 0
        ]
        # Return most recent failures
        return failed[-max_samples:]

    def get_skill_metrics(self, skill_name: str) -> Optional[SkillPerformanceRecord]:
        """Get performance metrics for a skill."""
        return self._performance.get(skill_name)

    def get_all_metrics(self) -> dict[str, SkillPerformanceRecord]:
        """Get metrics for all tracked skills."""
        return self._performance.copy()

    def get_recent_samples(self, skill_name: str, count: int = 10) -> list[RobotSample]:
        """Get most recent samples for a skill."""
        skill_samples = [s for s in self._samples if s.skill_name == skill_name]
        return skill_samples[-count:]

    def get_batch_for_training(self, batch_size: int = 32) -> list[RobotSample]:
        """
        Get a batch of samples for MetaClaw RL training.

        Returns samples with both successes and failures for balanced training.
        """
        successes = [s for s in self._samples if s.reward > 0]
        failures = [s for s in self._samples if s.reward <= 0]

        # Balance the batch
        half = batch_size // 2
        batch = []
        batch.extend(successes[-half:] if len(successes) >= half else successes)
        batch.extend(failures[-(batch_size - len(batch)):] if len(failures) >= (batch_size - len(batch)) else failures)

        # Shuffle
        import random
        random.shuffle(batch)

        return batch

    def _persist_sample(self, sample: RobotSample) -> None:
        """Persist a sample to disk."""
        if not self._storage_dir:
            return

        sample_file = self._storage_dir / "samples.jsonl"
        try:
            with open(sample_file, "a") as f:
                f.write(json.dumps(sample.to_dict()) + "\n")
        except Exception as e:
            logger.warning(f"[SkillPerformanceTracker] Failed to persist sample: {e}")

    def _persist_metrics(self) -> None:
        """Persist aggregated metrics to disk."""
        if not self._storage_dir:
            return

        metrics_file = self._storage_dir / "metrics.json"
        try:
            data = {
                name: record.to_dict()
                for name, record in self._performance.items()
            }
            with open(metrics_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"[SkillPerformanceTracker] Failed to persist metrics: {e}")

    def _load_existing_data(self) -> None:
        """Load existing data from storage directory."""
        if not self._storage_dir or not self._storage_dir.exists():
            return

        # Load metrics
        metrics_file = self._storage_dir / "metrics.json"
        if metrics_file.exists():
            try:
                with open(metrics_file) as f:
                    data = json.load(f)
                for name, record_dict in data.items():
                    record = SkillPerformanceRecord(
                        skill_name=record_dict["skill_name"],
                        total_executions=record_dict.get("total_executions", 0),
                        successful_executions=record_dict.get("successful_executions", 0),
                        failed_executions=record_dict.get("failed_executions", 0),
                        safety_violations=record_dict.get("safety_violations", 0),
                        avg_execution_time_ms=record_dict.get("avg_execution_time_ms", 0.0),
                        success_rate=record_dict.get("success_rate", 0.0),
                        last_execution_timestamp=record_dict.get("last_execution_timestamp", 0.0),
                    )
                    self._performance[name] = record
                logger.info(f"[SkillPerformanceTracker] Loaded {len(self._performance)} skill metrics")
            except Exception as e:
                logger.warning(f"[SkillPerformanceTracker] Failed to load metrics: {e}")

        # Load recent samples (limited to avoid memory issues)
        sample_file = self._storage_dir / "samples.jsonl"
        if sample_file.exists():
            try:
                with open(sample_file) as f:
                    lines = f.readlines()
                # Load last 1000 samples max
                for line in lines[-1000:]:
                    try:
                        data = json.loads(line)
                        # Reconstruct RobotSample would require outcome object
                        # For now, just track count
                    except json.JSONDecodeError:
                        continue
                logger.info(f"[SkillPerformanceTracker] Loaded sample history")
            except Exception as e:
                logger.warning(f"[SkillPerformanceTracker] Failed to load samples: {e}")

    def get_skill_summary(self) -> dict:
        """Get a summary of all tracked skills and their status."""
        summary = {}
        for skill_name, record in self._performance.items():
            should_evolve = self.should_evolve_skill(skill_name)
            summary[skill_name] = {
                "total_executions": record.total_executions,
                "success_rate": record.success_rate,
                "avg_execution_time_ms": record.avg_execution_time_ms,
                "safety_violations": record.safety_violations,
                "needs_evolution": should_evolve,
            }
        return summary
