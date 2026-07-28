"""
AI Agent API endpoints.

  POST   /ai/chat                  — main chat turn
  GET    /ai/sessions/{session_id} — fetch persisted session
  DELETE /ai/sessions/{session_id} — delete a session (clear history)
  POST   /ai/edit-itinerary        — itinerary-edit helper (separate from chat)
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from backend.app.models.ai_api import (
    ChatRequest,
    ChatResponse,
    EditItineraryRequest,
    EditItineraryResponse,
    SessionInfo,
    GenericSuccess,
)
from backend.app.services.ai_agent_service import ai_agent_service

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """Run a single turn of the AI travel assistant."""
    try:
        return ai_agent_service.chat(
            session_id=req.session_id,
            user_id=req.user_id,
            message=req.message,
            screen_context=req.screen_context,
            screen_data=req.screen_data,
            itinerary_context=req.itinerary_context,
            created_itineraries=req.created_itineraries,
        )
    except Exception as e:  # pragma: no cover - safety net
        raise HTTPException(status_code=500, detail=f"Chat pipeline error: {e}")


@router.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str) -> SessionInfo:
    """Fetch the stored state of a chat session."""
    info = ai_agent_service.get_session(session_id)
    if not info:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionInfo(**info)


@router.delete("/sessions/{session_id}", response_model=GenericSuccess)
async def delete_session(session_id: str) -> GenericSuccess:
    """Delete a chat session and clear its history."""
    deleted = ai_agent_service.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return GenericSuccess(message="Session deleted")


@router.post("/edit-itinerary", response_model=EditItineraryResponse)
async def edit_itinerary(req: EditItineraryRequest) -> EditItineraryResponse:
    """Ask the AI to propose edits to a given itinerary in a single call."""
    try:
        return ai_agent_service.edit_itinerary(
            current_itinerary=req.current_itinerary,
            edit_request=req.edit_request,
            user_id=req.user_id,
        )
    except Exception as e:  # pragma: no cover - safety net
        raise HTTPException(status_code=500, detail=f"Edit itinerary pipeline error: {e}")
