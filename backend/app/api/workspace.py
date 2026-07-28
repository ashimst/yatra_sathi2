"""
Workspace API endpoints.

  POST   /workspace                                       — create new workspace
  GET    /workspace/{id}/versions                         — list immutable versions
  GET    /workspace/{id}                                  — get workspace state
  POST   /workspace/{id}/execute                          — apply simple operation immediately
  POST   /workspace/{id}/propose                          — create AI proposal (pending)
  POST   /workspace/{id}/proposals/{proposal_id}/action   — accept or reject a proposal
  POST   /workspace/{id}/undo                             — undo last operation
  POST   /workspace/{id}/redo                             — redo last undone operation
"""
from fastapi import APIRouter, HTTPException

from backend.app.models.ai_api import (
    WorkspaceCreate,
    WorkspaceExecute,
    WorkspacePropose,
    ProposalAction,
    GenericSuccess,
)
from backend.app.services.workspace_service import workspace_service

router = APIRouter(prefix="/workspace", tags=["workspace"])


def _not_found(msg: str = "Workspace not found"):
    return HTTPException(status_code=404, detail=msg)


@router.post("")
async def create_workspace(req: WorkspaceCreate):
    """Create a new workspace, optionally seeded with an initial itinerary."""
    try:
        return workspace_service.create_workspace(
            user_id=req.user_id,
            name=req.name,
            origin_lat=req.origin_lat,
            origin_lng=req.origin_lng,
            destination_lat=req.destination_lat,
            destination_lng=req.destination_lng,
            start_date=req.start_date,
            end_date=req.end_date,
            initial_itinerary=req.initial_itinerary,
        )
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Failed to create workspace: {e}")


@router.get("/{workspace_id}/versions")
async def list_versions(workspace_id: str):
    """List immutable saved versions of a workspace."""
    try:
        versions = workspace_service.list_versions(workspace_id)
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))
    if versions is None:
        raise _not_found()
    return {"versions": versions, "count": len(versions)}


@router.get("/{workspace_id}")
async def get_workspace(workspace_id: str):
    """Fetch the current state of a workspace (itinerary + undo/redo sizes)."""
    try:
        data = workspace_service.get_workspace(workspace_id)
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))
    if not data:
        raise _not_found()
    return data


@router.post("/{workspace_id}/execute")
async def execute_operation(workspace_id: str, req: WorkspaceExecute):
    """Apply a single simple operation immediately (no proposal, no review)."""
    try:
        return workspace_service.execute_operation(
            workspace_id,
            operation_type=req.operation_type,
            args=req.args,
            user_id=req.user_id,
        )
    except KeyError:
        raise _not_found()
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{workspace_id}/propose")
async def propose_changes(workspace_id: str, req: WorkspacePropose):
    """Create an AI proposal that the user must explicitly accept or reject."""
    try:
        operations = [o.model_dump() for o in req.operations]
        return workspace_service.propose_changes(
            workspace_id,
            operations=operations,
            user_id=req.user_id,
            screen_context=req.screen_context,
        )
    except KeyError:
        raise _not_found()
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{workspace_id}/proposals/{proposal_id}/action")
async def proposal_action(workspace_id: str, proposal_id: str, req: ProposalAction):
    """Accept or reject a pending proposal. Accept optionally creates an immutable version."""
    try:
        return workspace_service.resolve_proposal(
            workspace_id,
            proposal_id,
            action=req.action,
            create_version=req.create_version,
            version_description=req.version_description,
        )
    except KeyError as e:
        detail = str(e) if len(str(e)) > 0 else "Workspace or proposal not found"
        raise HTTPException(status_code=404, detail=detail)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{workspace_id}/undo")
async def undo(workspace_id: str):
    """Pop the last operation off the undo stack and revert the itinerary snapshot."""
    try:
        return workspace_service.undo(workspace_id)
    except KeyError:
        raise _not_found()
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{workspace_id}/redo")
async def redo(workspace_id: str):
    """Re-apply the most recently undone operation, if any."""
    try:
        return workspace_service.redo(workspace_id)
    except KeyError:
        raise _not_found()
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))
