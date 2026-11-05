"""
Trail Watch: community trail-condition board.

Travelers post trail hazard reports that are shown publicly to other
travelers, and can sign up as volunteer stewards. YatraSathi is an
independent platform: reports are NOT forwarded to any authority or
conservation body, and no affiliation with any organization is implied.
In an emergency, contact Nepal Police (100) or the Tourist Police (1144).
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, EmailStr, Field
from typing import Literal, Optional
from sqlalchemy.orm import Session
import uuid

from backend.app.config.settings import settings
from backend.app.core.deps import get_current_user
from backend.app.core.rate_limit import rate_limit
from backend.app.db.database import get_db
from backend.app.models.trail_watch import TrailReport, TrailSteward
from backend.app.models.user import User

router = APIRouter(prefix="/trail-watch", tags=["trail-watch"])

# "Resolved & Cleared" is the legacy label still present in older rows.
RESOLVED_STATUSES = ("Resolved", "Resolved & Cleared")

_HAZARD_CATEGORIES = [
    (("waste", "plastic", "litter", "trash"), "Waste & Litter"),
    (("shrine", "mani", "heritage", "temple", "stupa"), "Heritage Site"),
    (("bridge", "cable"), "Bridge & Crossing"),
    (("landslide", "obstruction", "rock", "flood", "snow", "avalanche"), "Trail Obstruction"),
]


def categorize_hazard(hazard_type: str) -> str:
    lowered = hazard_type.lower()
    for keywords, label in _HAZARD_CATEGORIES:
        if any(k in lowered for k in keywords):
            return label
    return "General Trail Condition"


class CreateReportRequest(BaseModel):
    hazard_type: str = Field(min_length=1, max_length=120)
    urgency: Literal["Low", "Moderate", "Urgent"] = "Moderate"
    description: str = Field(min_length=1, max_length=2000)
    location_name: Optional[str] = Field(default="Trisuli Gorge Sector", max_length=255)
    latitude: Optional[float] = Field(default=27.9881, ge=-90, le=90)
    longitude: Optional[float] = Field(default=86.8256, ge=-180, le=180)
    altitude: Optional[int] = Field(default=2810, ge=-500, le=9000)
    image_url: Optional[str] = Field(default=None, max_length=2048, pattern=r"^(https?://|/uploads/)")


class RegisterStewardRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    preferred_region: Optional[str] = Field(default="Annapurna Circuit", max_length=120)


# Illustrative sample reports, seeded only outside production (see get_reports).
INITIAL_AUDITS = [
    {
        "hazard_type": "Waste & Plastic Accumulation",
        "urgency": "Moderate",
        "description": "Sample report: wrappers and plastic bottles reported along the trail near Namche Bazaar.",
        "location_name": "Khumbu Corridor • Namche to Tengboche",
        "latitude": 27.805,
        "longitude": 86.714,
        "altitude": 3440,
        "image_url": None,
        "status": "Resolved",
        "assigned_guild": "Waste & Litter",
    },
    {
        "hazard_type": "Trail Obstruction / Landslide",
        "urgency": "Urgent",
        "description": "Sample report: loose rocks from shale slippage across the lower bypass trail.",
        "location_name": "Annapurna Circuit • Dana to Ghasa",
        "latitude": 28.539,
        "longitude": 83.652,
        "altitude": 2810,
        "image_url": None,
        "status": "Open",
        "assigned_guild": "Trail Obstruction",
    },
    {
        "hazard_type": "Heritage Shrine & Mani Wall Damage",
        "urgency": "Low",
        "description": "Sample report: weathered slate inscriptions on a mani wall.",
        "location_name": "Trishuli Corridor • Gosainkunda Way",
        "latitude": 28.082,
        "longitude": 85.342,
        "altitude": 3120,
        "image_url": None,
        "status": "Open",
        "assigned_guild": "Heritage Site",
    },
]


@router.post("/reports", dependencies=[rate_limit("trail_watch", settings.RATE_LIMIT_UPLOAD)])
async def create_report(
    req: CreateReportRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """File a verified trail hazard report."""
    # Categorise the report by topic so travelers can filter the board.
    # (Stored in the legacy ``assigned_guild`` column; no one is "assigned".)
    category = categorize_hazard(req.hazard_type)

    report = TrailReport(
        id=uuid.uuid4(),
        hazard_type=req.hazard_type,
        urgency=req.urgency,
        description=req.description,
        location_name=req.location_name or "Himalayan Corridor",
        latitude=req.latitude,
        longitude=req.longitude,
        altitude=req.altitude or 2400,
        image_url=req.image_url,
        status="Open",
        assigned_guild=category
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "success": True,
        "message": (
            "Thanks! Your report is now visible to other travelers on the Trail Watch board. "
            "It is not sent to any authority; in an emergency call Nepal Police (100) or Tourist Police (1144)."
        ),
        "report": {
            "id": str(report.id),
            "hazard_type": report.hazard_type,
            "urgency": report.urgency,
            "description": report.description,
            "location_name": report.location_name,
            "altitude": report.altitude,
            "image_url": report.image_url,
            "status": report.status,
            "assigned_guild": report.assigned_guild,
            "created_at": report.created_at.isoformat() if hasattr(report.created_at, 'isoformat') else str(report.created_at or "")
        }
    }


@router.get("/reports")
async def get_reports(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    """Retrieve trail reports, newest first."""
    db_reports = db.query(TrailReport).order_by(TrailReport.created_at.desc()).limit(limit).all()

    # Demo sample audits are only seeded outside production; in production an
    # empty table is shown as empty rather than with illustrative records.
    if not db_reports and not settings.is_production:
        for audit in INITIAL_AUDITS:
            r = TrailReport(
                id=uuid.uuid4(),
                hazard_type=audit["hazard_type"],
                urgency=audit["urgency"],
                description=audit["description"],
                location_name=audit["location_name"],
                latitude=audit["latitude"],
                longitude=audit["longitude"],
                altitude=audit["altitude"],
                image_url=audit["image_url"],
                status=audit["status"],
                assigned_guild=audit["assigned_guild"]
            )
            db.add(r)
        db.commit()
        db_reports = db.query(TrailReport).order_by(TrailReport.created_at.desc()).limit(limit).all()

    return {
        "count": len(db_reports),
        "reports": [
            {
                "id": str(r.id),
                "hazard_type": r.hazard_type,
                "urgency": r.urgency,
                "description": r.description,
                "location_name": r.location_name,
                "altitude": r.altitude,
                "image_url": r.image_url,
                "status": r.status,
                "assigned_guild": r.assigned_guild,
                "created_at": r.created_at.isoformat() if r.created_at else ""
            }
            for r in db_reports
        ]
    }


@router.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Retrieve stewardship metrics computed from stored reports and stewards."""
    total_reports = db.query(TrailReport).count()
    active_reports = db.query(TrailReport).filter(TrailReport.status.notin_(RESOLVED_STATUSES)).count()
    resolved_reports = db.query(TrailReport).filter(TrailReport.status.in_(RESOLVED_STATUSES)).count()
    steward_count = db.query(TrailSteward).count()

    return {
        "active_trail_reports": active_reports,
        "cleanups_completed": resolved_reports,
        "registered_stewards": steward_count,
        "total_reports": total_reports,
        # Share of reports marked resolved; None when there are no reports.
        "resolution_rate": round(resolved_reports / total_reports, 3) if total_reports else None,
    }


@router.post("/stewards", dependencies=[rate_limit("auth", settings.RATE_LIMIT_AUTH)])
async def register_steward(req: RegisterStewardRequest, db: Session = Depends(get_db)):
    """Register traveler as a volunteer ecological steward with doko pack."""
    steward = TrailSteward(
        id=uuid.uuid4(),
        name=req.name,
        email=req.email,
        preferred_region=req.preferred_region or "Annapurna Circuit",
        doko_pack_issued=True
    )
    db.add(steward)
    db.commit()
    db.refresh(steward)

    member_code = f"YS-{str(steward.id)[:8].upper()}"
    return {
        "success": True,
        "message": f"Welcome {req.name}! You're registered as a YatraSathi community steward (member #{member_code}).",
        "steward_id": str(steward.id),
        "credential_code": member_code,
        "preferred_region": steward.preferred_region,
    }
