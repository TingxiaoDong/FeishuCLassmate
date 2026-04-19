---
name: diagnose-robot-connection-before-retrying
description: When WebSocket or network connection to robot fails, run connectivity diagnostics before attempting the same action again.
category: robotics/execution
---

## Diagnose Robot Connection Before Retrying

When connection to robot (WebSocket at IP:port) times out or fails:

1. **First attempt timeout** → Do NOT immediately retry the same command
2. **Run connectivity checks** (in parallel):
   - `ping -c 3 <robot_ip>` — verify network path
   - `nc -zv <robot_ip> <port>` — check port is open
   - `curl -m 5 http://<robot_ip>:<port>/status` — try HTTP health check
3. **Based on diagnostics**:
   - If ping fails → report "Robot is unreachable on network"
   - If port closed → report "Robot service not responding on port X"
   - If timeout → report "Robot is not responding, may be busy or offline"
4. **Offer next step**: Ask user to check robot power/WiFi, or try again in 30 seconds

**Anti-pattern:** Calling `websockets.connect()` multiple times with same timeout without checking what's wrong. This wastes time and may lock up the assistant.
