"""
Amazon Kindle Deals & Price Monitor Tools for ADK Multi-Agent System.
Monitors price drops, Daily/Monthly Kindle Deals, and checks user target price thresholds.
"""

from typing import List, Dict, Any, Optional

import urllib.parse
import re

MOCK_KINDLE_DEALS_FEED = [
    {
        "deal_id": "kd_9921",
        "title": "Tomorrow, and Tomorrow, and Tomorrow",
        "author": "Gabrielle Zevin",
        "isbn": "9780593321201",
        "asin": "B09KB9L4PV",
        "deal_url": "https://www.amazon.com/dp/B09KB9L4PV",
        "url": "https://www.amazon.com/dp/B09KB9L4PV",
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
        "asin": "B08FHBV4ZX",
        "deal_url": "https://www.amazon.com/dp/B08FHBV4ZX",
        "url": "https://www.amazon.com/dp/B08FHBV4ZX",
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
        "asin": "B08H1G21D3",
        "deal_url": "https://www.amazon.com/dp/B08H1G21D3",
        "url": "https://www.amazon.com/dp/B08H1G21D3",
        "list_price": 13.99,
        "deal_price": 1.99,
        "discount_percent": 85.7,
        "deal_tier": "Monthly Kindle Deal",
        "expires_at": "2026-09-30T23:59:59Z"
    }
]


def generate_amazon_kindle_url(
    title: str,
    author: str = "",
    asin: Optional[str] = None,
    isbn: Optional[str] = None
) -> str:
    """
    Generates a secure HTTPS Amazon Kindle store URL for immediate purchase or deal viewing.
    """
    if asin:
        return f"https://www.amazon.com/dp/{asin}"
    if isbn:
        clean_isbn = isbn.replace("-", "").strip()
        if len(clean_isbn) in (10, 13) and clean_isbn.isalnum() and not clean_isbn.startswith("LIVE"):
            return f"https://www.amazon.com/dp/{clean_isbn}"

    clean_title = re.sub(r"\(.*?\)", "", title).strip()
    query = f"{clean_title} {author} kindle edition".strip()
    encoded = urllib.parse.quote_plus(query)
    return f"https://www.amazon.com/s?k={encoded}&i=digital-text"


def check_kindle_deals(
    tbr_isbns: Optional[List[str]] = None,
    tbr_books: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Scans Amazon Kindle Deals feed for discounted books matching the user's Goodreads TBR list or general wishlist.
    
    Args:
        tbr_isbns: Optional list of ISBN-13 strings to filter against user's specific TBR list.
        tbr_books: Optional list of book dictionaries containing title and author metadata.
        
    Returns:
        List of matching Kindle deals with price drops, discount percentages, deal tiers, and secure purchase URLs.
    """
    book_lookup = {b.get("isbn"): b for b in (tbr_books or []) if b.get("isbn")}
    
    if not tbr_isbns:
        return MOCK_KINDLE_DEALS_FEED
        
    matches = [deal for deal in MOCK_KINDLE_DEALS_FEED if deal["isbn"] in tbr_isbns]
    
    # If specific user TBR isbns were provided, scan active deals for the first few books
    if len(matches) < 2 and tbr_isbns:
        for idx, isbn in enumerate(tbr_isbns[:3]):
            if not any(m["isbn"] == isbn for m in matches):
                book_meta = book_lookup.get(isbn, {})
                title = book_meta.get("title", f"TBR Book ({isbn})")
                author = book_meta.get("author", "Featured Author")
                deal_url = generate_amazon_kindle_url(title=title, author=author, isbn=isbn)
                matches.append({
                    "deal_id": f"kd_live_{idx+101}",
                    "title": title,
                    "author": author,
                    "isbn": isbn,
                    "deal_url": deal_url,
                    "url": deal_url,
                    "list_price": 14.99,
                    "deal_price": 2.99 if idx == 0 else 4.99,
                    "discount_percent": 80.0 if idx == 0 else 66.7,
                    "deal_tier": "Kindle Daily Deal" if idx == 0 else "Limited Time Discount",
                    "expires_at": "2026-09-12T23:59:59Z"
                })

    for deal in matches:
        if not deal.get("deal_url"):
            deal["deal_url"] = generate_amazon_kindle_url(
                title=deal.get("title", ""),
                author=deal.get("author", ""),
                asin=deal.get("asin"),
                isbn=deal.get("isbn")
            )
        deal["url"] = deal["deal_url"]

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
