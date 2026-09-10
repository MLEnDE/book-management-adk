"""
Libby / US OverDrive Library Integration Tools for ADK Multi-Agent System.
Provides tools to query digital library collections, check holds, estimate wait times, and route Kindle books.
"""

from typing import List, Dict, Any, Optional


MOCK_LIBRARY_CATALOG = {
    "9780593321201": { # Tomorrow, and Tomorrow, and Tomorrow
        "library_system": "New York Public Library",
        "status": "waitlisted",
        "wait_time_weeks": 3,
        "queue_position": 14,
        "total_copies": 25,
        "kindle_compatible": True
    },
    "9780593135204": { # Project Hail Mary
        "library_system": "Chicago Public Library",
        "status": "available_now",
        "wait_time_weeks": 0,
        "queue_position": 0,
        "total_copies": 40,
        "kindle_compatible": True
    },
    "9780063251922": { # Demon Copperhead
        "library_system": "Seattle Public Library",
        "status": "waitlisted",
        "wait_time_weeks": 1,
        "queue_position": 2,
        "total_copies": 30,
        "kindle_compatible": True
    },
    "9780593318171": { # Klara and the Sun
        "library_system": "San Francisco Public Library",
        "status": "available_now",
        "wait_time_weeks": 0,
        "queue_position": 0,
        "total_copies": 15,
        "kindle_compatible": True
    },
    "9780593422946": { # The Heaven & Earth Grocery Store
        "library_system": "Boston Public Library",
        "status": "waitlisted",
        "wait_time_weeks": 6,
        "queue_position": 48,
        "total_copies": 10,
        "kindle_compatible": True
    }
}

ACTIVE_USER_HOLDS = []


def search_libby_availability(title: str, isbn: Optional[str] = None) -> Dict[str, Any]:
    """
    Queries linked US library systems in Libby for digital Kindle edition availability and wait times.
    
    Args:
        title: Book title.
        isbn: ISBN-13 string if available.
        
    Returns:
        Availability report including status, wait time in weeks, and copy counts.
    """
    if isbn and isbn in MOCK_LIBRARY_CATALOG:
        match = MOCK_LIBRARY_CATALOG[isbn]
        return {
            "found": True,
            "title": title,
            "isbn": isbn,
            "library_system": match["library_system"],
            "status": match["status"],
            "wait_time_weeks": match["wait_time_weeks"],
            "queue_position": match["queue_position"],
            "total_copies": match["total_copies"],
            "kindle_compatible": match["kindle_compatible"]
        }
    
    # Fallback search by title key substring
    for key_isbn, data in MOCK_LIBRARY_CATALOG.items():
        if title.lower() in "project hail mary tomorrow demon copperhead klara heaven".lower():
            return {
                "found": True,
                "title": title,
                "isbn": key_isbn,
                "library_system": data["library_system"],
                "status": data["status"],
                "wait_time_weeks": data["wait_time_weeks"],
                "queue_position": data["queue_position"],
                "total_copies": data["total_copies"],
                "kindle_compatible": data["kindle_compatible"]
            }
            
    return {
        "found": False,
        "title": title,
        "status": "not_in_catalog",
        "message": "Title not found in linked library systems."
    }


def place_libby_hold(title: str, library_system: str, isbn: str) -> Dict[str, Any]:
    """
    Places a digital hold on Libby for a library book.
    Note: Requires HITL approval prior to execution in automated workflows.
    
    Args:
        title: Book title.
        library_system: Library system branch name.
        isbn: ISBN-13 identifier.
        
    Returns:
        Hold confirmation details.
    """
    hold_record = {
        "hold_id": f"libby_hold_{len(ACTIVE_USER_HOLDS) + 101}",
        "title": title,
        "isbn": isbn,
        "library_system": library_system,
        "status": "hold_placed",
        "deliver_to_device": "Kindle Reader (Emily's Kindle)"
    }
    ACTIVE_USER_HOLDS.append(hold_record)
    return {
        "success": True,
        "hold": hold_record,
        "message": f"Successfully placed hold for '{title}' at {library_system}. Will automatically deliver to Kindle when ready."
    }


def get_active_libby_holds() -> List[Dict[str, Any]]:
    """
    Returns all active library holds and active loans currently on the user's Libby account.
    """
    return ACTIVE_USER_HOLDS
