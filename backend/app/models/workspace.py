"""
SQLAlchemy ORM models for the itinerary Workspace subsystem.

Tables:
  workspaces            - mutable in-progress itinerary edits
  workspace_versions    - immutable snapshots for undo / redo / audit trail
  workspace_proposals   - AI-generated pending changes awaiting user review
"""
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Text,
    JSON,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.app.db.database import Base
import uuid
from datetime import datetime, timezone


class Workspace(Base):
    """Mutable workspace holding an itinerary that the AI + user collaborate on."""

    __tablename__ = "workspaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), index=True, nullable=False)
    name = Column(String(500), nullable=False)

    origin_lat = Column(Float)
    origin_lng = Column(Float)
    destination_lat = Column(Float)
    destination_lng = Column(Float)
    start_date = Column(String(50))
    end_date = Column(String(50))

    itinerary_snapshot = Column(JSON, default=dict)
    current_version_number = Column(Integer, default=0)

    undo_stack = Column(JSON, default=list)
    redo_stack = Column(JSON, default=list)

    meta = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    versions = relationship(
        "WorkspaceVersion",
        back_populates="workspace",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    proposals = relationship(
        "WorkspaceProposal",
        back_populates="workspace",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    __table_args__ = (Index("ix_workspaces_user_updated", "user_id", "updated_at"),)


class WorkspaceVersion(Base):
    """Immutable snapshot of a workspace, created on accept / explicit versioning."""

    __tablename__ = "workspace_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(String(255), index=True)
    version_number = Column(Integer, nullable=False)
    description = Column(Text)
    snapshot = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    workspace = relationship("Workspace", back_populates="versions")


class WorkspaceProposal(Base):
    """AI-proposed change to a workspace pending user accept/reject."""

    __tablename__ = "workspace_proposals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    proposal_id_readable = Column(String(64), unique=True, index=True, default=lambda: "prop_" + uuid.uuid4().hex[:12])
    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(String(255), index=True)
    screen_context = Column(String(255))

    operations = Column(JSON, default=list, nullable=False)
    explanation = Column(Text, default="")
    changes = Column(JSON, default=list)
    warnings = Column(JSON, default=list)
    proposed_snapshot = Column(JSON, default=dict, nullable=False)

    status = Column(String(32), default="pending")  # pending | accepted | rejected
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime)

    workspace = relationship("Workspace", back_populates="proposals")
