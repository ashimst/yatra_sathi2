"""
Itinerary Persistence and Sharing API
Allows saving, managing, and public sharing of curated Himalayan Yatras.

Access rules:
- Saving, listing, reading by id and deleting require authentication and
  only ever touch the caller's own itineraries.
- Public read-only access is available exclusively through ``/share/{share_id}``.
"""
from datetime import datetime, timezone
import secrets
import uuid
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.core.deps import get_current_user
from backend.app.db.database import get_db
from backend.app.models.itinerary import Itinerary
from backend.app.models.user import User

router = APIRouter(prefix="/itineraries", tags=["itineraries"])

MAX_LIST = 50


class SaveItineraryRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    origin_name: Optional[str] = Field(default="Kathmandu", max_length=255)
    dest_name: Optional[str] = Field(default="Pokhara", max_length=255)
    num_days: int = Field(default=3, ge=1, le=30)
    pace: str = Field(default="balanced", max_length=32)
    budget: str = Field(default="medium", max_length=32)
    destinations: Optional[List[Dict[str, Any]]] = Field(default_factory=list, max_length=200)
    route_data: Optional[Dict[str, Any]] = None
    itinerary_data: Dict[str, Any]


def _summary(it: Itinerary) -> dict:
    return {
        "id": str(it.id),
        "share_id": it.share_id,
        "title": it.title,
        "description": it.description,
        "origin_name": it.origin_name,
        "dest_name": it.dest_name,
        "num_days": it.num_days,
        "pace": it.pace,
        "budget": it.budget,
        "created_at": it.created_at.isoformat() if it.created_at else None,
        "share_url": f"/share/{it.share_id}",
    }


def _detail(it: Itinerary) -> dict:
    data = _summary(it)
    data.pop("share_url")
    data["itinerary"] = it.itinerary_data
    data["route"] = it.route_data
    return data


def _parse_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid itinerary UUID.")


def _get_owned(db: Session, itinerary_id: str, user: User) -> Itinerary:
    record = db.query(Itinerary).filter(
        Itinerary.id == _parse_uuid(itinerary_id),
        Itinerary.user_id == user.id,
    ).first()
    if not record:
        # 404 (not 403) so we don't reveal that someone else's id exists.
        raise HTTPException(status_code=404, detail="Itinerary not found.")
    return record


@router.post("")
async def save_itinerary(
    req: SaveItineraryRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save an itinerary to the caller's library and generate a public share ID."""
    record = Itinerary(
        id=uuid.uuid4(),
        user_id=user.id,
        # 64 bits of entropy: share links are unguessable capability URLs.
        share_id=f"nepal-{secrets.token_urlsafe(8)}",
        title=req.title,
        description=req.description or str(req.itinerary_data.get("summary", ""))[:2000],
        origin_name=req.origin_name,
        dest_name=req.dest_name,
        num_days=req.num_days,
        pace=req.pace,
        budget=req.budget,
        destinations=req.destinations or [],
        route_data=req.route_data,
        itinerary_data=req.itinerary_data,
        created_at=datetime.now(timezone.utc),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "success": True,
        "itinerary_id": str(record.id),
        "share_id": record.share_id,
        "title": record.title,
        "share_url": f"/share/{record.share_id}",
    }


@router.get("")
async def list_itineraries(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the caller's saved itineraries, newest first."""
    rows = (
        db.query(Itinerary)
        .filter(Itinerary.user_id == user.id)
        .order_by(Itinerary.created_at.desc())
        .limit(MAX_LIST)
        .all()
    )
    return {"itineraries": [_summary(it) for it in rows]}


@router.get("/share/{share_id}")
async def get_shared_itinerary(share_id: str, db: Session = Depends(get_db)):
    """Public read-only endpoint for viewing shared itineraries without login."""
    record = db.query(Itinerary).filter(Itinerary.share_id == share_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Shared itinerary not found or expired.")
    return _detail(record)


@router.get("/{itinerary_id}")
async def get_itinerary_by_id(
    itinerary_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get one of the caller's itineraries by ID."""
    return _detail(_get_owned(db, itinerary_id, user))


@router.delete("/{itinerary_id}")
async def delete_itinerary(
    itinerary_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete one of the caller's saved itineraries."""
    record = _get_owned(db, itinerary_id, user)
    db.delete(record)
    db.commit()
    return {"success": True, "deleted_id": itinerary_id}
