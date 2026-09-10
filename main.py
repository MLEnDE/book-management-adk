"""
Main Execution Entry Point for ADK Book Management Multi-Agent System.
Simulates end-to-end multi-agent orchestration, HITL approval resolution, and audit reporting.
"""

import sys
import os

# Ensure package path is resolved
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

from book_management_adk.agents.orchestrator import MasterBookConciergeOrchestrator
from book_management_adk.tools.hitl_tools import list_pending_approvals
from book_management_adk.hooks.observability_hooks import global_metrics_hook


def main():
    print("=" * 80)
    print("🚀 INITIALIZING ADK MULTI-AGENT BOOK MANAGEMENT SYSTEM")
    print("   Connecting: Goodreads ↔️ Libby ↔️ Amazon Kindle Deals ↔️ Book Clubs")
    print("=" * 80)
    print()

    # Instantiate Orchestrator
    orchestrator = MasterBookConciergeOrchestrator()
    
    # 1. Run full workflow cycle across subagents
    print("🔄 [PHASE 1] RUNNING MULTI-AGENT DISCOVERY & SYNCHRONIZATION CYCLE...")
    report = orchestrator.run_full_workflow_cycle()
    print()
    print(report.summary_markdown)
    
    # 2. Inspect HITL Approval Queue
    pending = list_pending_approvals()
    print("=" * 80)
    print(f"🛑 [PHASE 2] HUMAN-IN-THE-LOOP (HITL) INTERACTIVE APPROVAL GATE")
    print(f"   Found {len(pending)} pending action(s) requiring human confirmation.")
    print("=" * 80)
    print()
    
    # Simulate User Approvals for Demonstration
    for idx, req in enumerate(pending):
        req_id = req["request_id"]
        title = req["title"]
        act_type = req["action_type"]
        
        print(f"👉 Reviewing Item #{idx+1} ID [{req_id}]")
        print(f"   Action: {act_type}")
        print(f"   Title:  {title}")
        print(f"   Details: {req['description']}")
        
        # Simulate user decision (Approving Item 1 & 2, rejecting 3 for demo)
        if idx == 0:
            user_decision = True
            user_note = "Auto-approved Libby hold for Kindle delivery."
        elif idx == 1:
            user_decision = True
            user_note = "Great deal price! Approved Kindle 1-click purchase."
        else:
            user_decision = True
            user_note = "Approved discussion prompts for Goodreads Group."
            
        print(f"   👤 User Input: {'APPROVED' if user_decision else 'REJECTED'} ({user_note})")
        
        # Process decision through orchestrator
        res = orchestrator.process_user_approval_decision(req_id, user_decision, user_note)
        if res.get("execution_result"):
            print(f"   ✅ Execution Output: {res['execution_result']['message']}")
        else:
            print(f"   ❌ Execution Output: Action rejected or cancelled.")
        print("-" * 60)
        print()
        
    # 3. Print Execution & Observability Summary
    print("=" * 80)
    print("📊 [PHASE 3] ADK SYSTEM OBSERVABILITY & AUDIT SUMMARY")
    metrics = global_metrics_hook.get_summary()
    print(f"   Total Agent Turns: {metrics['total_turns']}")
    print(f"   Total Tool Invocations: {metrics['total_tool_calls']}")
    print(f"   Total Cycle Latency: {metrics['total_duration_sec']} seconds")
    print(f"   Audit Log Recorded Events: {metrics['audit_log_entries']}")
    print("=" * 80)
    print("✨ ADK Multi-Agent Workflow Completed Successfully!")


if __name__ == "__main__":
    main()
