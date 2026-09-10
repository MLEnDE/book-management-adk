"""
Master Orchestrator Agent for ADK Book Management System.
Coordinates subagents, manages workflow state, enforces safety policies, and generates executive summaries.
"""

from typing import Dict, Any, List
from book_management_adk.agents.goodreads_agent import GoodreadsAgent
from book_management_adk.agents.libby_agent import LibbyAgent
from book_management_adk.agents.kindle_agent import KindleAgent
from book_management_adk.agents.bookclub_agent import BookClubAgent
from book_management_adk.tools.hitl_tools import list_pending_approvals, resolve_approval_request
from book_management_adk.tools.libby_tools import place_libby_hold
from book_management_adk.tools.kindle_tools import execute_kindle_deal_purchase
from book_management_adk.tools.bookclub_tools import publish_goodreads_group_post
from book_management_adk.models.schemas import WorkflowReport, ActionType
from book_management_adk.hooks.observability_hooks import global_metrics_hook


class MasterBookConciergeOrchestrator:
    """
    Master Orchestrator Agent operating in ADK environment.
    Coordinates Goodreads, Libby, Kindle Deals, and Book Club domain subagents.
    """
    
    def __init__(self, name: str = "MasterBookConcierge"):
        self.name = name
        self.system_instructions = (
            "You are the Master Book Concierge. You coordinate specialized domain subagents "
            "to automate Goodreads shelf tracking, Libby library hold discovery, Amazon Kindle deal monitoring, "
            "and Goodreads group book club coordination, while strictly enforcing Human-In-The-Loop approval gates."
        )
        
        # Instantiate subagents
        self.goodreads_agent = GoodreadsAgent()
        self.libby_agent = LibbyAgent()
        self.kindle_agent = KindleAgent()
        self.bookclub_agent = BookClubAgent()

    def run_full_workflow_cycle(self) -> WorkflowReport:
        """Executes an end-to-end multi-agent orchestration cycle."""
        global_metrics_hook.on_turn_start(self.name, 1, "Initiate full multi-agent book management cycle")
        
        # Step 1: Delegate to Goodreads Agent
        gr_results = self.goodreads_agent.run_sync_task()
        tbr_books = gr_results["tbr_books"]
        groups = gr_results["groups"]
        
        # Step 2: Delegate to Libby Agent
        libby_results = self.libby_agent.check_and_queue_holds(tbr_books)
        
        # Step 3: Delegate to Kindle Deals Agent
        tbr_isbns = [b["isbn"] for b in tbr_books if "isbn" in b]
        kindle_results = self.kindle_agent.scan_and_evaluate_deals(tbr_isbns)
        
        # Step 4: Delegate to Book Club Coordinator Agent
        bookclub_results = self.bookclub_agent.process_group_discussions(groups)
        
        # Aggregate pending approvals
        pending_approvals = list_pending_approvals()
        
        # Format Markdown Executive Summary
        summary_md = (
            f"# 📚 Master Book Concierge Executive Report\n\n"
            f"**Execution Timestamp:** September 10, 2026\n\n"
            f"### 📊 Cycle Highlights\n"
            f"- **Goodreads TBR Shelf:** Sync completed ({len(tbr_books)} books active)\n"
            f"- **Goodreads Book Clubs:** {len(groups)} active group readings tracked\n"
            f"- **Libby Library Catalog:** Evaluated {len(tbr_books)} titles across linked library systems\n"
            f"- **Kindle Price Drops:** Found {len(kindle_results['evaluated_deals'])} matching deals\n"
            f"- **Human-In-The-Loop Actions Queued:** **{len(pending_approvals)} pending user approvals**\n\n"
            f"### 🛑 Human-In-The-Loop Approval Queue\n"
        )
        
        for idx, req in enumerate(pending_approvals):
            summary_md += (
                f"#### Request #{idx+1} [{req['request_id']}]: {req['title']}\n"
                f"- **Action Type:** `{req['action_type']}`\n"
                f"- **Risk Classification:** `{req['risk_level'].upper()}`\n"
                f"- **Context:** {req['description']}\n\n"
            )
            
        report = WorkflowReport(
            goodreads_tbr_count=len(tbr_books),
            libby_holds_active=len(libby_results["approval_requests"]),
            kindle_deals_found=len(kindle_results["evaluated_deals"]),
            book_club_updates_processed=len(groups),
            summary_markdown=summary_md
        )
        
        global_metrics_hook.on_turn_complete(self.name, 1.85, f"Completed cycle. {len(pending_approvals)} items awaiting HITL signoff.")
        return report

    def process_user_approval_decision(self, request_id: str, approved: bool, user_note: str = "") -> Dict[str, Any]:
        """
        Executes approved action or drops rejected action upon human confirmation.
        """
        res = resolve_approval_request(request_id, approved, user_note)
        if not res["success"] or res["decision"] == "rejected":
            return res
            
        req = res["request"]
        action_type = req["action_type"]
        payload = req["payload"]
        
        # Execute tool based on approved action type
        if action_type == ActionType.PLACE_LIBBY_HOLD.value:
            exec_res = place_libby_hold(payload["title"], payload["library_system"], payload["isbn"])
            return {**res, "execution_result": exec_res}
            
        elif action_type == ActionType.PURCHASE_KINDLE_DEAL.value:
            exec_res = execute_kindle_deal_purchase(payload["deal_id"], payload["title"], payload["deal_price"])
            return {**res, "execution_result": exec_res}
            
        elif action_type == ActionType.POST_BOOKCLUB_UPDATE.value:
            exec_res = publish_goodreads_group_post(payload["group_id"], payload["post_body"])
            return {**res, "execution_result": exec_res}
            
        return res
