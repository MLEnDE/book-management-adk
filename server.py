"""
FastAPI Server for ADK Multi-Agent Book Management System.
Exposes endpoints for Gemini Enterprise OpenAPI Tools, Cloud Run deployment, and HITL approvals.
"""

import os
import sys

# Ensure package directory is on Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from book_management_adk.agents.orchestrator import MasterBookConciergeOrchestrator
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


# --- Health & Info ---

@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint for Cloud Run container liveness."""
    return {"status": "ok", "app": "book-management-adk", "project": "orbit-499212"}


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
