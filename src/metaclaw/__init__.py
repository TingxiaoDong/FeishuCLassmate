"""
MetaClaw integration for the robotics system.

This module provides the bridge between MetaClaw's continual learning
framework and the robot control system.
"""

from .robot_claw_adapter import RobotClawAdapter, create_robot_claw_adapter
from .skill_executor import SkillExecutor
from .performance_tracker import SkillPerformanceTracker
from .prm_scorer import RobotPRMScorer, CompositePRMScorer, ProcessRewardScore
from .skill_converter import RobotSkillConverter, SkillSchemaUpdater
from .shadow_mode import MetaClawShadowMode
from .interfaces import (
    ExecutionOutcome,
    ExecutionStatus,
    RobotSample,
    SkillPerformanceRecord,
    SafetyViolation,
    SafetyConstraintType,
)

__all__ = [
    # Core adapter
    "RobotClawAdapter",
    "create_robot_claw_adapter",
    # Skill execution
    "SkillExecutor",
    # Performance tracking
    "SkillPerformanceTracker",
    # PRM scoring
    "RobotPRMScorer",
    "CompositePRMScorer",
    "ProcessRewardScore",
    # Skill conversion
    "RobotSkillConverter",
    "SkillSchemaUpdater",
    # Shadow mode
    "MetaClawShadowMode",
    # Data types
    "ExecutionOutcome",
    "ExecutionStatus",
    "RobotSample",
    "SkillPerformanceRecord",
    "SafetyViolation",
    "SafetyConstraintType",
]
