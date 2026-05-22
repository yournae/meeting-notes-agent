import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db, init_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base

# Test database
TEST_DATABASE_URL = "sqlite:///./test_meetings.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    """Create test database before each test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_root(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_create_meeting(client):
    """Test creating a meeting."""
    meeting_data = {
        "title": "Sprint Planning",
        "transcript": "John: We need to fix the login bug by Friday. Sarah: I'll handle the database migration."
    }

    response = client.post("/meetings", json=meeting_data)
    assert response.status_code == 200

    data = response.json()
    assert data["title"] == "Sprint Planning"
    assert "id" in data
    assert "action_items" in data


def test_list_meetings(client):
    """Test listing meetings."""
    # Create a meeting first
    meeting_data = {
        "title": "Test Meeting",
        "transcript": "Some discussion about tasks."
    }
    client.post("/meetings", json=meeting_data)

    # List meetings
    response = client.get("/meetings")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0


def test_get_meeting(client):
    """Test getting a specific meeting."""
    # Create a meeting
    meeting_data = {
        "title": "Test Meeting",
        "transcript": "Discussion content."
    }
    create_response = client.post("/meetings", json=meeting_data)
    meeting_id = create_response.json()["id"]

    # Get the meeting
    response = client.get(f"/meetings/{meeting_id}")
    assert response.status_code == 200
    assert response.json()["id"] == meeting_id


def test_get_nonexistent_meeting(client):
    """Test getting a meeting that doesn't exist."""
    response = client.get("/meetings/9999")
    assert response.status_code == 404


def test_list_action_items(client):
    """Test listing action items."""
    # Create a meeting with action items
    meeting_data = {
        "title": "Planning",
        "transcript": "John: Fix the bug by Friday. Sarah: Update docs by Monday."
    }
    client.post("/meetings", json=meeting_data)

    # List action items
    response = client.get("/action-items")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_update_action_item(client):
    """Test updating an action item."""
    # Create a meeting
    meeting_data = {
        "title": "Test",
        "transcript": "John: Complete the task."
    }
    create_response = client.post("/meetings", json=meeting_data)
    action_items = create_response.json()["action_items"]

    if len(action_items) > 0:
        item_id = action_items[0]["id"]

        # Update the item
        update_data = {"status": "completed"}
        response = client.patch(f"/action-items/{item_id}", json=update_data)
        assert response.status_code == 200
        assert response.json()["status"] == "completed"


def test_get_pending_items(client):
    """Test getting pending action items."""
    response = client.get("/action-items/pending")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_input_validation_title_too_long(client):
    """Test that title max length is enforced."""
    meeting_data = {
        "title": "x" * 501,  # max is 500
        "transcript": "Some transcript content."
    }
    response = client.post("/meetings", json=meeting_data)
    assert response.status_code == 422  # Validation error


def test_input_validation_transcript_too_long(client):
    """Test that transcript max length is enforced."""
    meeting_data = {
        "title": "Test",
        "transcript": "x" * 50001  # max is 50000
    }
    response = client.post("/meetings", json=meeting_data)
    assert response.status_code == 422  # Validation error


def test_input_validation_empty_title(client):
    """Test that empty title is rejected."""
    meeting_data = {
        "title": "",
        "transcript": "Some content."
    }
    response = client.post("/meetings", json=meeting_data)
    assert response.status_code == 422


def test_input_validation_bad_priority(client):
    """Test that invalid priority is rejected."""
    meeting_data = {
        "title": "Test",
        "transcript": "John: Do something."
    }
    # First create meeting to get an action item
    create_response = client.post("/meetings", json=meeting_data)
    action_items = create_response.json()["action_items"]

    if len(action_items) > 0:
        item_id = action_items[0]["id"]
        response = client.patch(f"/action-items/{item_id}", json={"priority": "urgent"})
        assert response.status_code == 422
