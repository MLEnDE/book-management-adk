"""
FastAPI Server for ADK Multi-Agent Book Management System.
Exposes endpoints for Gemini Enterprise OpenAPI Tools, Cloud Run deployment,
Agent Runtime lifecycle probes, Central Agent Registry discovery (A2A),
and Gemini Enterprise App Chat Interface (A2UI).
"""

import os
import sys
import json

# Ensure package directory is on Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field

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

@app.post("/a2a/v1/message", tags=["Gemini Enterprise App"])
@app.post("/api/v1/chat", tags=["Gemini Enterprise App"])
def handle_chat_message(payload: ChatMessageRequest) -> Dict[str, Any]:
    """
    Primary endpoint for Gemini Enterprise Chat App.
    Accepts natural language user input or slash commands, runs agent orchestration,
    and returns conversational responses alongside declarative A2UI Material 3 surfaces.
    """
    return chat_engine.handle_user_message(payload.message, payload.session_id)


@app.post("/a2a/v1/action", tags=["Gemini Enterprise App"])
def handle_ui_action(payload: A2UIActionEvent) -> Dict[str, Any]:
    """
    Handles deterministic button click actions from A2UI interactive confirmation cards
    directly inside the Gemini Enterprise Chat interface (HITL approval resolution).
    """
    return chat_engine.handle_a2ui_action(payload.action_id, payload.params)


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
