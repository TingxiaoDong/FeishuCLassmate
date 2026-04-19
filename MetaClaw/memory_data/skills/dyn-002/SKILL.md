---
name: dyn-002
description: Use when robot connectivity fails and diagnostic attempts do not resolve the issue. Ask the user to manually verify the robot's status rather than continuing automated diagnostics.
category: robotics/execution
---

## Request User Verification for Robot Issues

When automated diagnostics fail to resolve a robot connection problem:

1. Stop running additional diagnostic commands.
2. Ask the user to perform ONE manual verification step:
   - "Check the robot's screen: Go to Settings → About to see the current IP address."
   - "Confirm the robot is powered on and not in sleep mode."
   - "Verify your computer is connected to the same WiFi network as the robot."
3. Wait for the user to respond with the information.
4. Use the user's input to update connection parameters.

**Example:**

Robot connection failed (192.168.31.121 unreachable).

Could you check the robot's current IP address?
Go to: Settings → About → IP Address


**Anti-pattern:** Running multiple `curl`, `ping`, or `sleep` commands while the user remains unaware of the connection failure.
