"""
Workspace Service — Phase 0 implementation.

PURPOSE
  CRUD for mutable in-progress itinerary edits with:
    * Immutable versioning (snapshot every accepted proposal or explicit version creation)
    * Undo / redo stacks
    * AI proposals (pending accept/reject) that carry operations + proposed snapshot

MUTATION MODEL (Phase 0)
  For Phase 0 the actual semantic application of an operation (e.g. "add_stop") is
  a simple deep-copy snapshot push.  Real operation executors (with geospatial
  validation, itinerary optimiser calls, warning generation, etc.) are added in
  later phases.  However, the full contract (proposal creation, accept/reject,
  versioning, undo/redo) is already in place so the frontend integration can
  be implemented today.
"""
from __future__ import annotations

import copy
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.app.db.database import SessionLocal
from backend.app.models.workspace import Workspace, WorkspaceVersion, WorkspaceProposal


def _utc_iso(dt) -> str:
    if dt is None:
        return ""
    if getattr(dt, "tzinfo", None) is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _uuid_str(val) -> str:
    if val is None:
        return ""
    return str(val)


class WorkspaceService:
    # ------------------------------------------------------------------
    # Workspace CRUD
    # ------------------------------------------------------------------
    def create_workspace(
        self,
        *,
        user_id: str,
        name: str,
        origin_lat: Optional[float] = None,
        origin_lng: Optional[float] = None,
        destination_lat: Optional[float] = None,
        destination_lng: Optional[float] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        initial_itinerary: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        with SessionLocal() as db:
            ws = Workspace(
                user_id=user_id,
                name=name,
                origin_lat=origin_lat,
                origin_lng=origin_lng,
                destination_lat=destination_lat,
                destination_lng=destination_lng,
                start_date=start_date,
                end_date=end_date,
                itinerary_snapshot=copy.deepcopy(initial_itinerary or {}),
                current_version_number=1 if initial_itinerary else 0,
                undo_stack=[],
                redo_stack=[],
                meta={},
            )
            db.add(ws)
            db.flush()

            if initial_itinerary:
                v0 = WorkspaceVersion(
                    workspace_id=ws.id,
                    user_id=user_id,
                    version_number=1,
                    description="Initial snapshot from seed itinerary",
                    snapshot=copy.deepcopy(initial_itinerary),
                )
                db.add(v0)

            db.commit()
            return self._workspace_to_dict(ws, db)

    def get_workspace(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        with SessionLocal() as db:
            ws = self._load(db, workspace_id)
            if not ws:
                return None
            return self._workspace_to_dict(ws, db)

    def list_versions(self, workspace_id: str) -> List[Dict[str, Any]]:
        with SessionLocal() as db:
            ws = self._load(db, workspace_id)
            if not ws:
                return []
            rows = (
                db.query(WorkspaceVersion)
                .filter(WorkspaceVersion.workspace_id == ws.id)
                .order_by(WorkspaceVersion.version_number.asc())
                .all()
            )
            return [self._version_to_dict(v) for v in rows]

    # ------------------------------------------------------------------
    # Execute: immediate (simple) mutation applied to current snapshot
    # ------------------------------------------------------------------
    def execute_operation(
        self,
        workspace_id: str,
        *,
        operation_type: str,
        args: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        args = args or {}
        with SessionLocal() as db:
            ws = self._load(db, workspace_id)
            if not ws:
                raise KeyError("workspace not found")

            previous = copy.deepcopy(ws.itinerary_snapshot or {})
            new_snapshot = self._apply_operation_simple(previous, operation_type, args)

            ws.undo_stack = list(ws.undo_stack or []) + [
                {
                    "operation_type": operation_type,
                    "args": args,
                    "snapshot_before": previous,
                    "applied_at": _utc_iso(datetime.now(timezone.utc)),
                }
            ]
            # Any new explicit operation clears the redo branch.
            ws.redo_stack = []
            ws.itinerary_snapshot = new_snapshot
            ws.updated_at = datetime.now(timezone.utc)

            db.commit()
            return self._workspace_to_dict(ws, db)

    # ------------------------------------------------------------------
    # Propose / accept / reject
    # ------------------------------------------------------------------
    def propose_changes(
        self,
        workspace_id: str,
        *,
        operations: List[Dict[str, Any]],
        user_id: Optional[str] = None,
        screen_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        with SessionLocal() as db:
            ws = self._load(db, workspace_id)
            if not ws:
                raise KeyError("workspace not found")

            current = copy.deepcopy(ws.itinerary_snapshot or {})
            proposed_snapshot = current
            changes: List[Dict[str, Any]] = []
            for op in operations:
                op_type = op.get("operation_type") or "unknown"
                op_args = op.get("args") or {}
                proposed_snapshot = self._apply_operation_simple(
                    proposed_snapshot, op_type, op_args
                )
                changes.append(
                    {
                        "operation_type": op_type,
                        "args": op_args,
                        "explanation": (
                            f"Phase-0 stub for operation '{op_type}'. "
                            "Real semantic mutation + warnings in Phase 3."
                        ),
                    }
                )

            explanation = (
                f"Proposal containing {len(operations)} operation(s). "
                "Review the resulting itinerary snapshot and Approve to apply."
            )
            warnings = [
                "This proposal is generated by the Phase 0 stub. Real AI-powered itinerary mutation "
                "with validation is added in Phase 3."
            ]

            prop = WorkspaceProposal(
                workspace_id=ws.id,
                user_id=user_id or ws.user_id,
                screen_context=screen_context,
                operations=[copy.deepcopy(o) for o in operations],
                explanation=explanation,
                changes=changes,
                warnings=warnings,
                proposed_snapshot=copy.deepcopy(proposed_snapshot),
                status="pending",
            )
            db.add(prop)
            db.flush()
            db.commit()
            return self._proposal_to_dict(prop)

    def resolve_proposal(
        self,
        workspace_id: str,
        proposal_id: str,
        *,
        action: str,
        create_version: bool = True,
        version_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        if action not in ("accept", "reject"):
            raise ValueError("action must be 'accept' or 'reject'")

        with SessionLocal() as db:
            ws = self._load(db, workspace_id)
            if not ws:
                raise KeyError("workspace not found")

            prop = self._load_proposal(db, ws.id, proposal_id)
            if not prop:
                raise KeyError("proposal not found")
            if prop.status != "pending":
                raise ValueError(f"proposal already resolved: {prop.status}")

            prop.status = action + ("ed" if action.endswith("t") else "d")  # accepted/rejected
            prop.resolved_at = datetime.now(timezone.utc)

            if action == "accept":
                previous = copy.deepcopy(ws.itinerary_snapshot or {})
                new_snapshot = copy.deepcopy(prop.proposed_snapshot or {})
                ws.undo_stack = list(ws.undo_stack or []) + [
                    {
                        "operation_type": "accept_proposal",
                        "proposal_id": _uuid_str(prop.id),
                        "proposal_id_readable": prop.proposal_id_readable,
                        "snapshot_before": previous,
                        "applied_at": _utc_iso(datetime.now(timezone.utc)),
                    }
                ]
                ws.redo_stack = []
                ws.itinerary_snapshot = new_snapshot

                if create_version:
                    next_version = (ws.current_version_number or 0) + 1
                    version = WorkspaceVersion(
                        workspace_id=ws.id,
                        user_id=ws.user_id,
                        version_number=next_version,
                        description=version_description
                        or f"Applied proposal {prop.proposal_id_readable}",
                        snapshot=copy.deepcopy(new_snapshot),
                    )
                    db.add(version)
                    ws.current_version_number = next_version

            ws.updated_at = datetime.now(timezone.utc)
            db.commit()
            return self._workspace_to_dict(ws, db, last_proposal=prop)

    # ------------------------------------------------------------------
    # Undo / Redo
    # ------------------------------------------------------------------
    def undo(self, workspace_id: str) -> Dict[str, Any]:
        with SessionLocal() as db:
            ws = self._load(db, workspace_id)
            if not ws:
                raise KeyError("workspace not found")

            undo_stack: List[Dict[str, Any]] = list(ws.undo_stack or [])
            if not undo_stack:
                return self._workspace_to_dict(ws, db)

            current_snapshot = copy.deepcopy(ws.itinerary_snapshot or {})
            last_entry = undo_stack.pop()
            previous_snapshot = last_entry.get("snapshot_before") or current_snapshot

            ws.redo_stack = list(ws.redo_stack or []) + [
                {
                    **last_entry,
                    "snapshot_after": current_snapshot,
                }
            ]
            ws.undo_stack = undo_stack
            ws.itinerary_snapshot = copy.deepcopy(previous_snapshot)
            ws.updated_at = datetime.now(timezone.utc)

            db.commit()
            return self._workspace_to_dict(ws, db)

    def redo(self, workspace_id: str) -> Dict[str, Any]:
        with SessionLocal() as db:
            ws = self._load(db, workspace_id)
            if not ws:
                raise KeyError("workspace not found")

            redo_stack: List[Dict[str, Any]] = list(ws.redo_stack or [])
            if not redo_stack:
                return self._workspace_to_dict(ws, db)

            current_snapshot = copy.deepcopy(ws.itinerary_snapshot or {})
            last_entry = redo_stack.pop()
            next_snapshot = last_entry.get("snapshot_after") or current_snapshot

            ws.undo_stack = list(ws.undo_stack or []) + [
                {
                    **last_entry,
                    "snapshot_before": current_snapshot,
                }
            ]
            ws.redo_stack = redo_stack
            ws.itinerary_snapshot = copy.deepcopy(next_snapshot)
            ws.updated_at = datetime.now(timezone.utc)

            db.commit()
            return self._workspace_to_dict(ws, db)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load(self, db: Session, workspace_id: str) -> Optional[Workspace]:
        try:
            uid = uuid.UUID(workspace_id)
        except (ValueError, AttributeError, TypeError):
            return None
        return db.query(Workspace).filter(Workspace.id == uid).first()

    def _load_proposal(
        self, db: Session, workspace_uuid, proposal_id: str
    ) -> Optional[WorkspaceProposal]:
        query = db.query(WorkspaceProposal).filter(WorkspaceProposal.workspace_id == workspace_uuid)
        try:
            uid = uuid.UUID(proposal_id)
            prop = query.filter(WorkspaceProposal.id == uid).first()
            if prop:
                return prop
        except (ValueError, AttributeError, TypeError):
            pass
        return query.filter(WorkspaceProposal.proposal_id_readable == proposal_id).first()

    def _apply_operation_simple(
        self, snapshot: Dict[str, Any], operation_type: str, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Phase-0 operation executor.

        Does not implement real semantic mutation yet, but DOES produce a
        deterministic new snapshot so the contract (undo/redo / versioning /
        proposal snapshots) is fully exercisable by the frontend.  The
        `meta.applied_operations` array tracks operations so callers can
        inspect them and tests can assert the pipeline works.
        """
        out = copy.deepcopy(snapshot or {})
        meta = dict(out.get("meta") or {})
        ops = list(meta.get("applied_operations") or [])
        ops.append(
            {
                "operation_type": operation_type,
                "args": copy.deepcopy(args or {}),
                "applied_at": _utc_iso(datetime.now(timezone.utc)),
            }
        )
        meta["applied_operations"] = ops
        out["meta"] = meta

        # Special-case: modify_itinerary.args.itinerary overrides the snapshot.
        # This lets the chatbot pass a full updated_itinerary straight through.
        if operation_type == "modify_itinerary" and isinstance(args.get("itinerary"), dict):
            replacement = copy.deepcopy(args["itinerary"])
            # Preserve our meta tracking if the replacement doesn't bring its own.
            if "meta" in replacement and isinstance(replacement["meta"], dict):
                merged_meta = {**(replacement["meta"] or {}), "applied_operations": ops}
                replacement["meta"] = merged_meta
            else:
                replacement["meta"] = meta
            return replacement

        return out

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------
    def _workspace_to_dict(
        self, ws: Workspace, db: Session, last_proposal: Optional[WorkspaceProposal] = None
    ) -> Dict[str, Any]:
        pending_count = (
            db.query(WorkspaceProposal)
            .filter(
                WorkspaceProposal.workspace_id == ws.id,
                WorkspaceProposal.status == "pending",
            )
            .count()
        )
        data = {
            "id": _uuid_str(ws.id),
            "user_id": ws.user_id,
            "name": ws.name,
            "origin_lat": ws.origin_lat,
            "origin_lng": ws.origin_lng,
            "destination_lat": ws.destination_lat,
            "destination_lng": ws.destination_lng,
            "start_date": ws.start_date,
            "end_date": ws.end_date,
            "itinerary": copy.deepcopy(ws.itinerary_snapshot or {}),
            "current_version_number": ws.current_version_number or 0,
            "pending_proposals": pending_count,
            "undo_stack_size": len(ws.undo_stack or []),
            "redo_stack_size": len(ws.redo_stack or []),
            "meta": dict(ws.meta or {}),
            "created_at": _utc_iso(ws.created_at),
            "updated_at": _utc_iso(ws.updated_at),
        }
        if last_proposal is not None:
            data["last_proposal"] = self._proposal_to_dict(last_proposal)
        return data

    @staticmethod
    def _version_to_dict(v: WorkspaceVersion) -> Dict[str, Any]:
        return {
            "id": _uuid_str(v.id),
            "workspace_id": _uuid_str(v.workspace_id),
            "user_id": v.user_id,
            "version_number": v.version_number,
            "description": v.description,
            "snapshot": copy.deepcopy(v.snapshot or {}),
            "created_at": _utc_iso(v.created_at),
        }

    @staticmethod
    def _proposal_to_dict(p: WorkspaceProposal) -> Dict[str, Any]:
        return {
            "id": _uuid_str(p.id),
            "proposal_id": p.proposal_id_readable,
            "workspace_id": _uuid_str(p.workspace_id),
            "user_id": p.user_id,
            "screen_context": p.screen_context,
            "operations": list(p.operations or []),
            "explanation": p.explanation or "",
            "changes": list(p.changes or []),
            "warnings": list(p.warnings or []),
            "proposed_itinerary": copy.deepcopy(p.proposed_snapshot or {}),
            "status": p.status,
            "created_at": _utc_iso(p.created_at),
            "resolved_at": _utc_iso(p.resolved_at),
        }


workspace_service = WorkspaceService()
