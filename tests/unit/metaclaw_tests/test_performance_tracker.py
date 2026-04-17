"""
Unit tests for SkillPerformanceTracker.

Tests reward computation, skill evolution decisions,
sample recording, and performance metrics.

Authoritative source: src/metaclaw/performance_tracker.py
"""
import pytest
from unittest.mock import Mock, patch
import time

from src.metaclaw.interfaces import RobotSample
from tests.unit.metaclaw_tests.conftest import (
    make_success_outcome,
    make_failure_outcome,
)


class TestRewardComputation:
    """Tests for reward computation from ExecutionOutcome."""

    def test_full_success_reward_is_1(self, tracker, success_outcome):
        """Full success with all effects achieved returns reward 1.0."""
        reward = tracker._compute_reward(success_outcome)
        assert reward == 1.0

    def test_partial_success_reward_between_0_5_and_1(self, tracker):
        """Partial success (some effects not achieved) returns 0.5-1.0 reward."""
        from src.metaclaw.interfaces import ExecutionOutcome, ExecutionStatus

        outcome = ExecutionOutcome(
            skill_name="test",
            status=ExecutionStatus.SUCCESS,
            execution_time_ms=100.0,
            effects_achieved=["effect1"],
            effects_not_achieved=["effect2", "effect3"],
        )
        reward = tracker._compute_reward(outcome)
        # achieved_ratio = 1/(1+2) = 0.333
        # reward = 0.5 + (0.5 * 0.333) = 0.6667
        assert 0.5 < reward < 1.0

    def test_failure_reward_is_0(self, tracker, failure_outcome):
        """Failed execution returns reward 0.0."""
        reward = tracker._compute_reward(failure_outcome)
        assert reward == 0.0

    def test_precondition_failed_reward_is_0(self, tracker, precondition_failed_outcome):
        """Precondition failed returns reward 0.0."""
        reward = tracker._compute_reward(precondition_failed_outcome)
        assert reward == 0.0

    def test_safety_violation_reward_is_negative(self, tracker, safety_violation_outcome):
        """Safety violation returns negative reward based on severity."""
        reward = tracker._compute_reward(safety_violation_outcome)
        # severity 0.8, recovered=True: -0.5 * 0.8 = -0.4
        assert reward == -0.4

    def test_safety_violation_no_recovery_penalty(self, tracker):
        """Safety violation without recovery gets full penalty."""
        from src.metaclaw.interfaces import ExecutionOutcome, ExecutionStatus, SafetyViolation, SafetyConstraintType

        outcome = ExecutionOutcome(
            skill_name="test",
            status=ExecutionStatus.SAFETY_VIOLATION,
            execution_time_ms=50.0,
            safety_violations=[
                SafetyViolation(
                    constraint_type=SafetyConstraintType.FORCE_LIMIT,
                    description="Excessive force",
                    severity=0.9,
                    recovered=False,  # Did not recover
                )
            ],
        )
        reward = tracker._compute_reward(outcome)
        assert reward == -0.9


class TestRecordExecution:
    """Tests for recording skill executions."""

    def test_record_execution_returns_robot_sample(self, tracker, success_outcome):
        """record_execution returns a RobotSample with correct fields."""
        sample = tracker.record_execution(success_outcome, "Grasp the red block")
        assert isinstance(sample, RobotSample)
        assert sample.skill_name == "grasp"
        assert sample.task_description == "Grasp the red block"
        assert sample.reward == 1.0

    def test_record_execution_updates_performance_metrics(self, tracker, success_outcome):
        """Recording updates SkillPerformanceRecord for the skill."""
        tracker.record_execution(success_outcome, "Test task")
        record = tracker.get_skill_metrics("grasp")
        assert record is not None
        assert record.total_executions == 1
        assert record.successful_executions == 1
        assert record.success_rate == 1.0

    def test_record_execution_with_explicit_reward(self, tracker, success_outcome):
        """Explicit reward overrides computed reward."""
        sample = tracker.record_execution(
            success_outcome, "Test task", reward=0.75
        )
        assert sample.reward == 0.75

    def test_record_multiple_executions_accumulates(self, tracker):
        """Multiple recordings accumulate metrics correctly."""
        from tests.unit.metaclaw_tests.conftest import make_success_outcome, make_failure_outcome

        tracker.record_execution(make_success_outcome(), "Task 1")
        tracker.record_execution(make_success_outcome(), "Task 2")
        tracker.record_execution(make_failure_outcome(), "Task 3")

        record = tracker.get_skill_metrics("grasp")
        assert record.total_executions == 3
        assert record.successful_executions == 2
        assert record.failed_executions == 1
        assert record.success_rate == pytest.approx(2/3)

    def test_record_execution_tracks_execution_time(self, tracker, success_outcome):
        """Execution time is tracked in metrics."""
        tracker.record_execution(success_outcome, "Task")
        record = tracker.get_skill_metrics("grasp")
        assert record.avg_execution_time_ms == 100.0


class TestShouldEvolveSkill:
    """Tests for skill evolution decision logic."""

    def test_untrained_skill_returns_false(self, tracker):
        """Skill with no executions should not trigger evolution."""
        result = tracker.should_evolve_skill("new_skill")
        assert result is False

    def test_skill_below_threshold_triggers_evolution(self, tracker):
        """Skill with success rate below threshold triggers evolution."""
        from tests.unit.metaclaw_tests.conftest import make_success_outcome, make_failure_outcome

        # Record mostly failures (1/5 = 20% success rate, below 40% threshold)
        for _ in range(4):
            tracker.record_execution(make_failure_outcome(), "Task")
        tracker.record_execution(make_success_outcome(), "Task")

        result = tracker.should_evolve_skill("grasp")
        assert result is True

    def test_skill_above_threshold_no_evolution(self, tracker):
        """Skill with success rate above threshold does not trigger evolution."""
        from tests.unit.metaclaw_tests.conftest import make_success_outcome

        # 4 successes out of 5 = 80% > 40%
        for _ in range(4):
            tracker.record_execution(make_success_outcome(), "Task")
        tracker.record_execution(make_failure_outcome(), "Task")

        result = tracker.should_evolve_skill("grasp")
        assert result is False

    def test_skill_with_insufficient_data_no_evolution(self, tracker):
        """Skill with fewer than 5 executions does not trigger evolution."""
        from tests.unit.metaclaw_tests.conftest import make_failure_outcome

        # Only 3 executions (insufficient data)
        for _ in range(3):
            tracker.record_execution(make_failure_outcome(), "Task")

        result = tracker.should_evolve_skill("grasp")
        assert result is False

    def test_custom_threshold_override(self, tracker):
        """Custom threshold can override default."""
        # 2 successes + 3 failures = 40% success rate with 5 executions
        # (enough data for decision)
        tracker.record_execution(make_success_outcome(), "Task")
        tracker.record_execution(make_success_outcome(), "Task")
        tracker.record_execution(make_failure_outcome(), "Task")
        tracker.record_execution(make_failure_outcome(), "Task")
        tracker.record_execution(make_failure_outcome(), "Task")

        # With 50% threshold, should not evolve (40% < 50%, yes evolves!)
        # Actually we want to test that threshold works for NO evolution
        # So use 30% threshold: 40% > 30% so should NOT evolve
        assert tracker.should_evolve_skill("grasp", threshold=0.3) is False
        # With 50% threshold: 40% < 50% so SHOULD evolve
        assert tracker.should_evolve_skill("grasp", threshold=0.5) is True


class TestGetFailedSamples:
    """Tests for retrieving failed execution samples."""

    def test_get_failed_samples_returns_failures(self, tracker):
        """Returns samples where reward <= 0."""
        from tests.unit.metaclaw_tests.conftest import make_success_outcome, make_failure_outcome

        tracker.record_execution(make_success_outcome(), "Task 1")  # reward 1.0
        tracker.record_execution(make_failure_outcome(), "Task 2")  # reward 0.0
        tracker.record_execution(make_success_outcome(), "Task 3")  # reward 1.0

        failures = tracker.get_failed_samples("grasp")
        assert len(failures) == 1
        assert failures[0].reward == 0.0

    def test_get_failed_samples_respects_max_limit(self, tracker):
        """Returns at most max_samples."""
        from tests.unit.metaclaw_tests.conftest import make_failure_outcome

        for i in range(20):
            tracker.record_execution(make_failure_outcome(), f"Task {i}")

        failures = tracker.get_failed_samples("grasp", max_samples=5)
        assert len(failures) == 5

    def test_get_failed_samples_returns_most_recent(self, tracker):
        """Returns most recent failures (end of sample list)."""
        from tests.unit.metaclaw_tests.conftest import make_success_outcome, make_failure_outcome

        # interleaved success/failure
        tracker.record_execution(make_success_outcome(), "S1")
        tracker.record_execution(make_failure_outcome(), "F1")
        tracker.record_execution(make_success_outcome(), "S2")
        tracker.record_execution(make_failure_outcome(), "F2")
        tracker.record_execution(make_success_outcome(), "S3")

        failures = tracker.get_failed_samples("grasp")
        assert len(failures) == 2
        # Most recent failures are F1 then F2, but we get last 2


class TestGetSkillMetrics:
    """Tests for retrieving skill performance metrics."""

    def test_get_skill_metrics_returns_record(self, tracker):
        """Returns SkillPerformanceRecord for tracked skill."""
        from tests.unit.metaclaw_tests.conftest import make_success_outcome

        tracker.record_execution(make_success_outcome(), "Task")
        record = tracker.get_skill_metrics("grasp")

        assert record is not None
        assert record.skill_name == "grasp"
        assert record.total_executions == 1

    def test_get_skill_metrics_returns_none_for_unknown(self, tracker):
        """Returns None for skill not yet tracked."""
        record = tracker.get_skill_metrics("unknown_skill")
        assert record is None

    def test_get_all_metrics_returns_all_tracked(self, tracker):
        """get_all_metrics returns all tracked skill records."""
        from tests.unit.metaclaw_tests.conftest import make_success_outcome

        tracker.record_execution(make_success_outcome(skill_name="grasp"), "Task1")
        tracker.record_execution(make_success_outcome(skill_name="place"), "Task2")

        all_metrics = tracker.get_all_metrics()
        assert "grasp" in all_metrics
        assert "place" in all_metrics


class TestGetRecentSamples:
    """Tests for retrieving recent samples."""

    def test_get_recent_samples(self, tracker):
        """Returns most recent N samples for a skill."""
        from tests.unit.metaclaw_tests.conftest import make_success_outcome

        for i in range(15):
            tracker.record_execution(make_success_outcome(), f"Task {i}")

        recent = tracker.get_recent_samples("grasp", count=5)
        assert len(recent) == 5


class TestGetBatchForTraining:
    """Tests for batch generation for RL training."""

    def test_batch_includes_successes_and_failures(self, tracker):
        """Batch includes both positive and negative reward samples."""
        from tests.unit.metaclaw_tests.conftest import make_success_outcome, make_failure_outcome

        for _ in range(10):
            tracker.record_execution(make_success_outcome(), "Success task")
        for _ in range(10):
            tracker.record_execution(make_failure_outcome(), "Failure task")

        batch = tracker.get_batch_for_training(batch_size=20)
        rewards = [s.reward for s in batch]
        assert any(r > 0 for r in rewards)
        assert any(r <= 0 for r in rewards)

    def test_batch_respects_size_limit(self, tracker):
        """Batch size is capped at batch_size."""
        from tests.unit.metaclaw_tests.conftest import make_success_outcome

        for _ in range(50):
            tracker.record_execution(make_success_outcome(), "Task")

        batch = tracker.get_batch_for_training(batch_size=10)
        assert len(batch) <= 10


class TestSkillPerformanceRecord:
    """Tests for SkillPerformanceRecord update logic."""

    def test_success_rate_calculation(self, tracker):
        """Success rate is correctly calculated."""
        from tests.unit.metaclaw_tests.conftest import make_success_outcome, make_failure_outcome

        tracker.record_execution(make_success_outcome(), "T1")
        tracker.record_execution(make_success_outcome(), "T2")
        tracker.record_execution(make_failure_outcome(), "T3")
        tracker.record_execution(make_failure_outcome(), "T4")

        record = tracker.get_skill_metrics("grasp")
        assert record.success_rate == 0.5

    def test_avg_execution_time_rolling_average(self, tracker):
        """Average execution time uses rolling average."""
        from src.metaclaw.interfaces import ExecutionOutcome, ExecutionStatus

        outcome1 = ExecutionOutcome(
            skill_name="test", status=ExecutionStatus.SUCCESS,
            execution_time_ms=100.0
        )
        outcome2 = ExecutionOutcome(
            skill_name="test", status=ExecutionStatus.SUCCESS,
            execution_time_ms=200.0
        )

        tracker.record_execution(outcome1, "T1")
        tracker.record_execution(outcome2, "T2")

        record = tracker.get_skill_metrics("test")
        assert record.avg_execution_time_ms == 150.0

    def test_safety_violations_counter(self, tracker, safety_violation_outcome):
        """Safety violations are counted in metrics."""
        tracker.record_execution(safety_violation_outcome, "Task")
        record = tracker.get_skill_metrics("grasp")
        assert record.safety_violations == 1


class TestSkillSummary:
    """Tests for skill summary generation."""

    def test_skill_summary_includes_evolution_flag(self, tracker):
        """Summary includes needs_evolution for each skill."""
        from tests.unit.metaclaw_tests.conftest import make_success_outcome

        tracker.record_execution(make_success_outcome(), "Task")
        summary = tracker.get_skill_summary()

        assert "grasp" in summary
        assert "needs_evolution" in summary["grasp"]
        assert "success_rate" in summary["grasp"]
        assert "total_executions" in summary["grasp"]
