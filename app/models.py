"""SQLAlchemy models."""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timezone

Base = declarative_base()


def utcnow():
    """Timezone-aware UTC now."""
    return datetime.now(timezone.utc)


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    transcript = Column(Text)
    date = Column(DateTime, default=utcnow)
    created_at = Column(DateTime, default=utcnow)

    action_items = relationship("ActionItem", back_populates="meeting", cascade="all, delete-orphan")


class ActionItem(Base):
    __tablename__ = "action_items"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), index=True)
    task = Column(String, index=True)
    owner = Column(String, nullable=True)
    deadline = Column(String, nullable=True)
    priority = Column(String, default="medium")
    status = Column(String, default="pending")
    linear_issue_id = Column(String, nullable=True)
    related_items = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    meeting = relationship("Meeting", back_populates="action_items")
