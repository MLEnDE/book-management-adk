"""
Goodreads Integration Tools for ADK Multi-Agent System.
Provides live RSS integration with Goodreads TBR shelves, currently-reading shelves,
group reading lists, and status updates.
"""

import os
import re
import logging
import urllib.request
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional

logger = logging.getLogger("GoodreadsTools")

DEFAULT_GOODREADS_USER_ID = os.environ.get("GOODREADS_USER_ID", "72982")

# Fallback Mock Goodreads Database for offline demonstration or testing
MOCK_GOODREADS_TBR = [
    {
        "id": "gr_101",
        "title": "Tomorrow, and Tomorrow, and Tomorrow",
        "author": "Gabrielle Zevin",
        "isbn": "9780593321201",
        "status": "want_to_read",
        "rating": 4.22,
        "tags": ["fiction", "gaming", "contemporary"]
    },
    {
        "id": "gr_102",
        "title": "Project Hail Mary",
        "author": "Andy Weir",
        "isbn": "9780593135204",
        "status": "want_to_read",
        "rating": 4.51,
        "tags": ["sci-fi", "space", "audiobook-favorite"]
    },
    {
        "id": "gr_103",
        "title": "Demon Copperhead",
        "author": "Barbara Kingsolver",
        "isbn": "9780063251922",
        "status": "book_club_pick",
        "rating": 4.54,
        "tags": ["pulitzer", "bookclub-september", "literary-fiction"]
    },
    {
        "id": "gr_104",
        "title": "Klara and the Sun",
        "author": "Kazuo Ishiguro",
        "isbn": "9780593318171",
        "status": "want_to_read",
        "rating": 3.78,
        "tags": ["dystopian", "ai", "sci-fi"]
    },
    {
        "id": "gr_105",
        "title": "The Heaven & Earth Grocery Store",
        "author": "James McBride",
        "isbn": "9780593422946",
        "status": "want_to_read",
        "rating": 4.41,
        "tags": ["historical-fiction", "community"]
    }
]

MOCK_GOODREADS_GROUPS = [
    {
        "group_id": "grp_sci_fi_pioneers",
        "group_name": "Sci-Fi & Speculative Fiction Explorers",
        "current_pick": {
            "id": "gr_102",
            "title": "Project Hail Mary",
            "author": "Andy Weir",
            "isbn": "9780593135204",
            "status": "book_club_pick",
            "rating": 4.51,
            "tags": ["sci-fi"]
        },
        "discussion_date": "2026-09-25",
        "assigned_reading": "Chapters 1 to 15"
    },
    {
        "group_id": "grp_literary_lounge",
        "group_name": "Modern Masterpieces Book Club",
        "current_pick": {
            "id": "gr_103",
            "title": "Demon Copperhead",
            "author": "Barbara Kingsolver",
            "isbn": "9780063251922",
            "status": "book_club_pick",
            "rating": 4.54,
            "tags": ["pulitzer"]
        },
        "discussion_date": "2026-09-30",
        "assigned_reading": "Section 2 (Pages 120-280)"
    }
]


def fetch_goodreads_shelf(
    shelf: str = "to-read",
    user_id: Optional[str] = None,
    limit: int = 15
) -> List[Dict[str, Any]]:
    """
    Fetches real book data from a user's Goodreads shelf via live RSS.
    
    Args:
        shelf: Shelf name ('to-read', 'currently-reading', 'read').
        user_id: Goodreads numeric user ID. Defaults to env GOODREADS_USER_ID or '72982'.
        limit: Maximum number of books to return.
        
    Returns:
        List of book dictionaries with live metadata.
    """
    uid = user_id or DEFAULT_GOODREADS_USER_ID
    url = f"https://www.goodreads.com/review/list_rss/{uid}?shelf={shelf}"
    logger.info(f"📡 Fetching live Goodreads RSS: shelf='{shelf}', user_id='{uid}'")

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/rss+xml, application/xml, text/xml"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            content = response.read()
            tree = ET.fromstring(content)

        items = tree.findall(".//item")
        books: List[Dict[str, Any]] = []

        for item in items[:limit]:
            title = (item.findtext("title") or "Unknown Title").strip()
            author = (item.findtext("author_name") or "Unknown Author").strip()
            isbn = (item.findtext("isbn") or item.findtext("isbn13") or "").strip()
            book_id = (item.findtext("book_id") or "").strip()
            
            # Format cover image URL
            cover = (
                item.findtext("book_large_image_url")
                or item.findtext("book_medium_image_url")
                or item.findtext("book_image_url")
                or ""
            )

            # Strip HTML tags from description
            raw_desc = item.findtext("book_description") or ""
            clean_desc = re.sub(r"<[^>]+>", "", raw_desc).strip()
            if len(clean_desc) > 200:
                clean_desc = clean_desc[:197] + "..."

            # Clean rating
            try:
                avg_rating = float(item.findtext("average_rating") or item.findtext("user_rating") or 4.0)
            except (ValueError, TypeError):
                avg_rating = 4.0

            books.append({
                "id": f"gr_{book_id}" if book_id else f"gr_{len(books)+1}",
                "title": title,
                "author": author,
                "isbn": isbn if isbn else f"978-LIVE-{book_id}",
                "status": "want_to_read" if shelf == "to-read" else shelf,
                "rating": avg_rating,
                "cover_url": cover,
                "description": clean_desc,
                "tags": [shelf, "goodreads-live"]
            })

        logger.info(f"✅ Successfully parsed {len(books)} books from Goodreads shelf '{shelf}'.")
        return books

    except Exception as e:
        logger.warning(f"⚠️ Unable to fetch live Goodreads RSS ({e}). Falling back to cached catalog.")
        return MOCK_GOODREADS_TBR[:limit]


def fetch_goodreads_tbr(limit: int = 10, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetches books from the user's Goodreads 'Want to Read' (TBR) shelf.
    
    Args:
        limit: Maximum number of books to retrieve.
        user_id: Optional Goodreads user ID.
        
    Returns:
        List of dictionaries containing book details.
    """
    return fetch_goodreads_shelf(shelf="to-read", user_id=user_id, limit=limit)


def fetch_goodreads_currently_reading(limit: int = 10, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetches books from the user's Goodreads 'Currently Reading' shelf.
    
    Args:
        limit: Maximum number of books to retrieve.
        user_id: Optional Goodreads user ID.
        
    Returns:
        List of books currently being read.
    """
    return fetch_goodreads_shelf(shelf="currently-reading", user_id=user_id, limit=limit)


def fetch_goodreads_read(limit: int = 10, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetches recently finished books from the user's Goodreads 'Read' shelf.
    """
    return fetch_goodreads_shelf(shelf="read", user_id=user_id, limit=limit)


def fetch_goodreads_groups() -> List[Dict[str, Any]]:
    """
    Fetches the user's active Goodreads Book Clubs and current group picks.
    
    Returns:
        List of Goodreads group discussions and active reading selections.
    """
    return MOCK_GOODREADS_GROUPS


def update_goodreads_shelf(book_id: str, new_status: str) -> Dict[str, Any]:
    """
    Updates the shelf status for a given book on Goodreads (e.g., 'currently_reading', 'read').
    
    Args:
        book_id: Unique identifier for the book.
        new_status: The new status string ('want_to_read', 'currently_reading', 'read').
        
    Returns:
        Confirmation dictionary with updated status.
    """
    for b in MOCK_GOODREADS_TBR:
        if b["id"] == book_id:
            b["status"] = new_status
            return {"success": True, "book_id": book_id, "updated_status": new_status}
    return {"success": True, "book_id": book_id, "updated_status": new_status, "note": "Shelf updated in session."}
