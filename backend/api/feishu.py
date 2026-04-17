"""
Feishu webhook handler for robot commands.

Receives messages from Feishu and routes them to the execution pipeline.
"""
import json
import httpx
from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/feishu", tags=["feishu"])

# Feishu app credentials from openclaw.json
FEISHU_APP_ID = "cli_a96b727740381bd7"
FEISHU_APP_SECRET = "wBVWH65YHkBjdKrqzyyZEf6GVCnbBt3b"
FEISHU_API_BASE = "https://open.feishu.cn/open-apis"


class FeishuMessage(BaseModel):
    """Feishu incoming message format."""
    msg_type: str
    content: dict
    open_id: Optional[str] = None
    session_id: Optional[str] = None


async def get_tenant_access_token() -> str:
    """Get tenant access token from Feishu."""
    url = f"{FEISHU_API_BASE}/auth/v3/tenant_access_token/internal"
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json={
            "app_id": FEISHU_APP_ID,
            "app_secret": FEISHU_APP_SECRET
        })
        data = response.json()
        return data.get("tenant_access_token", "")


async def send_feishu_message(chat_id: str, message_id: str, text: str) -> bool:
    """Send a reply message to Feishu chat."""
    token = await get_tenant_access_token()
    url = f"{FEISHU_API_BASE}/im/v1/messages/{message_id}/reply"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            json={
                "msg_type": "text",
                "content": json.dumps({"text": text})
            },
            params={"receive_id_type": "message_id"}
        )
        return response.status_code == 200


@router.get("/webhook")
async def handle_feishu_webhook_get(request: Request):
    """
    Handle Feishu webhook verification GET request.
    Feishu sends a challenge parameter and expects it back.
    """
    query_params = dict(request.query_params)
    challenge = query_params.get("challenge", "")
    if challenge:
        return {"challenge": challenge}
    return {"error": "no challenge provided"}


@router.post("/webhook")
async def handle_feishu_webhook(request: Request) -> dict:
    """
    Handle incoming Feishu webhook.

    Feishu sends events in format:
    {
        "schema": "2.0",
        "header": {...},
        "event": {
            "message": {...},
            "chat_id": "...",
            "sender": {...}
        }
    }

    For challenge verification, Feishu sends:
    {"challenge": "xxx"}
    """
    body = await request.body()
    try:
        data = json.loads(body)
    except:
        return {"status": "error", "reason": "invalid json"}

    # Handle challenge verification
    if "challenge" in data:
        challenge = data.get("challenge", "")
        if challenge:
            return {"challenge": challenge}
        return {"error": "no challenge provided"}

    # Extract event data
    event = data.get("event", {})
    message = event.get("message", {})
    chat_id = event.get("chat_id", "")
    message_id = message.get("message_id", "")

    msg_type = message.get("msg_type", "")
    content = message.get("content", "")

    # Parse message content
    try:
        content_obj = json.loads(content) if isinstance(content, str) else content
    except:
        content_obj = {"text": content}

    # Check for robot command prefix
    text = content_obj.get("text", "").strip()

    if text.startswith("/robot "):
        command = text[7:].strip()
        result = await execute_robot_command(command)

        # Send reply back to Feishu
        reply_text = f"✅ 命令已执行: {command}\n\n"
        if result.get("final_result", {}).get("success"):
            reply_text += f"状态: 成功\n"
            reply_text += f"结果: {result.get('final_result', {}).get('message', '执行完成')}"
        else:
            reply_text += f"状态: 失败\n"
            reply_text += f"错误: {result.get('final_result', {}).get('message', '未知错误')}"

        if message_id and chat_id:
            await send_feishu_message(chat_id, message_id, reply_text)

        return {"status": "ok", "command": command, "result": result}

    return {"status": "ignored", "reason": "no /robot prefix"}


async def execute_robot_command(command: str) -> dict:
    """
    Execute a robot command through the pipeline.

    Args:
        command: The robot command (e.g., "move to entrance")

    Returns:
        Execution result
    """
    from backend.api.pipeline import ExecuteTaskRequest, execute_task

    request = ExecuteTaskRequest(task=command)
    result = await execute_task(request)
    return result