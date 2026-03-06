"""
Ecommerce Assistant — Lightweight Web UI
Streams agent responses via SSE (Server-Sent Events).

Usage:
    python app.py
    -> opens http://localhost:8080
"""

import asyncio
import json
import os
import uuid

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.ecommerce_orchestrator import root_agent

app = FastAPI(title="Insightron Ecommerce Assistant")

# ADK runner setup
session_service = InMemorySessionService()
runner = Runner(agent=root_agent, app_name="ecommerce_assistant", session_service=session_service)

# In-memory session store per browser tab
USER_ID = "web_user"
sessions: dict[str, str] = {}


async def _get_or_create_session(session_key: str) -> str:
    """Return an ADK session ID, creating one if needed."""
    if session_key not in sessions:
        session = await session_service.create_session(
            app_name="ecommerce_assistant",
            user_id=USER_ID,
        )
        sessions[session_key] = session.id
    return sessions[session_key]


async def _stream_agent(session_id: str, message: str):
    """Yield SSE chunks as the agent responds."""
    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=message)],
    )
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=content,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    payload = json.dumps({
                        "agent": event.author or "assistant",
                        "text": part.text,
                    })
                    yield f"data: {payload}\n\n"
    yield "data: [DONE]\n\n"


# ── API routes ──────────────────────────────────────────────

@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    message = body.get("message", "").strip()
    session_key = body.get("session_key", str(uuid.uuid4()))

    if not message:
        return {"error": "empty message"}

    session_id = await _get_or_create_session(session_key)

    return StreamingResponse(
        _stream_agent(session_id, message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/reset")
async def reset_session(request: Request):
    body = await request.json()
    session_key = body.get("session_key", "")
    sessions.pop(session_key, None)
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def index():
    with open("static/index.html", "r") as f:
        return f.read()


# Serve static assets
app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)
