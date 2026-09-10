"""
Data Models and Schemas for ADK Multi-Agent Book Management System.
Defines Pydantic contracts for inter-agent communication and structured outputs.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class FormatType(str, Enum):
    KINDLE = "kindle"
    HARDCOVER = "hardcover"
    PAPERBACK = "paperback"
    AUDIOBOOK = "audiobook"


class BookStatus(str, Enum):
    WANT_TO_READ = "want_to_read"
    READING = "currently_reading"
    READ = "read"
    BOOK_CLUB_PICK = "book_club_pick"


class Book(BaseModel):
    id: str = Field(..., description="Unique Identifier (e.g. ISBN or Goodreads ID)")
    title: str = Field(..., description="Book Title")
    author: str = Field(..., description="Author Name")
    isbn: Optional[str] = Field(None, description="ISBN-13 if available")
    format_preference: FormatType = Field(default=FormatType.KINDLE)
    status: BookStatus = Field(default=BookStatus.WANT_TO_READ)
    rating: Optional[float] = Field(None, description="Goodreads average rating (1.0 - 5.0)")
    tags: List[str] = Field(default_factory=list, description="User or club tags")


class HoldStatus(str, Enum):
    AVAILABLE_NOW = "available_now"
    WAITLISTED = "waitlisted"
    ON_HOLD = "on_hold"
    BORROWED = "borrowed"
    EXPIRED = "expired"


class LibraryHold(BaseModel):
    hold_id: str = Field(..., description="Library transaction ID")
    book: Book
    library_system: str = Field(..., description="Name of participating US library branch")
    status: HoldStatus
    wait_time_weeks: int = Field(0, description="Estimated wait time in weeks")
    queue_position: int = Field(0, description="Current position in queue")
    total_copies: int = Field(1, description="Total library licenses available")
    kindle_compatible: bool = Field(True, description="Supports Libby direct send-to-kindle")


class KindleDeal(BaseModel):
    deal_id: str = Field(..., description="Amazon deal reference ID")
    book: Book
    list_price: float = Field(..., description="Original Kindle list price ($)")
    deal_price: float = Field(..., description="Current discounted price ($)")
    discount_percent: float = Field(..., description="Percentage savings")
    expires_at: Optional[str] = Field(None, description="Deal expiration timestamp")
    deal_tier: str = Field("Daily Deal", description="Daily Deal, Monthly Deal, or Price Drop")


class BookClubPick(BaseModel):
    group_id: str = Field(..., description="Goodreads Group ID")
    group_name: str = Field(..., description="Name of book club")
    book: Book
    meeting_date: str = Field(..., description="Target discussion date (YYYY-MM-DD)")
    assigned_reading: str = Field(..., description="Current target chapters/pages")
    discussion_prompts: List[str] = Field(default_factory=list, description="AI-curated discussion questions")


class ActionType(str, Enum):
    PLACE_LIBBY_HOLD = "place_libby_hold"
    PURCHASE_KINDLE_DEAL = "purchase_kindle_deal"
    POST_BOOKCLUB_UPDATE = "post_bookclub_update"
    SYNC_GOODREADS_SHELF = "sync_goodreads_shelf"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ApprovalRequest(BaseModel):
    request_id: str = Field(..., description="Unique request identifier")
    action_type: ActionType
    title: str = Field(..., description="Human-readable title of requested action")
    description: str = Field(..., description="Detailed explanation of what will occur")
    payload: Dict[str, Any] = Field(..., description="Action metadata and tool arguments")
    risk_level: RiskLevel = Field(default=RiskLevel.MEDIUM)
    auto_approved: bool = Field(False)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class WorkflowReport(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    goodreads_tbr_count: int = 0
    libby_holds_active: int = 0
    kindle_deals_found: int = 0
    book_club_updates_processed: int = 0
    pending_approvals: List[ApprovalRequest] = Field(default_factory=list)
    summary_markdown: str = ""
