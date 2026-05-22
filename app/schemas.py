"""Pydantic schemas with validation."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class ActionItemBase(BaseModel):
    task: str = Field(..., min_length=1, max_length=5000, description="Task description")
    owner: Optional[str] = Field(None, max_length=200, description="Person responsible")
    deadline: Optional[str] = Field(None, max_length=100, description="Deadline")
    priority: str = Field("medium", pattern="^(low|medium|high)$", description="Priority level")
    status: str = Field("pending", pattern="^(pending|in_progress|completed|blocked)$", description="Status")


class ActionItemCreate(ActionItemBase):
    pass


class ActionItemUpdate(BaseModel):
    task: Optional[str] = Field(None, min_length=1, max_length=5000)
    owner: Optional[str] = Field(None, max_length=200)
    deadline: Optional[str] = Field(None, max_length=100)
    priority: Optional[str] = Field(None, pattern="^(low|medium|high)$")
    status: Optional[str] = Field(None, pattern="^(pending|in_progress|completed|blocked)$")


class ActionItemResponse(ActionItemBase):
    id: int
    meeting_id: int
    linear_issue_id: Optional[str] = None
    related_items: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MeetingBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500, description="Meeting title")
    transcript: str = Field(..., min_length=1, max_length=50000, description="Meeting transcript")


class MeetingCreate(MeetingBase):
    pass


class MeetingResponse(MeetingBase):
    id: int
    date: datetime
    created_at: datetime
    action_items: List[ActionItemResponse] = []

    model_config = {"from_attributes": True}


class ExtractedActionItems(BaseModel):
    items: List[ActionItemBase]
    summary: str
