"""
Lab Robot Skills - OpenClaw Skills for Research Lab Robot.

These skills support:
- Lab tours and visitor guidance
- Asset management (RFID + visual inspection)
- Project progress management (Gantt tracking)
- Student supervision (focus monitoring)
- Idle behavior (self-initiated activities)
"""
from typing import TypedDict
from dataclasses import dataclass, field

from src.skill.skill_schemas import SkillSchema, SkillType


# ============================================================
# Atomic Skill Input TypedDicts
# ============================================================

class NavigateToInput(TypedDict):
    """Input for navigate_to skill."""
    location: str  # e.g., "lab entrance", "desk_12", "whiteboard"
    speed: float


class RecognizePersonInput(TypedDict):
    """Input for recognize_person skill."""
    timeout: float


class SpeakInput(TypedDict):
    """Input for speak skill."""
    text: str
    voice_id: str  # e.g., "friendly", "professional"


class DetectRFIDInput(TypedDict):
    """Input for detect_rfid skill."""
    tag_id: str


class CaptureVisionInput(TypedDict):
    """Input for capture_vision skill."""
    scene_type: str  # e.g., "desk", "whiteboard", "person", "asset"
    save: bool


class UpdateGanttInput(TypedDict):
    """Input for update_gantt skill."""
    project_id: str
    task_id: str
    updates: dict  # e.g., {"status": "completed", "progress": 100}


class MonitorFocusInput(TypedDict):
    """Input for monitor_focus skill."""
    student_id: str
    duration: float  # seconds


class InitiateConversationInput(TypedDict):
    """Input for initiate_conversation skill."""
    topic: str  # e.g., "research", "coffee", "project_update"
    participant_id: str


# ============================================================
# Atomic Skill Schemas
# ============================================================

NAVIGATE_TO_SCHEMA = SkillSchema(
    name="navigate_to",
    description="Move robot to a specified location in the lab. Uses SLAM for navigation.",
    skill_type=SkillType.MOTION,
    inputs=NavigateToInput,
    preconditions=[
        "robot.battery_level > 20%",
        "target location is mapped",
        "path is clear of obstacles",
    ],
    effects=[
        "robot.position matches target location",
        "robot.state == COMPLETED",
    ],
    safety_constraints=[
        "speed must be within safe limits (< 0.5 m/s indoors)",
        "collision detection must be active",
        "emergency stop available at all times",
    ],
)

RECOGNIZE_PERSON_SCHEMA = SkillSchema(
    name="recognize_person",
    description="Detect and identify a person using vision and optionally RFID.",
    skill_type=SkillType.SENSING,
    inputs=RecognizePersonInput,
    preconditions=[
        "camera is operational",
        "lighting conditions are adequate",
    ],
    effects=[
        "person.id is known",
        "person.name is recognized",
        "person.location is tracked",
    ],
    safety_constraints=[
        "privacy settings must be respected",
        "face recognition only with consent",
        "data retention policies apply",
    ],
)

SPEAK_SCHEMA = SkillSchema(
    name="speak",
    description="Output text as synthesized speech. Text-to-speech with configurable voice.",
    skill_type=SkillType.MANIPULATION,
    inputs=SpeakInput,
    preconditions=[
        "audio system is operational",
        "speaker volume is set",
    ],
    effects=[
        "audio output is produced",
        "message is delivered",
    ],
    safety_constraints=[
        "volume must be below 85 dB",
        "no harmful content",
        "interruption capability must work",
    ],
)

DETECT_RFID_SCHEMA = SkillSchema(
    name="detect_rfid",
    description="Read an RFID tag to identify assets or personnel.",
    skill_type=SkillType.SENSING,
    inputs=DetectRFIDInput,
    preconditions=[
        "RFID reader is operational",
        "tag is within range (< 1m)",
    ],
    effects=[
        "tag_id is read",
        "associated asset/person is identified",
    ],
    safety_constraints=[
        "RFID power must be within safe limits",
        "no interference with medical devices",
    ],
)

CAPTURE_VISION_SCHEMA = SkillSchema(
    name="capture_vision",
    description="Capture image or video from robot camera for analysis.",
    skill_type=SkillType.SENSING,
    inputs=CaptureVisionInput,
    preconditions=[
        "camera is operational",
        "lighting conditions are adequate",
    ],
    effects=[
        "image is captured",
        "scene_type is recorded",
    ],
    safety_constraints=[
        "privacy must be respected",
        "no unauthorized recording",
        "secure storage of images",
    ],
)

UPDATE_GANTT_SCHEMA = SkillSchema(
    name="update_gantt",
    description="Modify a project Gantt chart to update task status or progress.",
    skill_type=SkillType.MANIPULATION,
    inputs=UpdateGanttInput,
    preconditions=[
        "project management system is accessible",
        "user has permission to update",
        "task_id exists in project",
    ],
    effects=[
        "task status is updated",
        "progress is recorded",
        "stakeholders are notified",
    ],
    safety_constraints=[
        "only authorized updates allowed",
        "audit trail is maintained",
        "no deletion of critical tasks",
    ],
)

MONITOR_FOCUS_SCHEMA = SkillSchema(
    name="monitor_focus",
    description="Monitor a student's focus level during work session.",
    skill_type=SkillType.SENSING,
    inputs=MonitorFocusInput,
    preconditions=[
        "student has consented to monitoring",
        "camera is operational",
        "student is present at workstation",
    ],
    effects=[
        "focus_score is recorded",
        "distraction events are logged",
        "intervention triggered if needed",
    ],
    safety_constraints=[
        "privacy must be protected",
        "focus data is anonymized for reports",
        "student can stop monitoring anytime",
    ],
)

INITIATE_CONVERSATION_SCHEMA = SkillSchema(
    name="initiate_conversation",
    description="Start a social interaction on a given topic.",
    skill_type=SkillType.MANIPULATION,
    inputs=InitiateConversationInput,
    preconditions=[
        "participant is available",
        "topic is appropriate",
        "environment is suitable for conversation",
    ],
    effects=[
        "conversation is started",
        "participant is engaged",
        "interaction is logged",
    ],
    safety_constraints=[
        "topic must be appropriate",
        "no personal or sensitive subjects",
        "participant can end conversation anytime",
        "no persuasion manipulation",
    ],
)


# ============================================================
# Composite Skill Input TypedDicts
# ============================================================

class ConductLabTourInput(TypedDict):
    """Input for conduct_lab_tour skill."""
    visitor_id: str
    route: list[str]  # list of location names
    duration: float  # estimated minutes


class ManageAssetInventoryInput(TypedDict):
    """Input for manage_asset_inventory skill."""
    action: str  # "check", "register", "relocate", "retire"
    asset_id: str


class SuperviseStudentInput(TypedDict):
    """Input for supervise_student skill."""
    student_id: str
    session_duration: float  # minutes
    check_interval: float  # minutes between focus checks


class TrackProjectProgressInput(TypedDict):
    """Input for track_project_progress skill."""
    project_id: str
    include_subtasks: bool


class EngageIdleBehaviorInput(TypedDict):
    """Input for engage_idle_behavior skill."""
    preference: str  # "research", "social", "maintenance"
    duration: float  # minutes available


# ============================================================
# Composite Skill Schemas
# ============================================================

CONDUCT_LAB_TOUR_SCHEMA = SkillSchema(
    name="conduct_lab_tour",
    description="Conduct a complete lab tour for visitors. Navigate to locations, provide explanations, and answer questions.",
    skill_type=SkillType.COMPOSITE,
    inputs=ConductLabTourInput,
    preconditions=[
        "visitor_id is recognized",
        "route locations are mapped",
        "robot battery > 30%",
    ],
    effects=[
        "visitor receives tour",
        "all locations are visited",
        "visitor questions are answered",
        "tour feedback is recorded",
    ],
    safety_constraints=[
        "visitor safety is priority",
        "maintain safe distance from visitors",
        "no physical contact unless necessary",
        "emergency exit routes are clear",
    ],
)

MANAGE_ASSET_INVENTORY_SCHEMA = SkillSchema(
    name="manage_asset_inventory",
    description="Manage lab assets using RFID and vision. Check, register, relocate, or retire assets.",
    skill_type=SkillType.COMPOSITE,
    inputs=ManageAssetInventoryInput,
    preconditions=[
        "RFID reader operational",
        "camera operational",
        "asset database accessible",
    ],
    effects=[
        "asset status is updated",
        "inventory records are accurate",
        "location changes are logged",
    ],
    safety_constraints=[
        "only authorized assets are managed",
        "chain of custody is maintained",
        "sensitive assets require verification",
    ],
)

SUPERVISE_STUDENT_SCHEMA = SkillSchema(
    name="supervise_student",
    description="Monitor student work session, check focus, and provide interventions when needed.",
    skill_type=SkillType.COMPOSITE,
    inputs=SuperviseStudentInput,
    preconditions=[
        "student has consented",
        "student is present",
        "camera coverage is adequate",
    ],
    effects=[
        "focus score is recorded",
        "distractions are addressed",
        "breaks are suggested when needed",
        "session report is generated",
    ],
    safety_constraints=[
        "student privacy is protected",
        "interventions are gentle and helpful",
        "student autonomy is respected",
        "escalation path for issues exists",
    ],
)

TRACK_PROJECT_PROGRESS_SCHEMA = SkillSchema(
    name="track_project_progress",
    description="Track and update project progress via Gantt chart analysis.",
    skill_type=SkillType.COMPOSITE,
    inputs=TrackProjectProgressInput,
    preconditions=[
        "project management system accessible",
        "project exists and user has access",
    ],
    effects=[
        "progress is retrieved",
        "delays are identified",
        "stakeholders are notified",
    ],
    safety_constraints=[
        "only view and suggest updates",
        "no unauthorized modifications",
        "audit trail is maintained",
    ],
)

ENGAGE_IDLE_BEHAVIOR_SCHEMA = SkillSchema(
    name="engage_idle_behavior",
    description="Robot-initiated activities when no tasks pending. Options: research reading, social interaction, or equipment maintenance.",
    skill_type=SkillType.COMPOSITE,
    inputs=EngageIdleBehaviorInput,
    preconditions=[
        "no pending urgent tasks",
        "robot is charged (> 50%)",
        "environment is appropriate",
    ],
    effects=[
        "time is productively used",
        "robot state remains ready",
        "social bonds are maintained",
    ],
    safety_constraints=[
        "can be interrupted by urgent tasks",
        "social interactions are appropriate",
        "maintenance doesn't interfere with work",
    ],
)


# ============================================================
# Lab Robot Skill Registry
# ============================================================

LAB_SKILL_REGISTRY: dict[str, SkillSchema] = {
    # Atomic skills
    "navigate_to": NAVIGATE_TO_SCHEMA,
    "recognize_person": RECOGNIZE_PERSON_SCHEMA,
    "speak": SPEAK_SCHEMA,
    "detect_rfid": DETECT_RFID_SCHEMA,
    "capture_vision": CAPTURE_VISION_SCHEMA,
    "update_gantt": UPDATE_GANTT_SCHEMA,
    "monitor_focus": MONITOR_FOCUS_SCHEMA,
    "initiate_conversation": INITIATE_CONVERSATION_SCHEMA,
    # Composite skills
    "conduct_lab_tour": CONDUCT_LAB_TOUR_SCHEMA,
    "manage_asset_inventory": MANAGE_ASSET_INVENTORY_SCHEMA,
    "supervise_student": SUPERVISE_STUDENT_SCHEMA,
    "track_project_progress": TRACK_PROJECT_PROGRESS_SCHEMA,
    "engage_idle_behavior": ENGAGE_IDLE_BEHAVIOR_SCHEMA,
}


# ============================================================
# All Lab Skills as List (for iteration)
# ============================================================

LAB_SKILLS_LIST = list(LAB_SKILL_REGISTRY.values())
