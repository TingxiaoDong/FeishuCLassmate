# Feishu → OpenClaw → Temi Architecture Design

## Overview

This document describes the architecture for controlling a Temi robot via Feishu commands using OpenClaw as the skill planner.

## Architecture Options

### Option A (Recommended): Backend as Bridge

```
┌─────────┐     ┌─────────────────┐     ┌──────────────┐     ┌─────────────┐     ┌───────┐
│ Feishu  │────▶│ OpenClaw Gateway │────▶│ Our Backend  │────▶│ Temi Driver │────▶│ Temi  │
│  (User) │     │  (ws://...)     │     │  (Bridge)    │     │ (WebSocket) │     │       │
└─────────┘     └─────────────────┘     └──────────────┘     └─────────────┘     └───────┘
```

**Pros:**
- Full control over skill execution
- Can add logging, safety checks, validation
- Backend can intercept/modify skill sequences
- Easier to debug and test

**Cons:**
- Additional hop in the chain
- Need to maintain bridge logic

### Option B: OpenClaw Direct

```
Feishu → OpenClaw → Skills → Temi WebSocket → Temi
```

**Pros:**
- Simpler, fewer moving parts
- OpenClaw handles everything

**Cons:**
- Less control
- Harder to integrate safety checks
- OpenClaw must know Temi-specific commands

---

## Recommended: Option A with Clear Data Flow

## Data Flow

### 1. User Command (Feishu)
```
User: "Temi, conduct a lab tour"
```

### 2. OpenClaw Gateway (WebSocket)
```json
{
  "type": "task",
  "task": "conduct a lab tour",
  "session_id": "uuid",
  "source": "feishu"
}
```

### 3. Our Backend (Receives via WebSocket)
```python
# Connect to OpenClaw gateway
# Receive task, forward acknowledgment
{
  "type": "ack",
  "task": "conduct a lab tour",
  "status": "received"
}
```

### 4. Skill Sequence from OpenClaw
```json
{
  "type": "skill_sequence",
  "skills": [
    {"skill": "move_to", "params": {"location": "entrance"}},
    {"skill": "speak", "params": {"text": "Welcome to the lab"}},
    {"skill": "move_to", "params": {"location": "station_1"}},
    {"skill": "speak", "params": {"text": "This is our main research area"}}
  ]
}
```

### 5. Backend → Temi Commands (WebSocket)
```python
# For each skill, convert to Temi command
# Temi SDK uses: client.move_to(x, y, z) or client.go_to("location_name")
# For speak: client.speak(text)

# Example Temi command structure:
{
  "cmd": "move_to",
  "params": {"x": 1.0, "y": 2.0, "z": 0.0}
}
```

---

## Required API Endpoints

### Backend WebSocket (OpenClaw ↔ Backend)
```
WS /ws/openclaw
```

### Backend REST API (Feishu ↔ Backend)
```
POST /api/tasks/execute     # Execute a task
GET  /api/tasks/{id}/status # Get task status
POST /api/tasks/{id}/cancel # Cancel task

GET  /api/robot/state       # Get Temi state
POST /api/robot/command     # Direct command to Temi
```

### Temi WebSocket (Backend ↔ Temi)
```
WS /temi/connection (managed by tongji-cdi/temi library)
```

---

## Code Structure Recommendation

```
src/
├── temi/
│   ├── __init__.py
│   ├── driver.py          # Temi WebSocket connection manager
│   ├── commands.py         # Command builders (move_to, speak, etc.)
│   ├── converter.py        # Skill sequence → Temi commands
│   └── models.py           # Temi state models
│
├── integration/
│   ├── __init__.py
│   ├── openclaw_client.py # OpenClaw gateway WebSocket client
│   └── feishu_webhook.py   # Feishu webhook handler
│
└── bridge/
    ├── __init__.py
    ├── skill_executor.py   # Execute skill on Temi
    └── task_manager.py     # Manage task lifecycle
```

---

## Integrating tongji-cdi/temi

### Installation
```bash
pip install git+https://github.com/tongji-cdi/temi.git
# Or if local: pip install -e /path/to/temi
```

### Basic Usage
```python
from temi import TemiClient

# Connect to Temi
client = TemiClient("192.168.x.x")  # Temi's IP

# Control commands
client.move_to(x=1.0, y=2.0)  # Move to position
client.go_to("location_name") # Go to saved location
client.speak("Hello!")         # Text-to-speech
client.follow()                # Start follow mode
client.stop()                  # Stop all motion

# State callbacks
client.on_state_change(lambda state: print(state))
```

---

## Skill Sequence → Temi Command Mapping

| Skill | Temi Command |
|-------|--------------|
| move_to | `client.go_to(location)` or `client.move_to(x, y)` |
| speak | `client.speak(text)` |
| follow | `client.follow()` |
| stop | `client.stop()` |
| look_at | `client.look_at(x, y, z)` |
| navigate | `client.navigate(x, y)` |

---

## Safety Considerations

1. **Workspace bounds**: Validate all positions before sending to Temi
2. **Rate limiting**: Don't spam Temi with commands
3. **Timeout handling**: If Temi doesn't respond, mark task as failed
4. **Emergency stop**: Always available via `client.stop()`
5. **State monitoring**: Monitor Temi's battery, position, obstacles

---

## Implementation Steps

1. **Create `src/temi/` module** with driver, commands, converter
2. **Create `src/integration/openclaw_client.py`** to connect to OpenClaw gateway
3. **Create WebSocket endpoint** at `/ws/openclaw` to receive tasks
4. **Implement skill executor** that converts skills to Temi commands
5. **Add Feishu webhook endpoint** for external commands
6. **Test with local Temi** or mock

---

## Mock Mode for Testing

Without a real Temi, we can use `MockTemiDriver`:

```python
class MockTemiDriver:
    """Mock Temi for testing without hardware."""

    async def move_to(self, x, y):
        print(f"[Mock] Moving to ({x}, {y})")
        await asyncio.sleep(0.5)

    async def speak(self, text):
        print(f"[Mock] Speaking: {text}")
        await asyncio.sleep(1.0)

    async def stop(self):
        print("[Mock] Stopped")
```

---

## Next Steps

1. Set up `src/temi/` module with driver
2. Connect to OpenClaw gateway WebSocket
3. Implement skill-to-Temi converter
4. Build Feishu webhook handler
5. Test end-to-end with mock mode
