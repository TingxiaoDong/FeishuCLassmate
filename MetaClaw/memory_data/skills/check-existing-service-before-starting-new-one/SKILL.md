---
name: check-existing-service-before-starting-new-one
description: Use when attempting to start a server or service that connects to an existing robot endpoint, to avoid conflicts from duplicate processes.
category: automation
---

## Check Existing Services Before Starting New Ones

Before launching a server or service that will connect to an endpoint:

1. **Check if a process is already running** on the target port:
   bash
   lsof -i :8175 | grep LISTEN
   # or
   ps aux | grep -E "(uvicorn|server|robot)" | grep -v grep
   

2. **Check what's already connected to the robot**:
   bash
   curl -s "http://192.168.31.121:8175/api/status"
   

3. **If a service is already running**, use the existing one rather than starting a second instance.

4. **If you must restart**, kill the old process first:
   bash
   pkill -f "uvicorn.*server:app"
   sleep 2
   # then start new
   

**Anti-pattern:** Running `uvicorn server:app` multiple times without checking if one is already active, causing port conflicts and "going away" WebSocket errors.
