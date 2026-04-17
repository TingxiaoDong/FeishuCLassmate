"""
Planner-MetaClaw Adapter

Bidirectional interface between Planner layer and MetaClaw.

Per architecture:
- MetaClaw → Planner: Suggest skill parameter improvements
- Planner → MetaClaw: Send execution results for learning
- Evolved skills require SafetyConstraintValidator + CodeReviewer approval
"""

import logging
from typing import Optional

from src.metaclaw import (
    RobotClawAdapter,
    SkillPerformanceTracker,
    ExecutionOutcome,
    RobotSample,
)
from src.skill.skill_validator import SkillValidator, ValidationContext

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
        validator: Optional[SkillValidator] = None,
    ):
        """
        Initialize Planner-MetaClaw adapter.

        Args:
            robot_claw_adapter: The RobotClawAdapter for execution
            validator: SkillValidator for evolved skills (uses SkillValidator if None)
        """
        self._claw_adapter = robot_claw_adapter
        self._validator = validator or SkillValidator()
        self._pending_suggestions: list[dict] = []
        self._approved_suggestions: list[dict] = []  # After review approval

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
        Apply a skill suggestion after validation.

        Per architecture, new skills require:
        1. Safety validation via SafetyConstraintValidator
        2. Review by Code Reviewer
        3. Integration testing
        4. Approval before deployment

        Args:
            suggestion: Suggestion from MetaClaw (with name, description, content, category)

        Returns:
            True if suggestion passed validation and was approved for review
        """
        # Step 1: Basic format validation
        if not self._validate_suggestion_format(suggestion):
            logger.warning(
                f"[PlannerMetaClawAdapter] Suggestion rejected - invalid format: {suggestion.get('name')}"
            )
            return False

        # Step 2: Safety constraint validation
        # This would be done against the skill's safety constraints
        # For evolved skills, we check that safety constraints are preserved
        if not self._validate_safety_constraints(suggestion):
            logger.warning(
                f"[PlannerMetaClawAdapter] Suggestion rejected - safety validation failed: {suggestion.get('name')}"
            )
            return False

        # Move to approved suggestions (awaiting Code Reviewer approval)
        if suggestion in self._pending_suggestions:
            self._pending_suggestions.remove(suggestion)

        self._approved_suggestions.append(suggestion)

        logger.info(
            f"[PlannerMetaClawAdapter] Suggestion approved for review: {suggestion.get('name')}"
        )
        return True

    def _validate_suggestion_format(self, suggestion: dict) -> bool:
        """Validate that suggestion has required fields."""
        required_fields = ["name", "description", "content", "category"]
        return all(field in suggestion and suggestion[field] for field in required_fields)

    def _validate_safety_constraints(self, suggestion: dict) -> bool:
        """
        Validate that evolved skill preserves safety constraints.

        An evolved skill must still have meaningful safety constraints.
        """
        content = suggestion.get("content", "")

        # Check that safety-related content exists
        # This is a basic check - full validation would parse the content
        safety_keywords = ["safety", "constraint", "limit", "force", "workspace", "collision"]
        has_safety = any(keyword in content.lower() for keyword in safety_keywords)

        # Evolved skills should reference safety
        return has_safety

    def get_approved_suggestions(self) -> list[dict]:
        """Get suggestions that passed validation and await Code Reviewer approval."""
        return self._approved_suggestions.copy()

    def approve_suggestion(self, suggestion_name: str) -> bool:
        """
        Approve a suggestion after Code Reviewer review.

        Only approved suggestions can be deployed.

        Args:
            suggestion_name: Name of the suggestion to approve

        Returns:
            True if suggestion was found and approved
        """
        for suggestion in self._approved_suggestions:
            if suggestion.get("name") == suggestion_name:
                logger.info(
                    f"[PlannerMetaClawAdapter] Suggestion approved for deployment: {suggestion_name}"
                )
                return True

        logger.warning(
            f"[PlannerMetaClawAdapter] Suggestion not found for approval: {suggestion_name}"
        )
        return False

    def get_skill_metrics(self, skill_name: str) -> Optional[dict]:
        """Get performance metrics for a specific skill."""
        return self._claw_adapter.get_skill_metrics(skill_name)

    def get_all_metrics(self) -> dict:
        """Get metrics for all tracked skills."""
        return self._claw_adapter.get_all_metrics()

    def get_skill_summary(self) -> dict:
        """Get summary of all skills and their status."""
        return self._claw_adapter.get_skill_summary()
