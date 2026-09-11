"""
Conversational Chat Engine for Gemini Enterprise Chat Interface.
Translates user conversational queries, slash commands, and interactive events
into multi-agent orchestrations, returning text and declarative A2UI Material 3 surfaces.
"""

from typing import Dict, Any, List, Optional
from book_management_adk.agents.orchestrator import MasterBookConciergeOrchestrator
from book_management_adk.tools.hitl_tools import list_pending_approvals
from book_management_adk.tools.goodreads_tools import (
    fetch_goodreads_tbr,
    fetch_goodreads_groups,
    fetch_goodreads_currently_reading
)
from book_management_adk.models.a2ui_schemas import (
    A2UISurface,
    build_hitl_approval_card,
    build_action_result_surface
)


class GeminiEnterpriseChatEngine:
    """Handles conversation flow and A2UI surface rendering for the Gemini Enterprise Chat interface."""

    def __init__(self, orchestrator: Optional[MasterBookConciergeOrchestrator] = None):
        self.orchestrator = orchestrator or MasterBookConciergeOrchestrator()

    def handle_user_message(self, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Processes a chat message from Gemini Enterprise, executes the appropriate multi-agent workflow,
        and returns formatted response text along with interactive A2UI surfaces.
        """
        msg_clean = message.strip().lower()
        surfaces: List[Dict[str, Any]] = []

        # 1. Full Multi-Agent Sync Cycle
        if msg_clean.startswith("/sync") or "run cycle" in msg_clean or "full sync" in msg_clean:
            report = self.orchestrator.run_full_workflow_cycle()
            pending = list_pending_approvals()

            # Generate interactive A2UI cards for any pending approvals
            for req in pending:
                card = build_hitl_approval_card(req)
                surfaces.append(card.model_dump())

            response_text = (
                f"### 📚 Reading Concierge Multi-Agent Cycle Complete\n\n"
                f"- **TBR Books Tracked:** {report.goodreads_tbr_count}\n"
                f"- **Libby Library Holds Evaluated:** {report.libby_holds_active}\n"
                f"- **Kindle Price Drops Detected:** {report.kindle_deals_found}\n"
                f"- **Book Club Discussions Prepared:** {report.book_club_updates_processed}\n\n"
            )
            if pending:
                response_text += f"⚠️ **Action Required:** Found {len(pending)} actions awaiting your sign-off below."
            else:
                response_text += "✨ Everything is up to date! No pending approvals."

            return {
                "text": response_text,
                "a2ui_surfaces": surfaces,
                "session_id": session_id,
                "protocol": "A2UI-v0.9"
            }

        # 2. Kindle Deals Radar
        elif msg_clean.startswith("/deals") or "kindle" in msg_clean or "deal" in msg_clean or "price drop" in msg_clean:
            tbr = fetch_goodreads_tbr()
            isbns = [b["isbn"] for b in tbr if "isbn" in b]
            res = self.orchestrator.kindle_agent.scan_and_evaluate_deals(isbns, tbr_books=tbr)

            deals = res.get("evaluated_deals", [])
            approvals = res.get("approval_requests", [])

            for req in approvals:
                card = build_hitl_approval_card(req)
                surfaces.append(card.model_dump())

            response_text = f"### 🏷️ Kindle Deals Radar\n\nFound **{len(deals)}** active discounts matching your Goodreads TBR list:\n\n"
            for d in deals:
                response_text += (
                    f"- **{d['title']}** by {d['author']}: "
                    f"~~${d['list_price']:.2f}~~ ➡️ **${d['deal_price']:.2f}** "
                    f"(`{d['discount_percent']}% OFF` | {d['deal_tier']})\n"
                )

            if approvals:
                response_text += f"\n💡 *I've queued {len(approvals)} recommended purchases for your approval below.*"

            return {
                "text": response_text,
                "a2ui_surfaces": surfaces,
                "session_id": session_id,
                "protocol": "A2UI-v0.9"
            }

        # 3. Libby Library Holds
        elif msg_clean.startswith("/holds") or "libby" in msg_clean or "library" in msg_clean:
            tbr = fetch_goodreads_tbr()
            res = self.orchestrator.libby_agent.check_and_queue_holds(tbr)
            approvals = res.get("approval_requests", [])

            for req in approvals:
                card = build_hitl_approval_card(req)
                surfaces.append(card.model_dump())

            response_text = f"### 🏛️ Libby Library Catalog Availability\n\nCross-referenced {len(tbr)} titles across your library branches:\n\n"
            for report in res.get("availability_reports", []):
                status_str = "🟢 Available Now" if report.get("status") == "available_now" else f"⏳ Waitlist (~{report.get('wait_time_weeks')} wks)"
                response_text += f"- **{report.get('title')}** at {report.get('library_system')}: {status_str}\n"

            if approvals:
                response_text += f"\n📖 *Review and confirm hold requests using the interactive cards below.*"

            return {
                "text": response_text,
                "a2ui_surfaces": surfaces,
                "session_id": session_id,
                "protocol": "A2UI-v0.9"
            }

        # 4. Book Club Coordination
        elif msg_clean.startswith("/bookclub") or "book club" in msg_clean or "discussion" in msg_clean:
            groups = fetch_goodreads_groups()
            res = self.orchestrator.bookclub_agent.process_group_discussions(groups)
            approvals = res.get("approval_requests", [])

            for req in approvals:
                card = build_hitl_approval_card(req)
                surfaces.append(card.model_dump())

            response_text = f"### 👥 Goodreads Book Clubs & Discussion Hub\n\n"
            for g in groups:
                pick = g.get("current_pick", {})
                response_text += (
                    f"**{g.get('group_name')}**\n"
                    f"- Current Reading: *{pick.get('title')}* by {pick.get('author')}\n"
                    f"- Milestone: {g.get('assigned_reading')} (Meeting: {g.get('discussion_date')})\n\n"
                )

            if approvals:
                response_text += "📝 *Drafted discussion prompts are ready. Click below to approve and publish to group forums.*"

            return {
                "text": response_text,
                "a2ui_surfaces": surfaces,
                "session_id": session_id,
                "protocol": "A2UI-v0.9"
            }

        # 5. Pending Approvals Queue
        elif msg_clean.startswith("/approvals") or "approval" in msg_clean or "pending" in msg_clean:
            pending = list_pending_approvals()
            for req in pending:
                card = build_hitl_approval_card(req)
                surfaces.append(card.model_dump())

            if not pending:
                response_text = "### 🛑 Human-in-the-Loop Approval Gate\n\nNo pending approval requests! You are all caught up."
            else:
                response_text = f"### 🛑 Human-in-the-Loop Approval Gate\n\nYou have **{len(pending)}** pending action(s) awaiting confirmation:"

            return {
                "text": response_text,
                "a2ui_surfaces": surfaces,
                "session_id": session_id,
                "protocol": "A2UI-v0.9"
            }

        # 6. Goodreads Shelves & Current Reading
        elif (
            msg_clean.startswith("/shelf")
            or msg_clean.startswith("/goodreads")
            or "currently reading" in msg_clean
            or "tbr" in msg_clean
            or "want to read" in msg_clean
            or "my books" in msg_clean
            or "reading list" in msg_clean
        ):
            cr_books = fetch_goodreads_currently_reading(limit=5)
            tbr_books = fetch_goodreads_tbr(limit=5)
            
            response_text = "### 📖 Emily's Live Goodreads Library\n\n"
            response_text += f"**Currently Reading ({len(cr_books)} in progress):**\n"
            for b in cr_books:
                response_text += f"- **{b['title']}** by {b['author']}\n"
            
            response_text += f"\n**Up Next on Want-to-Read (TBR Shelf):**\n"
            for b in tbr_books:
                response_text += f"- **{b['title']}** by {b['author']}\n"
            
            response_text += "\n*💡 Tip: Use `/deals` to check Kindle price drops on these books or `/holds` to query Libby library availability.*"
            
            return {
                "text": response_text,
                "a2ui_surfaces": surfaces,
                "session_id": session_id,
                "protocol": "A2UI-v0.9"
            }

        # 7. Default / Welcome Assistance
        else:
            response_text = (
                "### 👋 Welcome to your ADK Book Management Concierge!\n\n"
                "I coordinate your reading ecosystem across Goodreads, Libby, and Amazon Kindle Deals.\n\n"
                "**Quick Commands & Suggested Prompts:**\n"
                "- `/shelf` — View your live Goodreads currently-reading & Want-to-Read shelves\n"
                "- `/sync` — Run complete multi-agent discovery and sync\n"
                "- `/deals` — Scan Kindle price drops for your TBR list\n"
                "- `/holds` — Check Libby library availability & wait times\n"
                "- `/bookclub` — Review book club milestones and draft discussion questions\n"
                "- `/approvals` — View pending Human-In-The-Loop actions\n"
            )
            return {
                "text": response_text,
                "a2ui_surfaces": [],
                "session_id": session_id,
                "protocol": "A2UI-v0.9"
            }

    def handle_a2ui_action(self, action_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a deterministic user action event triggered by physical button clicks
        in the Gemini Enterprise Chat interface (e.g. confirming a Libby hold or Kindle purchase).
        """
        if action_id == "resolve_approval":
            request_id = params.get("request_id", "")
            approved = bool(params.get("approved", False))
            user_note = params.get("user_note", "Approved via Gemini Enterprise Chat UI")

            res = self.orchestrator.process_user_approval_decision(request_id, approved, user_note)
            title = res.get("request", {}).get("title", f"Request {request_id}")

            if not res.get("success"):
                error_msg = res.get("error", "Failed to resolve approval request.")
                surface = build_action_result_surface(request_id, title, error_msg, success=False)
                return {
                    "success": False,
                    "surface": surface.model_dump(),
                    "message": error_msg
                }

            if approved:
                exec_res = res.get("execution_result", {})
                msg = exec_res.get("message", f"Successfully executed action for {title}")
                surface = build_action_result_surface(request_id, title, msg, success=True)
                return {
                    "success": True,
                    "surface": surface.model_dump(),
                    "message": msg
                }
            else:
                msg = f"Request for '{title}' was declined and removed from the approval queue."
                surface = build_action_result_surface(request_id, title, msg, success=True)
                return {
                    "success": True,
                    "surface": surface.model_dump(),
                    "message": msg
                }

        return {
            "success": False,
            "message": f"Unknown action_id: {action_id}"
        }
