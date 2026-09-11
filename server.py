"""
FastAPI Server for ADK Multi-Agent Book Management System.
Exposes endpoints for Gemini Enterprise OpenAPI Tools, Cloud Run deployment,
Agent Runtime lifecycle probes, Central Agent Registry discovery (A2A),
and Gemini Enterprise App Chat Interface (A2UI).
"""

import os
import sys
import json
import uuid
import logging

# Ensure package directory is on Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Body, Request
from fastapi.responses import JSONResponse, FileResponse
try:
    from sse_starlette.sse import EventSourceResponse
except ImportError:
    from fastapi.responses import StreamingResponse
    def EventSourceResponse(generator):
        async def sse_gen():
            async for item in generator:
                if isinstance(item, dict) and "data" in item:
                    yield f"data: {item['data']}\n\n"
                else:
                    yield f"data: {item}\n\n"
        return StreamingResponse(sse_gen(), media_type="text/event-stream")
from pydantic import BaseModel, Field

logger = logging.getLogger("book_management_server")

from book_management_adk.agents.orchestrator import MasterBookConciergeOrchestrator
from book_management_adk.agents.chat_engine import GeminiEnterpriseChatEngine
from book_management_adk.tools.hitl_tools import list_pending_approvals, resolve_approval_request
from book_management_adk.tools.libby_tools import search_libby_availability, place_libby_hold
from book_management_adk.tools.kindle_tools import check_kindle_deals, evaluate_deal_threshold
from book_management_adk.tools.bookclub_tools import generate_discussion_prompts, draft_group_discussion_post
from book_management_adk.tools.goodreads_tools import fetch_goodreads_tbr, fetch_goodreads_groups

app = FastAPI(
    title="ADK Book Management Concierge API",
    description="Backend microservice exposing ADK Multi-Agent Book Management tools for Gemini Enterprise.",
    version="1.0.0"
)

orchestrator = MasterBookConciergeOrchestrator()
chat_engine = GeminiEnterpriseChatEngine(orchestrator)

AGENT_CARD_PATH = os.path.join(os.path.dirname(__file__), "deployment", "agent-card.json")
CHAT_EXTENSION_PATH = os.path.join(os.path.dirname(__file__), "deployment", "gemini_enterprise_chat_extension.json")


# --- Request/Response Models ---

class ApprovalDecisionRequest(BaseModel):
    approved: bool = Field(..., description="True to execute the pending action, False to reject")
    user_note: Optional[str] = Field("", description="Optional note or context from the approver")


class LibbySearchRequest(BaseModel):
    title: str = Field(..., description="Title of the book to search on Libby")
    isbn: Optional[str] = Field(None, description="ISBN-13 identifier")


class DiscussionPromptRequest(BaseModel):
    book_title: str = Field(..., description="Title of the book")
    author: str = Field(..., description="Author of the book")
    section: str = Field("Full Book", description="Assigned reading section or chapter range")


class ChatMessageRequest(BaseModel):
    message: str = Field(..., description="User query or slash command")
    session_id: Optional[str] = Field(None, description="Session ID for conversation state")


class A2UIActionEvent(BaseModel):
    action_id: str = Field(..., description="Action identifier triggered by UI click")
    params: Dict[str, Any] = Field(default_factory=dict, description="Contextual parameters for action")


# --- Agent Runtime Health & Discovery Probes ---

@app.get("/health", tags=["Agent Runtime Probes"])
def health_check():
    """Health check endpoint for Cloud Run / Agent Runtime container liveness."""
    return {"status": "ok", "app": "book-management-adk", "project": "orbit-499212"}


@app.get("/healthz", tags=["Agent Runtime Probes"])
def healthz_probe():
    """Kubernetes / Agent Runtime liveness probe."""
    return {"status": "alive", "runtime": "google-agent-runtime-v1"}


@app.get("/readyz", tags=["Agent Runtime Probes"])
def readyz_probe():
    """Kubernetes / Agent Runtime readiness probe."""
    return {"status": "ready", "dependencies": "operational"}


# --- Central Agent Registry Discovery (A2A Protocol) ---

@app.get("/.well-known/agent-card.json", tags=["Agent Registry Discovery"])
@app.get("/a2a/v1/agent-card", tags=["Agent Registry Discovery"])
def get_agent_card() -> Dict[str, Any]:
    """Returns the A2A v1.0 Agent Card for Central Agent Registry discovery and registration."""
    if os.path.exists(AGENT_CARD_PATH):
        with open(AGENT_CARD_PATH, "r") as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="Agent Card not found.")


@app.get("/api/v1/chat/extension-manifest", tags=["Gemini Enterprise App"])
def get_chat_extension_manifest() -> Dict[str, Any]:
    """Returns Gemini Enterprise Chat App Extension manifest."""
    if os.path.exists(CHAT_EXTENSION_PATH):
        with open(CHAT_EXTENSION_PATH, "r") as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="Extension manifest not found.")


# --- Gemini Enterprise Chat App & A2A Endpoints ---

@app.get("/a2a/v1/message", tags=["Gemini Enterprise App"])
def get_message_probe():
    """Liveness probe for A2A messaging endpoint."""
    return {
        "status": "operational",
        "protocol": "A2A JSON-RPC 2.0",
        "supportedMethods": ["message/stream", "message/send"]
    }


@app.post("/a2a/v1/message", tags=["Gemini Enterprise App"])
@app.post("/api/v1/chat", tags=["Gemini Enterprise App"])
async def handle_chat_message(request: Request) -> Any:
    """
    Primary endpoint for Gemini Enterprise Chat App and A2A wire protocol.
    Natively supports both:
    1. A2A JSON-RPC 2.0 payloads (methods: 'message/stream' with SSE, 'message/send' with JSONResponse).
    2. Direct REST JSON payloads ({'message': '...', 'session_id': '...'}).
    Returns conversational markdown and interactive Material 3 A2UI surfaces.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    is_jsonrpc = isinstance(body, dict) and body.get("jsonrpc") == "2.0"

    if is_jsonrpc:
        req_id = body.get("id")
        method = body.get("method", "message/stream")
        params = body.get("params", {})
        msg = params.get("message", {}) if isinstance(params, dict) else {}

        # Extract text from parts array or params/body
        parts = msg.get("parts", []) if isinstance(msg, dict) else []
        text_chunks = []
        for p in parts:
            if isinstance(p, dict) and "text" in p and p["text"]:
                text_chunks.append(str(p["text"]))
            elif isinstance(p, str):
                text_chunks.append(p)

        user_message = " ".join(text_chunks).strip()
        if not user_message:
            if isinstance(params, dict):
                user_message = params.get("text", "")
            if not user_message and isinstance(body, dict):
                user_message = body.get("message", "")

        session_id = None
        if isinstance(msg, dict):
            session_id = msg.get("contextId") or msg.get("context_id")
        if not session_id and isinstance(params, dict):
            session_id = params.get("session_id") or params.get("context_id")
        if not session_id and isinstance(body, dict):
            session_id = body.get("session_id")

        logger.info("Received A2A JSON-RPC request [method=%s, id=%s]: '%s'", method, req_id, user_message)

        try:
            engine_res = chat_engine.handle_user_message(user_message, session_id=session_id)
        except Exception as e:
            logger.exception("Error executing agent for query: %s", e)
            engine_res = {
                "text": f"I encountered an error retrieving book data: {str(e)}",
                "a2ui_surfaces": []
            }

        resp_msg_id = str(uuid.uuid4())
        response_payload = {
            "id": req_id,
            "jsonrpc": "2.0",
            "result": {
                "kind": "message",
                "role": "agent",
                "messageId": resp_msg_id,
                "parts": [
                    {
                        "kind": "text",
                        "text": engine_res["text"]
                    }
                ],
                "metadata": {
                    "a2ui_surfaces": engine_res.get("a2ui_surfaces", [])
                }
            }
        }

        if method == "message/stream":
            async def event_generator():
                yield {"data": json.dumps(response_payload)}
            return EventSourceResponse(event_generator())
        else:
            return JSONResponse(content=response_payload)

    # Fallback to direct REST API
    user_message = body.get("message", "") if isinstance(body, dict) else ""
    session_id = body.get("session_id") if isinstance(body, dict) else None
    return chat_engine.handle_user_message(user_message, session_id=session_id)


@app.post("/a2a/v1/action", tags=["Gemini Enterprise App"])
async def handle_ui_action(request: Request) -> Any:
    """
    Handles deterministic button click actions from A2UI interactive confirmation cards
    directly inside the Gemini Enterprise Chat interface (HITL approval resolution).
    Supports both JSON-RPC 2.0 and direct REST POSTs.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    is_jsonrpc = isinstance(body, dict) and body.get("jsonrpc") == "2.0"

    if is_jsonrpc:
        req_id = body.get("id")
        params = body.get("params", {}) if isinstance(body, dict) else {}
        action_id = (params.get("action_id") or params.get("actionId") or body.get("action_id", ""))
        action_params = params.get("params", {})
        res = chat_engine.handle_a2ui_action(action_id, action_params)
        return JSONResponse(content={
            "id": req_id,
            "jsonrpc": "2.0",
            "result": {
                "kind": "message",
                "role": "agent",
                "messageId": str(uuid.uuid4()),
                "parts": [{"kind": "text", "text": res.get("text", "Action processed.")}],
                "metadata": res
            }
        })

    action_id = body.get("action_id", "") if isinstance(body, dict) else ""
    action_params = body.get("params", {}) if isinstance(body, dict) else {}
    return chat_engine.handle_a2ui_action(action_id, action_params)


# --- Orchestration Endpoints ---

@app.post("/api/v1/cycle", tags=["Orchestration"])
def trigger_workflow_cycle() -> Dict[str, Any]:
    """
    Executes a complete multi-agent cycle across Goodreads, Libby, Kindle Deals, and Book Clubs.
    Enqueues pending actions requiring human approval.
    """
    report = orchestrator.run_full_workflow_cycle()
    return report.model_dump()


# --- HITL Approval Endpoints ---

@app.get("/api/v1/approvals", tags=["Human-in-the-Loop"])
def get_pending_approvals() -> List[Dict[str, Any]]:
    """Returns all queued actions currently awaiting Human-in-the-Loop review."""
    return list_pending_approvals()


@app.post("/api/v1/approvals/{request_id}/resolve", tags=["Human-in-the-Loop"])
def resolve_approval(request_id: str, decision: ApprovalDecisionRequest) -> Dict[str, Any]:
    """Approve or reject a pending HITL action (e.g. placing hold, buying Kindle deal)."""
    res = orchestrator.process_user_approval_decision(request_id, decision.approved, decision.user_note)
    if not res.get("success"):
        raise HTTPException(status_code=404, detail=res.get("error", "Failed to resolve approval request"))
    return res


# --- Gemini Enterprise OpenAPI Tools ---

@app.get("/api/v1/tools/goodreads/tbr", tags=["Gemini Enterprise Tools"])
def tool_fetch_tbr(limit: int = 10) -> List[Dict[str, Any]]:
    """Tool: Fetches books on the user's Goodreads Want-to-Read (TBR) shelf."""
    return fetch_goodreads_tbr(limit=limit)


@app.get("/api/v1/tools/goodreads/groups", tags=["Gemini Enterprise Tools"])
def tool_fetch_groups() -> List[Dict[str, Any]]:
    """Tool: Fetches active book club groups and assigned reading."""
    return fetch_goodreads_groups()


@app.post("/api/v1/tools/libby/search", tags=["Gemini Enterprise Tools"])
def tool_search_libby(payload: LibbySearchRequest) -> Dict[str, Any]:
    """Tool: Checks availability and estimated wait times across connected digital library cards."""
    return search_libby_availability(title=payload.title, isbn=payload.isbn)


@app.get("/api/v1/tools/kindle/deals", tags=["Gemini Enterprise Tools"])
def tool_check_kindle_deals() -> List[Dict[str, Any]]:
    """Tool: Scans Amazon Kindle deals for books on the user's TBR list."""
    return check_kindle_deals()


@app.post("/api/v1/tools/bookclub/prompts", tags=["Gemini Enterprise Tools"])
def tool_generate_prompts(payload: DiscussionPromptRequest) -> List[str]:
    """Tool: Generates engaging discussion questions for book club meetings."""
    return generate_discussion_prompts(book_title=payload.book_title, author=payload.author, section=payload.section)
