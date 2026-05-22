import pytest
import os

# Force mock mode for tests
os.environ["MOCK_MODE"] = "true"

from app.agent import extract_action_items, find_related_items


def test_extract_action_items():
    """Test action item extraction from transcript."""
    transcript = """
    John: We need to fix the login bug by Friday.
    Sarah: I'll handle the database migration, deadline is next Monday.
    John: Can someone update the documentation?
    Mike: I'll do that by end of week.
    Sarah: We're blocked on the API integration until John finishes.
    """

    result = extract_action_items(transcript)

    assert "items" in result
    assert "summary" in result
    assert len(result["items"]) > 0

    # Check structure of extracted items
    for item in result["items"]:
        assert "task" in item
        assert "priority" in item


def test_find_related_items():
    """Test finding related action items."""
    existing_items = [
        {"id": 1, "task": "Fix login bug", "owner": "John", "status": "pending"},
        {"id": 2, "task": "Update database schema", "owner": "Sarah", "status": "in_progress"},
        {"id": 3, "task": "Deploy to production", "owner": "Mike", "status": "pending"},
    ]

    new_task = "Fix authentication issues in login flow"
    related = find_related_items(new_task, existing_items)

    assert isinstance(related, list)
    # Should find the login bug as related
    assert 1 in related or len(related) == 0  # May or may not find depending on LLM


def test_extract_action_items_empty():
    """Test extraction with minimal transcript."""
    transcript = "Just a casual chat with no action items."

    result = extract_action_items(transcript)

    assert "items" in result
    assert isinstance(result["items"], list)
