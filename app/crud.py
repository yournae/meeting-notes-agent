"""Database CRUD operations."""

from sqlalchemy.orm import Session
from app.models import Meeting, ActionItem, utcnow
from app.schemas import MeetingCreate, ActionItemCreate, ActionItemUpdate
from typing import List, Optional
import json

MAX_PAGINATION_LIMIT = 100


def create_meeting(db: Session, meeting: MeetingCreate) -> Meeting:
    """Create a new meeting record."""
    db_meeting = Meeting(
        title=meeting.title,
        transcript=meeting.transcript,
        date=utcnow()
    )
    db.add(db_meeting)
    db.commit()
    db.refresh(db_meeting)
    return db_meeting


def get_meeting(db: Session, meeting_id: int) -> Optional[Meeting]:
    """Get a meeting by ID."""
    return db.query(Meeting).filter(Meeting.id == meeting_id).first()


def get_all_meetings(db: Session, skip: int = 0, limit: int = 100) -> List[Meeting]:
    """Get all meetings with pagination."""
    limit = min(limit, MAX_PAGINATION_LIMIT)
    return db.query(Meeting).offset(skip).limit(limit).all()


def create_action_item(db: Session, meeting_id: int, item: ActionItemCreate, related_items: Optional[List[int]] = None) -> ActionItem:
    """Create a new action item."""
    db_item = ActionItem(
        meeting_id=meeting_id,
        task=item.task,
        owner=item.owner,
        deadline=item.deadline,
        priority=item.priority,
        status=item.status,
        related_items=json.dumps(related_items) if related_items else None
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def get_action_item(db: Session, item_id: int) -> Optional[ActionItem]:
    """Get an action item by ID."""
    return db.query(ActionItem).filter(ActionItem.id == item_id).first()


def get_action_items_by_meeting(db: Session, meeting_id: int) -> List[ActionItem]:
    """Get all action items for a meeting."""
    return db.query(ActionItem).filter(ActionItem.meeting_id == meeting_id).all()


def get_all_action_items(db: Session, skip: int = 0, limit: int = 100) -> List[ActionItem]:
    """Get all action items across all meetings."""
    limit = min(limit, MAX_PAGINATION_LIMIT)
    return db.query(ActionItem).offset(skip).limit(limit).all()


def update_action_item(db: Session, item_id: int, update: ActionItemUpdate) -> Optional[ActionItem]:
    """Update an action item."""
    db_item = db.query(ActionItem).filter(ActionItem.id == item_id).first()
    if not db_item:
        return None

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_item, field, value)

    db_item.updated_at = utcnow()
    db.commit()
    db.refresh(db_item)
    return db_item


def get_action_items_by_owner(db: Session, owner: str) -> List[ActionItem]:
    """Get all action items assigned to an owner."""
    return db.query(ActionItem).filter(ActionItem.owner == owner).all()


def get_pending_action_items(db: Session) -> List[ActionItem]:
    """Get all pending action items."""
    return db.query(ActionItem).filter(ActionItem.status == "pending").all()


def get_overdue_items(db: Session) -> List[ActionItem]:
    """Get action items past their deadline."""
    return db.query(ActionItem).filter(
        ActionItem.deadline.isnot(None),
        ActionItem.status != "completed"
    ).all()


def link_linear_issue(db: Session, item_id: int, linear_issue_id: str) -> Optional[ActionItem]:
    """Link a Linear issue to an action item."""
    db_item = db.query(ActionItem).filter(ActionItem.id == item_id).first()
    if not db_item:
        return None

    db_item.linear_issue_id = linear_issue_id
    db.commit()
    db.refresh(db_item)
    return db_item
