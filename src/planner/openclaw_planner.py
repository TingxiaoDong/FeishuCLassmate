"""
OpenClawPlanner - Intelligent task planning using MetaClaw's skill registry.

This planner:
- Takes natural language task descriptions
- Calls real MetaClaw proxy for skill decomposition
- Uses OpenAI-compatible API at http://127.0.0.1:30000/v1
- Falls back to keyword matching if MetaClaw is unavailable
"""

import re
import logging
from typing import Any, Optional

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from src.skill.skill_schemas import (
    SKILL_REGISTRY,
    get_skill_schema,
    SkillSchema,
    SkillType,
)
from src.metaclaw.interfaces import ExecutionStatus

logger = logging.getLogger(__name__)

# MetaClaw proxy configuration
METACLAW_BASE_URL = "http://127.0.0.1:30000/v1"
METACLAW_API_KEY = "metaclaw"
METACLAW_MODEL = "metaclaw-model"


# Available skills for planning
AVAILABLE_SKILLS = list(SKILL_REGISTRY.keys())

# Location string to coordinate mapping
LOCATION_COORDS = {
    "workstation 1": {"x": 0.5, "y": 0.0, "z": 0.1},
    "workstation 2": {"x": 1.0, "y": 0.0, "z": 0.1},
    "workstation 3": {"x": 1.5, "y": 0.0, "z": 0.1},
    "entrance": {"x": 0.0, "y": 0.0, "z": 0.0},
    "charging station": {"x": -0.5, "y": 0.0, "z": 0.0},
    "home": {"x": 0.0, "y": 0.0, "z": 0.0},
    "default": {"x": 0.5, "y": 0.0, "z": 0.1},
}

# MetaClaw skill name to our skill name mapping
SKILL_NAME_MAP = {
    "navigate_to": "move_to",
    "go_to": "move_to",
    "goto": "move_to",
    "move": "move_to",
    "navigate": "move_to",
    "say": "speak",
    "talk": "speak",
    "tell": "speak",
    "announce": "speak",
    "pick_up": "grasp",
    "get": "grasp",
    "grab": "grasp",
    "put_down": "release",
    "drop": "release",
    "place": "release",
    "stop": "stop",
    "halt": "stop",
}

# Parameter name mapping from MetaClaw to our format
PARAM_NAME_MAP = {
    "location": "target_x",
    "target_location": "target_x",
    "dest": "target_x",
    "destination": "target_x",
    "position": "target_x",
    "pos": "target_x",
    "text": "message",
    "words": "message",
    "speech": "message",
}


class OpenClawPlanner:
    """
    Intelligent task planner using MetaClaw's skill registry.

    Calls real MetaClaw proxy for skill decomposition when available,
    falls back to keyword matching otherwise.
    """

    def __init__(self):
        """Initialize OpenClawPlanner with skill registry."""
        self._skill_registry = SKILL_REGISTRY
        self._client = None
        if OPENAI_AVAILABLE:
            try:
                self._client = OpenAI(api_key=METACLAW_API_KEY, base_url=METACLAW_BASE_URL)
                logger.info("[OpenClawPlanner] Connected to MetaClaw proxy")
            except Exception as e:
                logger.warning(f"[OpenClawPlanner] Failed to connect to MetaClaw: {e}")

    async def plan(self, task: str, context: Optional[dict] = None) -> list[dict[str, Any]]:
        """
        Plan skill sequence from natural language task.

        Args:
            task: Natural language task description
                  e.g., "pick the red box and place it at location A"
            context: Optional context dict with world state, objects, etc.

        Returns:
            List of skill dictionaries with name and parameters
            e.g., [{"skill": "pick_and_place", "params": {...}}]
        """
        # Try real MetaClaw first
        if self._client:
            try:
                return await self._plan_with_metaclaw(task, context)
            except Exception as e:
                logger.warning(f"[OpenClawPlanner] MetaClaw planning failed: {e}")

        # Fallback to keyword matching
        logger.info(f"[OpenClawPlanner] Using fallback planner for: '{task}'")
        return await self._plan_fallback(task, context)

    async def _plan_with_metaclaw(self, task: str, context: Optional[dict]) -> list[dict[str, Any]]:
        """Call real MetaClaw proxy for skill sequence."""
        # Build skill registry context for MetaClaw
        skill_context = self._build_skill_context()

        # Create message with skill context so MetaClaw knows available skills
        messages = [
            {"role": "system", "content": (
                "You are a robot skill planner. Given a task, respond ONLY with a JSON array "
                "of skills to execute. No explanation, no natural language.\n\n"
                "Available skills and their parameters:\n"
                f"{skill_context}\n\n"
                "Response format: [{\"skill\": \"skill_name\", \"params\": {...}}]"
            )},
            {"role": "user", "content": task}
        ]

        response = self._client.chat.completions.create(
            model=METACLAW_MODEL,
            messages=messages
        )

        # Extract skill sequence from response
        content = response.choices[0].message.content.strip()

        # Remove markdown code blocks if present
        if content.startswith("```"):
            # Remove first code block marker and language
            lines = content.split("\n")
            if len(lines) >= 2:
                content = "\n".join(lines[1:])  # Skip first line (```json)
            if content.endswith("```"):
                content = content[:-3]  # Remove last ```
            content = content.strip()

        # Parse response - expect JSON format: [{"skill": "...", "params": {...}}]
        import json
        try:
            skills = json.loads(content)
            if isinstance(skills, list) and len(skills) > 0:
                logger.info(f"[OpenClawPlanner] MetaClaw returned {len(skills)} skills")
                return self._normalize_skills(skills)
        except json.JSONDecodeError:
            logger.warning(f"[OpenClawPlanner] Failed to parse MetaClaw response: {content}")

        # If parsing failed, fall back
        return await self._plan_fallback(task, context)

    async def _plan_fallback(self, task: str, context: Optional[dict]) -> list[dict[str, Any]]:
        """Fallback planner using keyword matching."""
        context = context or {}
        task_lower = task.lower()

        # Extract task components
        intent = self._classify_intent(task_lower)
        objects = self._extract_objects(task_lower, context)
        locations = self._extract_locations(task_lower, context)

        logger.info(f"[OpenClawPlanner] Task: '{task}' -> Intent: {intent}, Objects: {objects}, Locations: {locations}")

        # Generate skill sequence based on intent
        if intent == "pick_and_place":
            return self._plan_pick_and_place(objects, locations, context)
        elif intent == "pick":
            return self._plan_pick(objects, context)
        elif intent == "place":
            return self._plan_place(objects, locations, context)
        elif intent == "move":
            return self._plan_move(locations, context)
        elif intent == "rotate":
            return self._plan_rotate(task_lower, context)
        elif intent == "stop":
            return self._plan_stop(context)
        elif intent == "grasp":
            return self._plan_grasp(objects, context)
        elif intent == "release":
            return self._plan_release(objects, context)
        else:
            # Default fallback
            return self._plan_default(task_lower, context)

    def _classify_intent(self, task: str) -> str:
        """Classify the primary intent of the task."""
        # Check for combined pick and place
        if any(kw in task for kw in ["pick", "grab", "get"]) and any(kw in task for kw in ["place", "put", "drop", "set"]):
            return "pick_and_place"
        if any(kw in task for kw in ["pick", "grab", "get"]):
            return "pick"
        if any(kw in task for kw in ["place", "put", "drop", "set"]):
            return "place"
        if any(kw in task for kw in ["move", "go", "navigate", "travel"]):
            return "move"
        if any(kw in task for kw in ["rotate", "turn", "spin", "twist"]):
            return "rotate"
        if any(kw in task for kw in ["stop", "halt", "emergency"]):
            return "stop"
        if any(kw in task for kw in ["grasp", "grip", "close"]):
            return "grasp"
        if any(kw in task for kw in ["release", "open", "let go"]):
            return "release"
        return "unknown"

    def _extract_objects(self, task: str, context: dict) -> dict[str, str]:
        """Extract object identifiers from task and context."""
        objects = {}

        # Try to extract object from task patterns
        # e.g., "pick the red box" -> object_id = "red_box"
        object_patterns = [
            r"(?:the\s+)?(\w+\s+\w+)",
            r"(?:the\s+)?(\w+)",
        ]

        # Extract color + object combinations
        color_match = re.search(r"(red|blue|green|yellow|black|white)\s+(\w+)", task)
        if color_match:
            color, obj = color_match.groups()
            objects["object_id"] = f"{color}_{obj}"
            objects["object_type"] = obj

        # Extract location references
        location_match = re.search(r"(?:at|near|in)\s+(?:location\s+)?([A-Z])", task)
        if location_match:
            objects["target_location"] = location_match.group(1)

        # Check context for default object
        if "object_id" not in objects and "objects" in context:
            if context["objects"]:
                objects["object_id"] = context["objects"][0].get("id", "default_object")

        if "object_id" not in objects:
            objects["object_id"] = "default_object"

        return objects

    def _extract_locations(self, task: str, context: dict) -> dict[str, Any]:
        """Extract location/position information from task and context."""
        locations = {}

        # Extract target location (e.g., "location A", "position B")
        location_match = re.search(r"(?:location|position|spot|target)\s+([A-Z]|\\d+)", task, re.IGNORECASE)
        if location_match:
            locations["target_location"] = location_match.group(1)

        # Extract coordinates if mentioned
        coord_match = re.search(r"x[:\s=]*([-\\d.]+)[,\\s]+y[:\s=]*([-\\d.]+)[,\\s]+z[:\s=]*([-\\d.]+)", task, re.IGNORECASE)
        if coord_match:
            locations["target_x"] = float(coord_match.group(1))
            locations["target_y"] = float(coord_match.group(2))
            locations["target_z"] = float(coord_match.group(3))

        # Check context for workspace bounds
        if "workspace_bounds" in context:
            locations["workspace_bounds"] = context["workspace_bounds"]

        return locations

    def _extract_numeric_param(self, task: str, param_name: str, default: float) -> float:
        """Extract a numeric parameter from task text."""
        pattern = rf"{param_name}[:\s=]*([-\d.]+)"
        match = re.search(pattern, task, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return default

    def _plan_pick_and_place(self, objects: dict, locations: dict, context: dict) -> list[dict[str, Any]]:
        """Plan pick_and_place composite skill."""
        object_id = objects.get("object_id", "default_object")

        # Use pick_and_place composite if available
        if "pick_and_place" in self._skill_registry:
            return [{
                "skill": "pick_and_place",
                "params": {
                    "object_id": object_id,
                    "target_x": locations.get("target_x", 0.5),
                    "target_y": locations.get("target_y", 0.0),
                    "target_z": locations.get("target_z", 0.0),
                    "approach_height": 0.1,
                    "grip_force": 50.0,
                    "speed": 0.5,
                }
            }]

        # Fallback to primitive skills
        return [
            {"skill": "move_to", "params": {"target_x": 0.0, "target_y": 0.0, "target_z": 0.1, "speed": 0.5, "motion_type": "linear"}},
            {"skill": "grasp", "params": {"object_id": object_id, "approach_height": 0.1, "grip_force": 50.0}},
            {"skill": "move_to", "params": {"target_x": locations.get("target_x", 0.5), "target_y": locations.get("target_y", 0.0), "target_z": 0.1, "speed": 0.5, "motion_type": "linear"}},
            {"skill": "release", "params": {"object_id": object_id, "gripper_open_width": 0.05}},
        ]

    def _plan_pick(self, objects: dict, context: dict) -> list[dict[str, Any]]:
        """Plan pick operation."""
        object_id = objects.get("object_id", "default_object")

        if "approach_and_grasp" in self._skill_registry:
            return [{
                "skill": "approach_and_grasp",
                "params": {
                    "object_id": object_id,
                    "target_x": 0.0,
                    "target_y": 0.0,
                    "target_z": 0.0,
                    "approach_height": 0.1,
                    "grip_force": 50.0,
                    "speed": 0.5,
                }
            }]

        return [
            {"skill": "move_to", "params": {"target_x": 0.0, "target_y": 0.0, "target_z": 0.1, "speed": 0.5, "motion_type": "linear"}},
            {"skill": "grasp", "params": {"object_id": object_id, "approach_height": 0.1, "grip_force": 50.0}},
        ]

    def _plan_place(self, objects: dict, locations: dict, context: dict) -> list[dict[str, Any]]:
        """Plan place operation."""
        object_id = objects.get("object_id", "default_object")

        return [
            {"skill": "move_to", "params": {
                "target_x": locations.get("target_x", 0.5),
                "target_y": locations.get("target_y", 0.0),
                "target_z": 0.1,
                "speed": 0.5,
                "motion_type": "linear"
            }},
            {"skill": "place", "params": {
                "object_id": object_id,
                "target_x": locations.get("target_x", 0.5),
                "target_y": locations.get("target_y", 0.0),
                "target_z": locations.get("target_z", 0.0),
                "approach_height": 0.1,
            }},
        ]

    def _plan_move(self, locations: dict, context: dict) -> list[dict[str, Any]]:
        """Plan move operation."""
        return [{
            "skill": "move_to",
            "params": {
                "target_x": locations.get("target_x", 0.5),
                "target_y": locations.get("target_y", 0.0),
                "target_z": locations.get("target_z", 0.1),
                "target_rx": 0.0,
                "target_ry": 0.0,
                "target_rz": 0.0,
                "speed": 0.5,
                "motion_type": "linear",
            }
        }]

    def _plan_rotate(self, task: str, context: dict) -> list[dict[str, Any]]:
        """Plan rotate operation."""
        # Extract axis and angle
        axis = "z"
        if "x-axis" in task or "around x" in task:
            axis = "x"
        elif "y-axis" in task or "around y" in task:
            axis = "y"

        # Extract angle (in degrees, convert to radians)
        angle_match = re.search(r"(\\d+)\\s*(?:degrees?|°)", task, re.IGNORECASE)
        if not angle_match:
            angle_match = re.search(r"(\\d+)\\s*(?:radians?|rad)", task, re.IGNORECASE)
            angle_deg = float(angle_match.group(1)) if angle_match else 90.0
        else:
            angle_deg = float(angle_match.group(1))

        import math
        angle_rad = angle_deg * math.pi / 180.0

        speed = self._extract_numeric_param(task, "speed", 0.5)

        return [{
            "skill": "rotate",
            "params": {
                "axis": axis,
                "angle": angle_rad,
                "speed": speed,
            }
        }]

    def _plan_stop(self, context: dict) -> list[dict[str, Any]]:
        """Plan stop operation."""
        # Check if emergency
        is_emergency = context.get("emergency", False)
        return [{
            "skill": "stop",
            "params": {
                "emergency": is_emergency,
            }
        }]

    def _plan_grasp(self, objects: dict, context: dict) -> list[dict[str, Any]]:
        """Plan grasp operation."""
        object_id = objects.get("object_id", "default_object")
        grip_force = context.get("grip_force", 50.0)
        approach_height = context.get("approach_height", 0.1)

        return [{
            "skill": "grasp",
            "params": {
                "object_id": object_id,
                "approach_height": approach_height,
                "grip_force": grip_force,
            }
        }]

    def _plan_release(self, objects: dict, context: dict) -> list[dict[str, Any]]:
        """Plan release operation."""
        object_id = objects.get("object_id", "default_object")
        gripper_open_width = context.get("gripper_open_width", 0.05)

        return [{
            "skill": "release",
            "params": {
                "object_id": object_id,
                "gripper_open_width": gripper_open_width,
            }
        }]

    def _plan_default(self, task: str, context: dict) -> list[dict[str, Any]]:
        """Default fallback planner."""
        # Try to extract any useful info
        locations = self._extract_locations(task, context)

        return [{
            "skill": "move_to",
            "params": {
                "target_x": locations.get("target_x", 0.0),
                "target_y": locations.get("target_y", 0.0),
                "target_z": locations.get("target_z", 0.1),
                "target_rx": 0.0,
                "target_ry": 0.0,
                "target_rz": 0.0,
                "speed": 0.5,
                "motion_type": "linear",
            }
        }]

    def get_available_skills(self) -> list[str]:
        """Get list of available skill names."""
        return AVAILABLE_SKILLS

    def _normalize_skills(self, skills: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Normalize skill names and parameters from MetaClaw to our format.

        Handles:
        - Skill name mapping (navigate_to → move_to)
        - Parameter mapping (location → target_x/y/z)
        - Location string to coordinate conversion
        """
        normalized = []
        for skill in skills:
            skill_name = skill.get("skill", "")
            params = skill.get("params", {})

            # Map skill name
            mapped_name = SKILL_NAME_MAP.get(skill_name.lower(), skill_name)

            # Map parameters
            mapped_params = {}
            for param_name, param_value in params.items():
                # Map parameter name
                mapped_param_name = PARAM_NAME_MAP.get(param_name.lower(), param_name)

                # Handle location string → coordinates conversion
                if mapped_param_name == "target_x" and isinstance(param_value, str):
                    # Try to convert location string to coordinates
                    location_key = param_value.lower()
                    coords = LOCATION_COORDS.get(location_key, LOCATION_COORDS.get("default", {}))
                    mapped_params["target_x"] = coords.get("x", 0.0)
                    mapped_params["target_y"] = coords.get("y", 0.0)
                    mapped_params["target_z"] = coords.get("z", 0.1)
                else:
                    mapped_params[mapped_param_name] = param_value

            normalized.append({
                "skill": mapped_name,
                "params": mapped_params
            })

        return normalized

    def _build_skill_context(self) -> str:
        """Build skill registry context string for MetaClaw prompts."""
        lines = []
        for name, schema in self._skill_registry.items():
            lines.append(f"- {name}: {schema.description}")
            if hasattr(schema, 'parameters'):
                params = schema.parameters if isinstance(schema.parameters, list) else []
                for p in params:
                    lines.append(f"  - {p.get('name', 'param')}: {p.get('description', '')}")
        return "\n".join(lines) if lines else "move_to(location), speak(text), grasp(object), release(object), stop()"

    def get_skill_info(self, skill_name: str) -> Optional[dict[str, Any]]:
        """Get information about a specific skill."""
        schema = get_skill_schema(skill_name)
        if schema:
            return {
                "name": schema.name,
                "description": schema.description,
                "skill_type": schema.skill_type.value,
                "preconditions": schema.preconditions,
                "effects": schema.effects,
                "safety_constraints": schema.safety_constraints,
            }
        return None
