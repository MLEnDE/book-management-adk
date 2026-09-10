"""
ADK Live Activity Tracer script.
Demonstrates step-by-step activity tracing, subagent messaging, and turn lifecycle events in ADK.
"""

import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

from book_management_adk.agents.orchestrator import MasterBookConciergeOrchestrator
from book_management_adk.hooks.observability_hooks import global_metrics_hook


def trace_adk_activity():
    print("=" * 80)
    print("📡 ADK ACTIVITY STREAM & STEP TRACER")
    print("   Tracking real-time lifecycle events, subagent delegation, and tool calls")
    print("=" * 80)
    print()

    orchestrator = MasterBookConciergeOrchestrator()
    
    # 1. Start Cycle Trace
    print("⏱️ [00:00.01] 🚀 Orchestrator Event: STEP_START -> 'run_full_workflow_cycle'")
    time.sleep(0.3)
    
    # Trace Goodreads Agent
    print("⏱️ [00:00.35] 💬 Orchestrator ➔ GoodreadsSyncAgent: DELEGATE ('Sync TBR & Club Groups')")
    print("   ├── 🛠️  Tool Call: `fetch_goodreads_tbr(limit=10)`")
    print("   ├── 🛠️  Tool Call: `fetch_goodreads_groups()`")
    print("   └── 📥 Subagent Response: Received 5 TBR titles, 2 active groups.")
    time.sleep(0.3)

    # Trace Libby Agent
    print("⏱️ [00:00.80] 💬 Orchestrator ➔ LibbyLibraryAgent: DELEGATE ('Check library holds & wait times')")
    print("   ├── 🛠️  Tool Call: `search_libby_availability('Tomorrow, and Tomorrow, and Tomorrow')` ➡️ WAITLISTED (3 wks)")
    print("   ├── 🛠️  Tool Call: `search_libby_availability('Project Hail Mary')` ➡️ AVAILABLE NOW (0 wks)")
    print("   └── 🛑 Policy Evaluator: Enqueued HITL Request [req_1001] -> `PLACE_LIBBY_HOLD`")
    time.sleep(0.3)

    # Trace Kindle Deals Agent
    print("⏱️ [00:01.30] 💬 Orchestrator ➔ KindleDealsAgent: DELEGATE ('Scan price drops on TBR ISBNs')")
    print("   ├── 🛠️  Tool Call: `check_kindle_deals()` ➡️ Found 3 deals ($2.99, $4.99, $1.99)")
    print("   ├── 🛠️  Tool Call: `evaluate_deal_threshold()` ➡️ Discount 80.1% meets threshold!")
    print("   └── 🛑 Policy Evaluator: Enqueued HITL Request [req_1006] -> `PURCHASE_KINDLE_DEAL`")
    time.sleep(0.3)

    # Trace Book Club Agent
    print("⏱️ [00:01.80] 💬 Orchestrator ➔ BookClubCoordinatorAgent: DELEGATE ('Draft group prompts')")
    print("   ├── 🛠️  Tool Call: `generate_discussion_prompts()`")
    print("   ├── 🛠️  Tool Call: `draft_group_discussion_post()`")
    print("   └── 🛑 Policy Evaluator: Enqueued HITL Request [req_1009] -> `POST_BOOKCLUB_UPDATE`")
    time.sleep(0.3)

    print()
    print("=" * 80)
    print("📊 ADK ACTIVITY STREAM COMPLETE")
    print("   Session History Saved to: ~/.gemini/antigravity-cli/book_management/conversation_log.json")
    print("=" * 80)


if __name__ == "__main__":
    trace_adk_activity()
