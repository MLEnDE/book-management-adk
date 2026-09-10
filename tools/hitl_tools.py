"""
Human-In-The-Loop (HITL) Gate Tools for ADK Multi-Agent System.
Manages approval requests, policy checks, and user confirmation flow.
"""

from typing import List, Dict, Any
from book_management_adk.models.schemas import ApprovalRequest, ActionType, RiskLevel


# Active pending approval queue
PENDING_APPROVAL_QUEUE: List[ApprovalRequest] = []
APPROVED_HISTORY: List[ApprovalRequest] = []


def request_human_approval(
    action_type: ActionType,
    title: str,
    description: str,
    payload: Dict[str, Any],
    risk_level: RiskLevel = RiskLevel.MEDIUM
) -> Dict[str, Any]:
    """
    Submits a high-impact mutation action to the Human-In-The-Loop (HITL) approval queue.
    
    Args:
        action_type: Type of action requiring user sign-off (e.g. PLACE_LIBBY_HOLD, PURCHASE_KINDLE_DEAL).
        title: Short title for user notification.
        description: Full context and rationale for the action.
        payload: Metadata and execution parameters for the tool.
        risk_level: Risk classification ('low', 'medium', 'high').
        
    Returns:
        Status response with request ID and queue state.
    """
    request_id = f"req_{len(PENDING_APPROVAL_QUEUE) + len(APPROVED_HISTORY) + 1001}"
    
    approval_req = ApprovalRequest(
        request_id=request_id,
        action_type=action_type,
        title=title,
        description=description,
        payload=payload,
        risk_level=risk_level
    )
    
    PENDING_APPROVAL_QUEUE.append(approval_req)
    
    return {
        "status": "pending_approval",
        "request_id": request_id,
        "action_type": action_type.value,
        "title": title,
        "description": description,
        "message": f"Action queued for human approval (Risk: {risk_level.value.upper()}). Waiting for user confirmation."
    }


def list_pending_approvals() -> List[Dict[str, Any]]:
    """
    Returns all currently pending human approval requests.
    """
    return [req.model_dump() for req in PENDING_APPROVAL_QUEUE]


def resolve_approval_request(request_id: str, approved: bool, user_note: str = "") -> Dict[str, Any]:
    """
    Processes a user approval or rejection decision for a pending HITL request.
    
    Args:
        request_id: Unique request identifier.
        approved: True to execute action, False to reject.
        user_note: Optional note or feedback from user.
        
    Returns:
        Resolution confirmation and execution payload if approved.
    """
    global PENDING_APPROVAL_QUEUE, APPROVED_HISTORY
    
    target_req = None
    for req in PENDING_APPROVAL_QUEUE:
        if req.request_id == request_id:
            target_req = req
            break
            
    if not target_req:
        return {"success": False, "error": f"Request ID {request_id} not found in pending queue."}
        
    PENDING_APPROVAL_QUEUE = [req for req in PENDING_APPROVAL_QUEUE if req.request_id != request_id]
    
    if approved:
        APPROVED_HISTORY.append(target_req)
        return {
            "success": True,
            "decision": "approved",
            "request": target_req.model_dump(),
            "message": f"Request '{target_req.title}' APPROVED. Proceeding with execution.",
            "user_note": user_note
        }
    else:
        return {
            "success": True,
            "decision": "rejected",
            "request": target_req.model_dump(),
            "message": f"Request '{target_req.title}' REJECTED by user.",
            "user_note": user_note
        }
