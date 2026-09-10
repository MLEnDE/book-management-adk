"""
Goodreads Sync Subagent Definition for ADK Multi-Agent System.
Specializes in tracking Goodreads TBR shelves, group discussions, and user reading goals.
"""

from typing import Dict, Any, List
from book_management_adk.tools.goodreads_tools import (
    fetch_goodreads_tbr,
    fetch_goodreads_groups,
    update_goodreads_shelf
)
from book_management_adk.hooks.observability_hooks import global_metrics_hook


class GoodreadsAgent:
    """Subagent responsible for syncing Goodreads data and group reading lists."""
    
    def __init__(self, name: str = "GoodreadsSyncAgent"):
        self.name = name
        self.system_instructions = (
            "You are the Goodreads Sync Specialist. Your responsibility is to monitor "
            "the user's 'Want to Read' shelf, track active Goodreads Book Club groups, "
            "and synchronize reading statuses."
        )

    def run_sync_task(self) -> Dict[str, Any]:
        """Executes a full Goodreads sync cycle."""
        global_metrics_hook.on_turn_start(self.name, 1, "Sync Goodreads TBR and Group lists")
        
        # Tool call 1: Fetch TBR shelf
        global_metrics_hook.on_tool_call(self.name, "fetch_goodreads_tbr", {"limit": 10})
        tbr_books = fetch_goodreads_tbr(limit=10)
        
        # Tool call 2: Fetch Active Groups
        global_metrics_hook.on_tool_call(self.name, "fetch_goodreads_groups", {})
        groups = fetch_goodreads_groups()
        
        summary = f"Fetched {len(tbr_books)} books from 'Want to Read' shelf and {len(groups)} active book club groups."
        global_metrics_hook.on_turn_complete(self.name, 0.45, summary)
        
        return {
            "agent": self.name,
            "tbr_books": tbr_books,
            "groups": groups,
            "summary": summary
        }
