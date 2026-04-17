"""
MetaClaw Shadow Mode - Observational learning without robot impact.

Shadow mode observes execution trajectories, analyzes patterns,
and generates skill candidate suggestions for human review.

Key principles:
- READ-only: No robot commands sent
- ANALYZE: Pattern detection, success/failure analysis
- SUGGEST: Generate candidates for human review
- NO execution: All suggestions are stored, not deployed
"""

import logging
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Optional

from src.skill.skill_schemas import SKILL_REGISTRY, SkillType
from backend.db.database import get_trajectories

logger = logging.getLogger(__name__)


class MetaClawShadowMode:
    """
    Shadow mode for MetaClaw - observes and suggests, never executes.

    Analyzes stored trajectories to:
    - Detect execution patterns
    - Identify common failure modes
    - Generate skill improvement candidates
    - Suggest new composite skills
    """

    # Thresholds for candidate generation
    MIN_SUCCESS_RATE_FOR_PATTERN = 0.6
    MIN_FAILURE_COUNT_FOR_analysis = 3
    COMPOSITE_SEQUENCE_MIN_OCCURRENCES = 5

    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize Shadow Mode.

        Args:
            storage_dir: Directory to store candidate skills for review
        """
        self._storage_dir = storage_dir
        self._candidate_skills: list[dict] = []
        self._load_candidates()

    async def analyze_trajectories(self, limit: int = 100) -> dict:
        """
        Analyze recent trajectories for patterns.

        Args:
            limit: Maximum number of trajectories to analyze

        Returns:
            Analysis results with patterns, success rates, failure modes
        """
        trajectories = await get_trajectories(limit=limit)

        if not trajectories:
            return {
                "summary": "No trajectories found",
                "total_trajectories": 0,
                "patterns": [],
                "success_rates": {},
                "failure_modes": [],
            }

        # Aggregate analysis
        analysis = {
            "total_trajectories": len(trajectories),
            "analyzed_at": datetime.utcnow().isoformat(),
            "patterns": self._detect_patterns(trajectories),
            "success_rates": self._compute_success_rates(trajectories),
            "failure_modes": self._identify_failure_modes(trajectories),
            "skill_sequences": self._analyze_skill_sequences(trajectories),
            "common_tasks": self._analyze_common_tasks(trajectories),
        }

        # Add summary statistics
        successful = sum(1 for t in trajectories if t.get("final_result", {}).get("success", False))
        analysis["overall_success_rate"] = successful / len(trajectories) if trajectories else 0.0

        logger.info(
            f"[MetaClawShadowMode] Analyzed {len(trajectories)} trajectories, "
            f"found {len(analysis['patterns'])} patterns, "
            f"overall success rate: {analysis['overall_success_rate']:.2%}"
        )

        return analysis

    async def generate_skill_candidates(self) -> list[dict]:
        """
        Generate candidate skill suggestions based on trajectory analysis.

        Returns:
            List of candidate skills for human review (NOT executed)
        """
        analysis = await self.analyze_trajectories()

        if analysis["total_trajectories"] == 0:
            return []

        candidates = []

        # Generate candidates from successful patterns
        for pattern in analysis.get("patterns", []):
            if pattern.get("type") == "sequence" and pattern.get("success_rate", 0) >= self.MIN_SUCCESS_RATE_FOR_PATTERN:
                candidate = self._create_composite_candidate(pattern, analysis)
                if candidate:
                    candidates.append(candidate)

        # Generate candidates from common failure modes
        for failure in analysis.get("failure_modes", []):
            if failure.get("count", 0) >= self.MIN_FAILURE_COUNT_FOR_analysis:
                candidate = self._create_failure_recovery_candidate(failure, analysis)
                if candidate:
                    candidates.append(candidate)

        # Add optimization candidates for low-success-rate skills
        for skill_name, stats in analysis.get("success_rates", {}).items():
            if stats.get("success_rate", 1.0) < self.MIN_SUCCESS_RATE_FOR_PATTERN:
                if stats.get("count", 0) >= self.MIN_FAILURE_COUNT_FOR_analysis:
                    candidate = self._create_optimization_candidate(skill_name, stats, analysis)
                    if candidate:
                        candidates.append(candidate)

        # Store candidates for review (DO NOT execute)
        self._candidate_skills.extend(candidates)
        self._persist_candidates()

        logger.info(f"[MetaClawShadowMode] Generated {len(candidates)} skill candidates for review")

        return candidates

    def get_candidates(self) -> list[dict]:
        """Get all stored candidate skills pending review."""
        return self._candidate_skills.copy()

    def get_candidate(self, candidate_id: str) -> Optional[dict]:
        """Get a specific candidate by ID."""
        for candidate in self._candidate_skills:
            if candidate.get("id") == candidate_id:
                return candidate
        return None

    def approve_candidate(self, candidate_id: str) -> bool:
        """
        Mark a candidate as approved (for human review workflow).

        Note: This does NOT automatically deploy the skill.
        Human must still validate and deploy through proper channels.
        """
        for candidate in self._candidate_skills:
            if candidate.get("id") == candidate_id:
                candidate["status"] = "approved"
                candidate["approved_at"] = datetime.utcnow().isoformat()
                self._persist_candidates()
                logger.info(f"[MetaClawShadowMode] Candidate {candidate_id} approved (pending deployment)")
                return True
        return False

    def reject_candidate(self, candidate_id: str, reason: str = "") -> bool:
        """Reject a candidate skill."""
        for candidate in self._candidate_skills:
            if candidate.get("id") == candidate_id:
                candidate["status"] = "rejected"
                candidate["rejected_at"] = datetime.utcnow().isoformat()
                candidate["rejection_reason"] = reason
                self._persist_candidates()
                logger.info(f"[MetaClawShadowMode] Candidate {candidate_id} rejected: {reason}")
                return True
        return False

    def get_review_queue(self) -> list[dict]:
        """Get candidates pending review."""
        return [c for c in self._candidate_skills if c.get("status") == "pending"]

    # --- Private analysis methods ---

    def _detect_patterns(self, trajectories: list) -> list[dict]:
        """Detect common execution patterns."""
        patterns = []

        # Detect common skill sequences
        sequence_counts: dict = defaultdict(int)
        for traj in trajectories:
            seq = tuple(traj.get("skill_sequence", []))
            if seq:
                sequence_counts[seq] += 1

        # Convert to patterns
        for seq, count in sequence_counts.items():
            if count >= 2:
                successful = sum(
                    1 for t in trajectories
                    if tuple(t.get("skill_sequence", [])) == seq
                    and t.get("final_result", {}).get("success", False)
                )
                patterns.append({
                    "type": "sequence",
                    "skills": list(seq),
                    "count": count,
                    "success_rate": successful / count if count > 0 else 0.0,
                    "is_composite": len(seq) > 1,
                })

        # Sort by frequency
        patterns.sort(key=lambda p: p.get("count", 0), reverse=True)

        # Detect temporal patterns (time of day correlations)
        # (simplified - just check for morning/afternoon bias)
        time_patterns = self._detect_temporal_patterns(trajectories)
        patterns.extend(time_patterns)

        return patterns

    def _detect_temporal_patterns(self, trajectories: list) -> list[dict]:
        """Detect time-based execution patterns."""
        patterns = []

        # Group by hour
        hourly_counts: dict = defaultdict(lambda: {"total": 0, "success": 0})
        for traj in trajectories:
            started = traj.get("started_at", "")
            if started:
                try:
                    hour = int(started.split("T")[1].split(":")[0])
                    hourly_counts[hour]["total"] += 1
                    if traj.get("final_result", {}).get("success", False):
                        hourly_counts[hour]["success"] += 1
                except (IndexError, ValueError):
                    continue

        # Find high-performance hours
        for hour, stats in hourly_counts.items():
            if stats["total"] >= 3:
                rate = stats["success"] / stats["total"] if stats["total"] > 0 else 0
                if rate >= self.MIN_SUCCESS_RATE_FOR_PATTERN:
                    patterns.append({
                        "type": "temporal",
                        "description": f"Better performance at {hour}:00",
                        "hour": hour,
                        "success_rate": rate,
                        "count": stats["total"],
                    })

        return patterns

    def _compute_success_rates(self, trajectories: list) -> dict:
        """Compute per-skill success rates."""
        skill_stats: dict = defaultdict(lambda: {"total": 0, "success": 0, "failures": []})

        for traj in trajectories:
            success = traj.get("final_result", {}).get("success", False)
            for skill_info in traj.get("skill_sequence", []):
                skill_name = skill_info if isinstance(skill_info, str) else skill_info.get("skill", "unknown")
                skill_stats[skill_name]["total"] += 1
                if success:
                    skill_stats[skill_name]["success"] += 1
                else:
                    skill_stats[skill_name]["failures"].append({
                        "trajectory_id": traj.get("id"),
                        "error": traj.get("final_result", {}).get("message", "Unknown"),
                    })

        return {
            name: {
                "count": stats["total"],
                "success_count": stats["success"],
                "success_rate": stats["success"] / stats["total"] if stats["total"] > 0 else 0.0,
                "failure_details": stats["failures"][:5],  # Limit stored failures
            }
            for name, stats in skill_stats.items()
        }

    def _identify_failure_modes(self, trajectories: list) -> list[dict]:
        """Identify common failure modes."""
        failure_messages: dict = defaultdict(int)

        for traj in trajectories:
            if not traj.get("final_result", {}).get("success", True):
                msg = traj.get("final_result", {}).get("message", "Unknown error")
                # Normalize message
                normalized = self._normalize_error_message(msg)
                failure_messages[normalized] += 1

        # Convert to list sorted by frequency
        failures = [
            {
                "error_type": error_type,
                "count": count,
                "examples": [
                    t.get("final_result", {}).get("message")
                    for t in trajectories
                    if not t.get("final_result", {}).get("success", True)
                    and self._normalize_error_message(t.get("final_result", {}).get("message", "")) == error_type
                ][:3]
            }
            for error_type, count in failure_messages.items()
        ]

        failures.sort(key=lambda f: f["count"], reverse=True)
        return failures

    def _normalize_error_message(self, msg: str) -> str:
        """Normalize error message for grouping."""
        if not msg:
            return "unknown"
        msg = msg.lower()
        # Remove specific values but keep error type
        msg = msg.replace("object '", "object ")
        msg = msg.replace("position ", "")
        msg = msg.replace("x=", "").replace("y=", "").replace("z=", "")
        return msg.strip()[:50]

    def _analyze_skill_sequences(self, trajectories: list) -> dict:
        """Analyze skill sequences for optimization opportunities."""
        sequences = defaultdict(lambda: {"count": 0, "avg_duration_ms": 0, "success_rate": 0})

        for traj in trajectories:
            seq = tuple(skill_info if isinstance(skill_info, str) else skill_info.get("skill", "")
                       for skill_info in traj.get("skill_sequence", []))
            if seq:
                sequences[seq]["count"] += 1
                if traj.get("duration_ms"):
                    prev = sequences[seq]["avg_duration_ms"]
                    n = sequences[seq]["count"]
                    sequences[seq]["avg_duration_ms"] = (prev * (n - 1) + traj["duration_ms"]) / n
                if traj.get("final_result", {}).get("success", False):
                    sequences[seq]["success_rate"] += 1

        # Normalize success rates
        for seq, stats in sequences.items():
            if stats["count"] > 0:
                stats["success_rate"] /= stats["count"]

        return {str(k): v for k, v in sequences.items()}

    def _analyze_common_tasks(self, trajectories: list) -> list[dict]:
        """Analyze common task types."""
        task_counts: dict = defaultdict(lambda: {"count": 0, "success": 0})

        for traj in trajectories:
            task = traj.get("task", "unknown")
            # Normalize task
            normalized = self._normalize_task(task)
            task_counts[normalized]["count"] += 1
            if traj.get("final_result", {}).get("success", False):
                task_counts[normalized]["success"] += 1

        common = [
            {
                "task_pattern": task,
                "count": stats["count"],
                "success_rate": stats["success"] / stats["count"] if stats["count"] > 0 else 0.0,
            }
            for task, stats in task_counts.items()
        ]

        common.sort(key=lambda t: t["count"], reverse=True)
        return common[:10]

    def _normalize_task(self, task: str) -> str:
        """Normalize task string for grouping."""
        if not task:
            return "unknown"
        task = task.lower()
        # Extract intent
        for intent in ["pick", "place", "move", "grasp", "release", "rotate"]:
            if intent in task:
                return intent
        return "other"

    # --- Candidate generation methods ---

    def _create_composite_candidate(self, pattern: dict, analysis: dict) -> Optional[dict]:
        """Create a composite skill candidate from a successful pattern."""
        skills = pattern.get("skills", [])
        if len(skills) < 2:
            return None

        # Check if already exists
        skill_name = f"composite_{'_'.join(skills)}"
        if skill_name in SKILL_REGISTRY:
            return None

        return {
            "id": str(uuid.uuid4()),
            "type": "composite",
            "name": skill_name,
            "description": f"Composite skill combining: {' -> '.join(skills)}",
            "constituent_skills": skills,
            "source_pattern": pattern,
            "estimated_success_rate": pattern.get("success_rate", 0),
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "review_notes": f"Detected from {pattern.get('count', 0)} executions with {pattern.get('success_rate', 0):.0%} success rate",
        }

    def _create_failure_recovery_candidate(self, failure: dict, analysis: dict) -> Optional[dict]:
        """Create a recovery skill candidate from common failures."""
        error_type = failure.get("error_type", "")
        if not error_type or error_type == "unknown":
            return None

        skill_name = f"recover_from_{error_type[:20].replace(' ', '_')}"
        if skill_name in SKILL_REGISTRY:
            return None

        return {
            "id": str(uuid.uuid4()),
            "type": "recovery",
            "name": skill_name,
            "description": f"Recovery skill for error: {error_type}",
            "error_type": error_type,
            "occurrences": failure.get("count", 0),
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "review_notes": f"Detected {failure.get('count', 0)} failures of type: {error_type}",
        }

    def _create_optimization_candidate(self, skill_name: str, stats: dict, analysis: dict) -> Optional[dict]:
        """Create an optimized version of a low-performing skill."""
        if skill_name in SKILL_REGISTRY:
            existing = SKILL_REGISTRY[skill_name]
            new_name = f"{skill_name}_v2"
        else:
            new_name = skill_name

        if new_name in SKILL_REGISTRY:
            return None

        return {
            "id": str(uuid.uuid4()),
            "type": "optimization",
            "name": new_name,
            "description": f"Optimized version of {skill_name}",
            "based_on": skill_name,
            "current_success_rate": stats.get("success_rate", 0),
            "execution_count": stats.get("count", 0),
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "review_notes": f"Current {skill_name} has {stats.get('success_rate', 0):.0%} success rate over {stats.get('count', 0)} executions",
        }

    # --- Persistence methods ---

    def _load_candidates(self) -> None:
        """Load stored candidates from disk."""
        if not self._storage_dir:
            return

        import json
        from pathlib import Path

        candidates_file = Path(self._storage_dir) / "shadow_candidates.json"
        if candidates_file.exists():
            try:
                with open(candidates_file) as f:
                    self._candidate_skills = json.load(f)
                logger.info(f"[MetaClawShadowMode] Loaded {len(self._candidate_skills)} stored candidates")
            except Exception as e:
                logger.warning(f"[MetaClawShadowMode] Failed to load candidates: {e}")

    def _persist_candidates(self) -> None:
        """Persist candidates to disk."""
        if not self._storage_dir:
            return

        import json
        from pathlib import Path

        candidates_file = Path(self._storage_dir) / "shadow_candidates.json"
        try:
            Path(self._storage_dir).mkdir(parents=True, exist_ok=True)
            with open(candidates_file, "w") as f:
                json.dump(self._candidate_skills, f, indent=2)
        except Exception as e:
            logger.warning(f"[MetaClawShadowMode] Failed to persist candidates: {e}")
