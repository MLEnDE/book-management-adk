"""
Kindle Deals Subagent Definition for ADK Multi-Agent System.
Specializes in tracking Amazon Kindle Deals, price drops, and submitting purchase recommendations.
"""

from typing import Dict, Any, List, Optional
from book_management_adk.tools.kindle_tools import check_kindle_deals, evaluate_deal_threshold
from book_management_adk.tools.hitl_tools import request_human_approval
from book_management_adk.models.schemas import ActionType, RiskLevel
from book_management_adk.hooks.observability_hooks import global_metrics_hook


class KindleAgent:
    """Subagent responsible for scanning Kindle deal feeds and queueing deal purchase recommendations."""
    
    def __init__(self, name: str = "KindleDealsAgent"):
        self.name = name
        self.system_instructions = (
            "You are the Kindle Deals Specialist. You monitor Amazon's daily and monthly "
            "Kindle price drops against the user's Goodreads TBR list and submit high-value "
            "purchase recommendations for Human-In-The-Loop confirmation."
        )

    def scan_and_evaluate_deals(
        self,
        tbr_isbns: List[str],
        tbr_books: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Scans Kindle deals for books on the user's TBR list and evaluates discount thresholds."""
        global_metrics_hook.on_turn_start(self.name, 1, f"Scan Kindle deals for {len(tbr_isbns)} TBR ISBNs")
        
        global_metrics_hook.on_tool_call(self.name, "check_kindle_deals", {"tbr_isbns": tbr_isbns})
        deals = check_kindle_deals(tbr_isbns=tbr_isbns, tbr_books=tbr_books)
        
        evaluated_deals = []
        approval_requests = []
        
        for d in deals:
            list_p = d["list_price"]
            deal_p = d["deal_price"]
            
            global_metrics_hook.on_tool_call(self.name, "evaluate_deal_threshold", {"list_price": list_p, "deal_price": deal_p})
            eval_res = evaluate_deal_threshold(list_price=list_p, deal_price=deal_p, target_discount_pct=50.0)
            
            deal_info = {**d, "evaluation": eval_res}
            evaluated_deals.append(deal_info)
            
            if eval_res["recommended"]:
                title = d["title"]
                deal_url = d.get("deal_url") or d.get("url", "")
                req = request_human_approval(
                    action_type=ActionType.PURCHASE_KINDLE_DEAL,
                    title=f"Kindle Deal Recommendation: '{title}' (${deal_p:.2f})",
                    description=(
                        f"Price drop on TBR book '{title}'! "
                        f"Original: ${list_p:.2f} ➡️ Now: ${deal_p:.2f} ({eval_res['discount_pct']}% OFF). "
                        f"Tier: {d['deal_tier']}. Expiration: {d.get('expires_at', 'Tonight')}."
                        f"\nPurchase Link: {deal_url}"
                    ),
                    payload={
                        "deal_id": d["deal_id"],
                        "title": title,
                        "deal_price": deal_p,
                        "list_price": list_p,
                        "discount_pct": eval_res["discount_pct"],
                        "deal_url": deal_url,
                        "url": deal_url
                    },
                    risk_level=RiskLevel.MEDIUM
                )
                approval_requests.append(req)
                
        summary = f"Found {len(deals)} matching Kindle deals. Queued {len(approval_requests)} purchase recommendations for human approval."
        global_metrics_hook.on_turn_complete(self.name, 0.52, summary)
        
        return {
            "agent": self.name,
            "evaluated_deals": evaluated_deals,
            "approval_requests": approval_requests,
            "summary": summary
        }
