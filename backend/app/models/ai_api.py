"""
Pydantic request/response models for the AI Agent and Workspace APIs.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Proposed Action (human-in-the-loop confirmation object)
# ---------------------------------------------------------------------------
class ProposedAction(BaseModel):
    """Structured change that requires explicit user approval before applying."""

    type: str = Field(
        ...,
        description=(
            "One of: generate_itinerary, apply_edit, show_recommendations, "
            "add_stop, remove_stop, reorder_day, change_pace, navigate_to"
        ),
    )
    args: Dict[str, Any] = Field(default_factory=dict, description="Structured arguments for the action.")
    explanation: str = Field(
        "",
        description="Natural-language summary of what the action will change.",
    )


# ---------------------------------------------------------------------------
# Chat endpoints
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    """Request body for POST /ai/chat."""

    session_id: str = Field(..., description="Stable session identifier for the chat.")
    user_id: Optional[str] = Field(None, description="Authenticated user id, if any.")
    message: str = Field(..., min_length=1, description="User's latest message text.")

    screen_context: Optional[str] = Field(
        None,
        description=(
            "Name of the active Flutter screen: plan, explore, itinerary_edit, "
            "saved_itinerary_detail, profile, saved."
        ),
    )
    screen_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Screen-specific data (origin/destination, category filter, etc.).",
    )
    itinerary_context: Optional[Dict[str, Any]] = Field(
        None, description="The currently active itinerary in the UI."
    )
    created_itineraries: Optional[List[Dict[str, Any]]] = Field(
        None, description="All saved itineraries from UserSession (lightweight)."
    )


class ChatResponse(BaseModel):
    """Response body for POST /ai/chat."""

    session_id: str
    response_text: str = Field("", description="Natural language assistant reply.")
    proposed_action: Optional[ProposedAction] = Field(
        None, description="Optional pending action awaiting user approval."
    )
    redirect_screen: Optional[str] = Field(
        None, description="Optional screen the UI should navigate to, e.g. 'saved'."
    )
    messages: List[Dict[str, Any]] = Field(
        default_factory=list, description="Full updated conversation history."
    )


class SessionInfo(BaseModel):
    """Full persisted AI session metadata."""

    session_id: str
    user_id: Optional[str]
    messages: List[Dict[str, Any]]
    session_metadata: Dict[str, Any]
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Itinerary edit endpoint
# ---------------------------------------------------------------------------
class EditItineraryRequest(BaseModel):
    """Request body for POST /ai/edit-itinerary."""

    current_itinerary: Dict[str, Any] = Field(
        ..., description="Full current itinerary object from the frontend."
    )
    edit_request: str = Field(
        ..., min_length=1, description="User's natural language edit instruction."
    )
    user_id: Optional[str] = None


class EditItineraryResponse(BaseModel):
    """Response body for POST /ai/edit-itinerary."""

    proposed_itinerary: Dict[str, Any] = Field(
        ..., description="Proposed new itinerary object for the user to review."
    )
    explanation: str = Field("", description="Natural-language summary of changes.")
    warnings: List[str] = Field(default_factory=list)
    changes: List[Dict[str, Any]] = Field(default_factory=list)
    proposed_action: Optional[ProposedAction] = None


# ---------------------------------------------------------------------------
# Workspace endpoints
# ---------------------------------------------------------------------------
class WorkspaceCreate(BaseModel):
    """Request body for POST /workspace."""

    user_id: str = Field(..., description="Owner of the workspace.")
    name: str = Field(..., min_length=1, description="Display name, usually itinerary title.")
    origin_lat: Optional[float] = None
    origin_lng: Optional[float] = None
    destination_lat: Optional[float] = None
    destination_lng: Optional[float] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_itinerary: Optional[Dict[str, Any]] = Field(
        None, description="Seed itinerary snapshot."
    )


class WorkspaceOperation(BaseModel):
    """Single mutation operation inside a workspace execute/propose call."""

    operation_type: str = Field(
        ...,
        description=(
            "modify_itinerary, add_stop, remove_stop, reorder_day, "
            "change_pace, change_day_count, change_budget, replace_poi"
        ),
    )
    args: Dict[str, Any] = Field(default_factory=dict)


class WorkspaceExecute(BaseModel):
    """Request body for POST /workspace/{id}/execute."""

    operation_type: str
    args: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[str] = None


class WorkspacePropose(BaseModel):
    """Request body for POST /workspace/{id}/propose."""

    operations: List[WorkspaceOperation]
    user_id: Optional[str] = None
    screen_context: Optional[str] = None


class ProposalAction(BaseModel):
    """Request body for POST /workspace/{id}/proposals/{proposal_id}/action."""

    action: str = Field(..., description="One of: accept, reject.")
    create_version: bool = Field(
        True, description="Create an immutable version if the proposal is accepted."
    )
    version_description: Optional[str] = Field(
        None, description="Human-readable description for the new version."
    )


class GenericSuccess(BaseModel):
    success: bool = True
    message: Optional[str] = None
