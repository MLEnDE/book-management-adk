"""
Book Club Coordinator Subagent Definition for ADK Multi-Agent System.
Specializes in Goodreads group synchronization, discussion prompt drafting, and reading schedules.
"""

from typing import Dict, Any, List
from book_management_adk.tools.bookclub_tools import (
    generate_discussion_prompts,
    draft_group_discussion_post
)
from book_management_adk.tools.hitl_tools import request_human_approval
from book_management_adk.models.schemas import ActionType, RiskLevel
from book_management_adk.hooks.observability_hooks import global_metrics_hook


class BookClubAgent:
    """Subagent responsible for coordinating Goodreads group reading schedules and discussion posts."""
    
    def __init__(self, name: str = "BookClubCoordinatorAgent"):
        self.name = name
        self.system_instructions = (
            "You are the Book Club Coordinator. You track reading schedules across "
            "your book clubs, generate thoughtful AI discussion questions, and draft "
            "Goodreads group forum posts for human review before posting."
        )

    def process_group_discussions(self, groups: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generates discussion posts for active book club groups and submits for review."""
        global_metrics_hook.on_turn_start(self.name, 1, f"Process discussions for {len(groups)} book clubs")
        
        drafts = []
        approval_requests = []
        
        for g in groups:
            group_name = g.get("group_name", "Book Club")
            pick = g.get("current_pick", {})
            title = pick.get("title", "Current Pick")
            author = pick.get("author", "Author")
            section = g.get("assigned_reading", "Current Section")
            m_date = g.get("discussion_date", "2026-09-30")
            
            # Tool call 1: Generate Prompts
            global_metrics_hook.on_tool_call(self.name, "generate_discussion_prompts", {"book_title": title, "author": author, "section": section})
            prompts = generate_discussion_prompts(book_title=title, author=author, section=section)
            
            # Tool call 2: Draft Discussion Post
            global_metrics_hook.on_tool_call(self.name, "draft_group_discussion_post", {"group_name": group_name, "book_title": title})
            draft = draft_group_discussion_post(group_name=group_name, book_title=title, prompts=prompts, meeting_date=m_date)
            drafts.append(draft)
            
            # Queue HITL approval for posting
            req = request_human_approval(
                action_type=ActionType.POST_BOOKCLUB_UPDATE,
                title=f"Post Goodreads Club Discussion: '{group_name}'",
                description=f"Drafted discussion thread for '{title}' (Meeting Date: {m_date}). Review prompts and approve forum publish.",
                payload={
                    "group_id": g.get("group_id"),
                    "group_name": group_name,
                    "post_body": draft["post_body"]
                },
                risk_level=RiskLevel.LOW
            )
            approval_requests.append(req)
            
        summary = f"Drafted discussion threads for {len(groups)} book club groups. Queued for human approval."
        global_metrics_hook.on_turn_complete(self.name, 0.48, summary)
        
        return {
            "agent": self.name,
            "drafts": drafts,
            "approval_requests": approval_requests,
            "summary": summary
        }
