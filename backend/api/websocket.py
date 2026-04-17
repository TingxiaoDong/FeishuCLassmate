"""
WebSocket API routes for real-time updates.
"""
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from backend.services.websocket import manager
from backend.services.robot import get_robot_service

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/robot")
async def robot_websocket_endpoint(
    websocket: WebSocket,
    channel: str = Query(default="robot_updates")
):
    """
    WebSocket endpoint for real-time robot updates.

    Clients connect to this endpoint to receive:
    - Robot status updates
    - World state changes
    - Skill execution events
    """
    await manager.connect(websocket, channel)
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "channel": channel,
            "message": "Connected to robot updates stream"
        })

        # Start background task to send periodic status updates
        async def send_periodic_updates():
            while True:
                try:
                    service = get_robot_service()
                    status = await service.get_status()
                    await websocket.send_json({
                        "type": "status_update",
                        "data": status.model_dump()
                    })
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
                await asyncio.sleep(0.5)  # Update every 500ms

        update_task = asyncio.create_task(send_periodic_updates())

        # Listen for client messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif message.get("type") == "subscribe":
                    new_channel = message.get("channel", channel)
                    manager.disconnect(websocket, channel)
                    await manager.connect(websocket, new_channel)
                    channel = new_channel
                elif message.get("type") == "get_status":
                    service = get_robot_service()
                    status = await service.get_status()
                    await websocket.send_json({
                        "type": "status_update",
                        "data": status.model_dump()
                    })

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)
        update_task.cancel()
    except Exception as e:
        manager.disconnect(websocket, channel)
        try:
            update_task.cancel()
        except:
            pass


@router.websocket("/ws/openclaw")
async def openclaw_bridge_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for OpenClaw Gateway bridge.

    OpenClaw connects here to send skill sequences for execution.
    This bridges OpenClaw's planning with our robot control pipeline.

    Message format from OpenClaw:
    {
        "type": "skill_sequence",
        "task": "移动到位置A",
        "skills": [{"skill": "move_to", "params": {...}}, ...]
    }
    """
    await manager.connect(websocket, "openclaw")
    try:
        await websocket.send_json({
            "type": "connected",
            "channel": "openclaw",
            "message": "Connected to OpenClaw bridge"
        })

        # Import here to avoid circular imports
        from src.planner.execution_pipeline import ExecutionPipeline
        from src.planner.openclaw_planner import OpenClawPlanner
        from src.robot_api.mock_robot_api import MockRobotAPI

        pipeline = ExecutionPipeline(MockRobotAPI(), OpenClawPlanner())

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

            elif message.get("type") == "skill_sequence":
                # Execute skill sequence from OpenClaw
                skills = message.get("skills", [])
                task = message.get("task", "")

                results = []
                for skill in skills:
                    result = await pipeline.execute_skill(skill)
                    results.append({
                        "skill": skill.get("skill"),
                        "status": "completed" if hasattr(result, 'success') and result.success else "failed",
                        "message": result.message if hasattr(result, 'message') else str(result)
                    })

                await websocket.send_json({
                    "type": "execution_result",
                    "task": task,
                    "results": results,
                    "success": all(r.get("status") == "completed" for r in results)
                })

            elif message.get("type") == "execute_task":
                # Execute a full task string
                task = message.get("task", "")
                result = await pipeline.execute(task)

                await websocket.send_json({
                    "type": "execution_result",
                    "task": task,
                    "result": result.get("final_result"),
                    "success": result.get("final_result", {}).get("success", False)
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket, "openclaw")
    except Exception as e:
        manager.disconnect(websocket, "openclaw")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass


@router.websocket("/ws/world-state")
async def world_state_websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint specifically for world state updates.
    """
    await manager.connect(websocket, "world_state")
    try:
        await websocket.send_json({
            "type": "connected",
            "channel": "world_state",
            "message": "Connected to world state stream"
        })

        async def send_world_state():
            while True:
                try:
                    service = get_robot_service()
                    state = await service.get_world_state()
                    await websocket.send_json({
                        "type": "world_state_update",
                        "data": state.model_dump()
                    })
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
                await asyncio.sleep(1.0)  # Update every 1s

        update_task = asyncio.create_task(send_world_state())

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket, "world_state")
        update_task.cancel()
    except Exception:
        manager.disconnect(websocket, "world_state")
        try:
            update_task.cancel()
        except:
            pass
