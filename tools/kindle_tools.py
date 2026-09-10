"""
Amazon Kindle Deals & Price Monitor Tools for ADK Multi-Agent System.
Monitors price drops, Daily/Monthly Kindle Deals, and checks user target price thresholds.
"""

from typing import List, Dict, Any, Optional

MOCK_KINDLE_DEALS_FEED = [
    {
        "deal_id": "kd_9921",
        "title": "Tomorrow, and Tomorrow, and Tomorrow",
        "author": "Gabrielle Zevin",
        "isbn": "9780593321201",
        "list_price": 14.99,
        "deal_price": 2.99,
        "discount_percent": 80.0,
        "deal_tier": "Kindle Daily Deal",
        "expires_at": "2026-09-10T23:59:59Z"
    },
    {
        "deal_id": "kd_9922",
        "title": "Project Hail Mary",
        "author": "Andy Weir",
        "isbn": "9780593135204",
        "list_price": 16.99,
        "deal_price": 4.99,
        "discount_percent": 70.6,
        "deal_tier": "Limited Time Discount",
        "expires_at": "2026-09-12T23:59:59Z"
    },
    {
        "deal_id": "kd_9923",
        "title": "Klara and the Sun",
        "author": "Kazuo Ishiguro",
        "isbn": "9780593318171",
        "list_price": 13.99,
        "deal_price": 1.99,
        "discount_percent": 85.7,
        "deal_tier": "Monthly Kindle Deal",
        "expires_at": "2026-09-30T23:59:59Z"
    }
]


def check_kindle_deals(tbr_isbns: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Scans Amazon Kindle Deals feed for discounted books matching the user's Goodreads TBR list or general wishlist.
    
    Args:
        tbr_isbns: Optional list of ISBN-13 strings to filter against user's specific TBR list.
        
    Returns:
        List of matching Kindle deals with price drops, discount percentages, and deal tiers.
    """
    if not tbr_isbns:
        return MOCK_KINDLE_DEALS_FEED
        
    matches = [deal for deal in MOCK_KINDLE_DEALS_FEED if deal["isbn"] in tbr_isbns]
    return matches


def evaluate_deal_threshold(list_price: float, deal_price: float, target_discount_pct: float = 50.0) -> Dict[str, Any]:
    """
    Evaluates whether a Kindle deal price meets the user's criteria for purchase recommendation.
    
    Args:
        list_price: Original price ($).
        deal_price: Current discounted price ($).
        target_discount_pct: Minimum discount percentage threshold (default 50%).
        
    Returns:
        Evaluation report with recommendation status and savings calculation.
    """
    savings = list_price - deal_price
    discount_pct = (savings / list_price) * 100.0 if list_price > 0 else 0.0
    recommended = discount_pct >= target_discount_pct or deal_price <= 2.99
    
    return {
        "recommended": recommended,
        "discount_pct": round(discount_pct, 1),
        "savings_usd": round(savings, 2),
        "deal_price": deal_price,
        "reason": f"Discount of {round(discount_pct, 1)}% meets target threshold of {target_discount_pct}%." if recommended else "Discount below threshold."
    }


def execute_kindle_deal_purchase(deal_id: str, title: str, price: float) -> Dict[str, Any]:
    """
    Executes 1-Click Amazon Kindle purchase for a book deal.
    Note: Requires explicit HITL human approval before execution.
    """
    return {
        "success": True,
        "transaction_id": f"amzn_tx_{deal_id}",
        "title": title,
        "price_paid": price,
        "delivered_to": "Kindle Cloud Reader & Emily's Kindle Paperwhite",
        "message": f"Successfully purchased '{title}' for ${price:.2f}! Sent to Kindle."
    }
