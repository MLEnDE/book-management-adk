"""
Libby Library Subagent Definition for ADK Multi-Agent System.
Specializes in library catalog cross-referencing, hold placement, wait time estimation, and Kindle routing.
"""

from typing import Dict, Any, List
from book_management_adk.tools.libby_tools import search_libby_availability, place_libby_hold
from book_management_adk.tools.hitl_tools import request_human_approval
from book_management_adk.models.schemas import ActionType, RiskLevel
from book_management_adk.hooks.observability_hooks import global_metrics_hook


class LibbyAgent:
    """Subagent responsible for checking library catalogs, estimating holds, and queueing hold approvals."""
    
    def __init__(self, name: str = "LibbyLibraryAgent"):
        self.name = name
        self.system_instructions = (
            "You are the Libby Library Specialist. You cross-reference target books "
            "against linked US library cards, calculate wait times, evaluate Kindle compatibility, "
            "and submit hold requests for Human-In-The-Loop approval."
        )

    def check_and_queue_holds(self, books: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Cross-references a list of books against Libby catalog and queues hold requests."""
        global_metrics_hook.on_turn_start(self.name, 1, f"Check Libby availability for {len(books)} books")
        
        availability_reports = []
        approval_requests = []
        
        for b in books:
            title = b.get("title", "")
            isbn = b.get("isbn", "")
            
            global_metrics_hook.on_tool_call(self.name, "search_libby_availability", {"title": title, "isbn": isbn})
            result = search_libby_availability(title=title, isbn=isbn)
            availability_reports.append(result)
            
            # If waitlisted or available, queue HITL hold request
            if result.get("found") and result.get("status") in ["available_now", "waitlisted"]:
                wait_time = result.get("wait_time_weeks", 0)
                lib_sys = result.get("library_system", "Public Library")
                
                # Queue HITL approval
                req = request_human_approval(
                    action_type=ActionType.PLACE_LIBBY_HOLD,
                    title=f"Place Libby Hold: '{title}'",
                    description=(
                        f"Requesting hold at {lib_sys}. Status: {result.get('status').upper()}. "
                        f"Estimated Wait: {wait_time} weeks. Format: Kindle Direct Sync."
                    ),
                    payload={
                        "title": title,
                        "isbn": isbn,
                        "library_system": lib_sys,
                        "wait_time_weeks": wait_time
                    },
                    risk_level=RiskLevel.MEDIUM
                )
                approval_requests.append(req)
                
        summary = f"Evaluated {len(books)} books on Libby. Queued {len(approval_requests)} holds for human approval."
        global_metrics_hook.on_turn_complete(self.name, 0.62, summary)
        
        return {
            "agent": self.name,
            "availability_reports": availability_reports,
            "approval_requests": approval_requests,
            "summary": summary
        }
