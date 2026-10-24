from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import FindingStatus, FindingType, Severity, Verdict


class ReviewCreate(BaseModel):
    kit_id: str
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=50000)
    content_type: str = "general"


class RevisionIn(BaseModel):
    content: str = Field(min_length=1, max_length=50000)


class AnalyzeIn(BaseModel):
    evaluation_date: date | None = None


class FindingUpdate(BaseModel):
    status: FindingStatus
    final_text: str | None = Field(default=None, max_length=5000)


class DecisionIn(BaseModel):
    decision: Literal["approve", "request_changes", "reject"]
    version_number: int
    reason: str | None = Field(default=None, max_length=2000)


class CommentIn(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class RawFinding(BaseModel):
    """Shape we require from the AI. Anything else is rejected before display."""
    model_config = ConfigDict(extra="ignore")
    type: FindingType
    quoted_text: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    severity: Severity
    verdict: Verdict | None = None
    source_ids: list[str] = []
    source_quote: str | None = None
    suggested_fix: str | None = None
    replacement: str | None = None
    uncertainty: str | None = None


class ImageUpdate(BaseModel):
    alt_text: str | None = Field(default=None, max_length=500)
    text_color: str | None = Field(default=None, max_length=7)
    bg_color: str | None = Field(default=None, max_length=7)


class RequestReviewIn(BaseModel):
    reviewer_id: str | None = None


class GoogleDocReview(BaseModel):
    kit_id: str
    url: str = Field(min_length=10, max_length=500)
    title: str | None = Field(default=None, max_length=200)
    content_type: str = "document"


class SuggestionIn(BaseModel):
    version_number: int
    start: int = Field(ge=0)
    end: int = Field(ge=1)
    replacement: str = Field(max_length=5000)
    note: str = Field(min_length=1, max_length=1000)


class ReviewerEditIn(BaseModel):
    content: str = Field(min_length=1, max_length=50000)
    version_number: int
    note: str = Field(min_length=1, max_length=1000)


class StartReviewIn(BaseModel):
    rerun: bool = False


class TriageIn(BaseModel):
    action: Literal["flag", "dismiss", "reopen"]
