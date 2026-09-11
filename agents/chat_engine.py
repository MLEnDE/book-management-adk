"""
Conversational Chat Engine for Gemini Enterprise Chat Interface.
Translates user conversational queries, slash commands, and interactive events
into multi-agent orchestrations, returning text and declarative A2UI Material 3 surfaces.
"""

import re
import urllib.parse
from typing import Dict, Any, List, Optional
from book_management_adk.agents.orchestrator import MasterBookConciergeOrchestrator
from book_management_adk.tools.hitl_tools import list_pending_approvals
from book_management_adk.tools.goodreads_tools import (
    fetch_goodreads_tbr,
    fetch_goodreads_groups,
    fetch_goodreads_currently_reading
)
from book_management_adk.tools.kindle_tools import generate_amazon_kindle_url
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

        # 2. Kindle Deals Radar & Secure Purchase Links
        elif (
            msg_clean.startswith("/deals")
            or "deal" in msg_clean
            or "discount" in msg_clean
            or "price drop" in msg_clean
            or "kindle" in msg_clean
            or "link" in msg_clean
            or "url" in msg_clean
            or "buy" in msg_clean
            or "purchase" in msg_clean
            or "website" in msg_clean
            or "where to buy" in msg_clean
        ):
            tbr = fetch_goodreads_tbr()
            isbns = [b["isbn"] for b in tbr if "isbn" in b]
            res = self.orchestrator.kindle_agent.scan_and_evaluate_deals(isbns, tbr_books=tbr)

            deals = res.get("evaluated_deals", [])
            approvals = res.get("approval_requests", [])

            # Check if user specifically asked for the link to a single book
            is_link_query = any(k in msg_clean for k in ["link", "url", "buy", "purchase", "website", "where to buy", "how to buy"])
            matched_book = None
            if is_link_query:
                all_known_books = list(deals) + list(tbr) + fetch_goodreads_currently_reading()
                for b in all_known_books:
                    title = b.get("title", "")
                    clean_title = re.sub(r"\(.*?\)", "", title).strip().lower()
                    short_title = clean_title.split(":")[0].strip()
                    if (short_title and len(short_title) > 3 and short_title in msg_clean) or (clean_title and clean_title in msg_clean):
                        matched_book = b
                        break

            if matched_book and is_link_query:
                title = matched_book.get("title", "")
                author = matched_book.get("author", "")
                deal_url = (
                    matched_book.get("deal_url")
                    or matched_book.get("url")
                    or generate_amazon_kindle_url(title, author, asin=matched_book.get("asin"), isbn=matched_book.get("isbn"))
                )
                deal_price = matched_book.get("deal_price")
                list_price = matched_book.get("list_price")

                response_text = f"### 🔗 Secure Purchase Link: *{title}*\n\n"
                response_text += f"- **Book:** **{title}** by {author}\n"
                if deal_price and list_price:
                    response_text += f"- **Deal Price:** ~~${list_price:.2f}~~ ➡️ **${deal_price:.2f}** (`{matched_book.get('discount_percent', 0)}% OFF`)\n"
                response_text += (
                    f"- **Direct Purchase Website:** [Buy on Amazon Kindle ↗]({deal_url})\n"
                    f"- **Secure HTTPS URL:** `{deal_url}`\n\n"
                    f"🔒 *All transactions are securely handled through Amazon's official retail platform.*"
                )

                for req in approvals:
                    if title.lower() in req.get("title", "").lower():
                        card = build_hitl_approval_card(req)
                        surfaces.append(card.model_dump())

                return {
                    "text": response_text,
                    "a2ui_surfaces": surfaces,
                    "session_id": session_id,
                    "protocol": "A2UI-v0.9"
                }

            # Otherwise, render full deals list with direct purchase links
            for req in approvals:
                card = build_hitl_approval_card(req)
                surfaces.append(card.model_dump())

            response_text = f"### 🏷️ Amazon Kindle Deals & Secure Purchase Links\n\n"
            response_text += f"Found **{len(deals)}** active discounts matching your Goodreads Want-to-Read (TBR) list:\n\n"
            for idx, d in enumerate(deals, 1):
                deal_url = d.get("deal_url") or d.get("url") or generate_amazon_kindle_url(d["title"], d.get("author", ""), isbn=d.get("isbn"))
                expires = d.get("expires_at", "Tonight")
                if "T" in str(expires):
                    expires = str(expires).split("T")[0]

                response_text += (
                    f"#### {idx}. [{d['title']}]({deal_url})\n"
                    f"- **Author:** {d['author']}\n"
                    f"- **Deal Price:** ~~${d['list_price']:.2f}~~ ➡️ **${d['deal_price']:.2f}** "
                    f"(`{d['discount_percent']}% OFF` | {d['deal_tier']})\n"
                    f"- **Expiration:** {expires}\n"
                    f"- **Secure Purchase Site:** [Buy on Amazon Kindle ↗]({deal_url})\n"
                    f"- **Direct URL:** `{deal_url}`\n\n"
                )

            if approvals:
                response_text += "💡 *You can purchase immediately using the secure Amazon links above, or confirm through the approval cards below.*"

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
                book_url = generate_amazon_kindle_url(b['title'], b.get('author', ''), isbn=b.get('isbn'))
                response_text += f"- **[{b['title']}]({book_url})** by {b['author']}\n"
            
            response_text += f"\n**Up Next on Want-to-Read (TBR Shelf):**\n"
            for b in tbr_books:
                book_url = generate_amazon_kindle_url(b['title'], b.get('author', ''), isbn=b.get('isbn'))
                response_text += f"- **[{b['title']}]({book_url})** by {b['author']}\n"
            
            response_text += "\n*💡 Tip: Use `/deals` to check Kindle price drops with secure purchase links or `/holds` to query Libby library availability.*"
            
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
