"""
Observability and Audit Hooks for ADK Multi-Agent System.
Implements lifecycle hooks, safety policy enforcement, and audit tracing.
"""

import time
import logging
from typing import Dict, Any, Callable

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ADK_BookManagement")


class ExecutionMetricsHook:
    """Tracks token usage, turn execution duration, and tool call invocations."""
    
    def __init__(self):
        self.turns_count = 0
        self.tool_calls_count = 0
        self.total_duration = 0.0
        self.audit_log = []

    def on_turn_start(self, agent_name: str, turn_index: int, prompt_summary: str):
        self.turns_count += 1
        logger.info(f"🟢 [TURN START] Agent: '{agent_name}' | Turn #{turn_index} | Prompt: '{prompt_summary[:60]}...'")

    def on_tool_call(self, agent_name: str, tool_name: str, args: Dict[str, Any]):
        self.tool_calls_count += 1
        logger.info(f"🛠️  [TOOL INVOKED] Agent: '{agent_name}' | Tool: '{tool_name}' | Args: {args}")
        self.audit_log.append({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "agent": agent_name,
            "tool": tool_name,
            "args": args
        })

    def on_turn_complete(self, agent_name: str, duration_sec: float, response_summary: str):
        self.total_duration += duration_sec
        logger.info(f"🏁 [TURN COMPLETE] Agent: '{agent_name}' | Duration: {duration_sec:.2f}s | Output: '{response_summary[:60]}...'")

    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_turns": self.turns_count,
            "total_tool_calls": self.tool_calls_count,
            "total_duration_sec": round(self.total_duration, 2),
            "audit_log_entries": len(self.audit_log)
        }


# Global hook instance
global_metrics_hook = ExecutionMetricsHook()


def policy_predicate_check_hitl(tool_name: str, args: Dict[str, Any]) -> bool:
    """
    ADK Policy predicate that determines if a tool call requires Human-In-The-Loop confirmation.
    Returns True if the tool requires HITL sign-off.
    """
    sensitive_tools = ["place_libby_hold", "execute_kindle_deal_purchase", "publish_goodreads_group_post"]
    return tool_name in sensitive_tools
