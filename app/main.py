"""Meeting Notes Agent - FastAPI Application."""

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
from app.database import get_db, init_db
from app.schemas import MeetingCreate, MeetingResponse, ActionItemResponse, ActionItemUpdate
from app.auth import get_api_key
from app import crud
from typing import List
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiting storage (in-memory, per-IP)
_rate_limit_store: dict = {}
RATE_LIMIT_REQUESTS = 60  # max requests
RATE_LIMIT_WINDOW = 60    # per seconds


def _check_rate_limit(client_ip: str) -> bool:
    """Simple in-memory rate limiter. Returns True if allowed."""
    now = time.time()
    if client_ip not in _rate_limit_store:
        _rate_limit_store[client_ip] = []

    # Clean old entries
    _rate_limit_store[client_ip] = [
        t for t in _rate_limit_store[client_ip] if now - t < RATE_LIMIT_WINDOW
    ]

    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT_REQUESTS:
        return False

    _rate_limit_store[client_ip].append(now)
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle."""
    init_db()
    logger.info("Meeting Notes Agent started")
    yield
    logger.info("Meeting Notes Agent shutting down")


app = FastAPI(
    title="Meeting Notes Agent",
    version="0.2.0",
    description="AI-powered meeting action item tracker with cross-meeting intelligence",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Restrict in production!
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)


# ── Rate Limit Middleware ─────────────────────────────────
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limit all requests per client IP."""
    # Skip health check from rate limiting
    if request.url.path == "/health":
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"

    if not _check_rate_limit(client_ip):
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Try again later."},
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
        )

    response = await call_next(request)

    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"

    return response


# ── Public Endpoints (no auth) ────────────────────────────
@app.get("/")
def root():
    return {
        "message": "Meeting Notes Agent API",
        "version": "0.2.0",
        "docs": "/docs",
        "endpoints": {
            "POST /meetings": "Create meeting and extract action items",
            "GET /meetings": "List all meetings",
            "GET /meetings/{id}": "Get meeting details",
            "GET /action-items": "List all action items",
            "GET /action-items/{id}": "Get action item details",
            "PATCH /action-items/{id}": "Update action item",
            "GET /action-items/owner/{owner}": "Get items by owner",
            "GET /action-items/pending": "Get pending items",
        },
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# ── Protected Endpoints (require API key if configured) ───
@app.post("/meetings", response_model=MeetingResponse)
def create_meeting(
    meeting: MeetingCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    """Create a meeting and automatically extract action items."""
    from app.agent import extract_action_items, find_related_items, detect_status_updates
    from app.schemas import ActionItemCreate

    db_meeting = crud.create_meeting(db, meeting)

    # Extract action items using AI
    extraction = extract_action_items(meeting.transcript)

    # Get existing items for relationship detection
    existing_items = crud.get_all_action_items(db)
    existing_items_dict = [
        {"id": item.id, "task": item.task, "owner": item.owner, "status": item.status}
        for item in existing_items
    ]

    # Create action items with relationship detection
    for item_data in extraction.get("items", []):
        item = ActionItemCreate(**item_data)
        related_ids = find_related_items(item.task, existing_items_dict)
        crud.create_action_item(db, db_meeting.id, item, related_ids)

    # Detect status updates
    status_updates = detect_status_updates(meeting.transcript, existing_items_dict)
    for update in status_updates:
        item_id = update.get("item_id")
        new_status = update.get("new_status")
        if item_id and new_status:
            crud.update_action_item(db, item_id, ActionItemUpdate(status=new_status))

    db.refresh(db_meeting)
    return db_meeting


@app.get("/meetings", response_model=List[MeetingResponse])
def list_meetings(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    """List all meetings."""
    return crud.get_all_meetings(db, skip, limit)


@app.get("/meetings/{meeting_id}", response_model=MeetingResponse)
def get_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    """Get a specific meeting with its action items."""
    meeting = crud.get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@app.get("/action-items", response_model=List[ActionItemResponse])
def list_action_items(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    """List all action items across all meetings."""
    return crud.get_all_action_items(db, skip, limit)


@app.get("/action-items/pending", response_model=List[ActionItemResponse])
def get_pending_items(
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    """Get all pending action items."""
    return crud.get_pending_action_items(db)


@app.get("/action-items/owner/{owner}", response_model=List[ActionItemResponse])
def get_items_by_owner(
    owner: str,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    """Get all action items for a specific owner."""
    return crud.get_action_items_by_owner(db, owner)


@app.get("/action-items/{item_id}", response_model=ActionItemResponse)
def get_action_item(
    item_id: int,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    """Get a specific action item."""
    item = crud.get_action_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")
    return item


@app.patch("/action-items/{item_id}", response_model=ActionItemResponse)
def update_action_item(
    item_id: int,
    update: ActionItemUpdate,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    """Update an action item."""
    item = crud.update_action_item(db, item_id, update)
    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")
    return item
