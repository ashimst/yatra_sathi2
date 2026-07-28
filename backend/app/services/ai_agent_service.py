"""
AI Agent Service — Phase 0 Bootstrap implementation.

PERSISTENCE:
  Loads / saves AISession rows from SQLAlchemy (messages + metadata).

AGENT LOOP (Phase 0 stub — will be replaced by LangGraph in Phase 2):
  1. Restore / create session
  2. Append user message
  3. Classify intent (screen-context-aware heuristic)
  4. Dispatch → produce reply + optional ProposedAction + optional redirect_screen
  5. Persist and return

This is intentionally simple: the goal of Phase 0 is to get end-to-end
request/response working and correctly persist sessions.  The fancy tool
orchestration is added in subsequent phases.
"""
from __future__ import annotations

import copy
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.app.config.settings import settings
from backend.app.db.database import SessionLocal
from backend.app.models.ai_api import (
    ChatResponse,
    ProposedAction,
    EditItineraryResponse,
)
from backend.app.models.session import AISession


# ---------------------------------------------------------------------------
# Intent keywords
# ---------------------------------------------------------------------------
_INTENT_RULES: Dict[str, Tuple[List[str], List[str]]] = {
    # intent : (positive_keywords, context_hints)
    "GENERATE_ITINERARY": (
        ["plan", "create", "make", "build", "generate", "trip", "itinerary", "tour", "route"],
        ["plan"],
    ),
    "EDIT_ITINERARY": (
        ["edit", "modify", "change", "replace", "add", "remove", "delete", "swap", "update", "reorder", "more days", "less days"],
        ["itinerary_edit", "saved_itinerary_detail"],
    ),
    "FIND_PLACES": (
        ["find", "search", "look for", "best", "near", "nearby", "restaurant", "hotel", "temple", "place", "attraction", "cafe", "where"],
        ["explore", "saved"],
    ),
    "SHOW_RECOMMENDATIONS": (
        ["recommend", "suggest", "recommendation", "stop", "lunch", "dinner"],
        ["plan", "itinerary_edit", "saved_itinerary_detail"],
    ),
    "ANSWER_QUESTION": (
        ["what", "when", "how", "why", "is", "do", "can", "need", "permit", "visa", "safe", "weather", "best time"],
        [],
    ),
    "NAVIGATE": (
        ["show me", "take me", "go to", "open", "navigate"],
        [],
    ),
}


def _utc_iso(dt: Optional[datetime]) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


class AIAgentService:
    """Session-aware chatbot orchestrator."""

    # ------------------------------------------------------------------
    # Session CRUD
    # ------------------------------------------------------------------
    def _get_or_create_session(
        self, db: Session, session_id: str, user_id: Optional[str]
    ) -> AISession:
        row = db.query(AISession).filter(AISession.session_id == session_id).first()
        if row:
            return row
        row = AISession(
            session_id=session_id,
            messages=[],
            session_metadata={
                "user_id": user_id,
                "created_via": "ai_agent_service",
            },
        )
        db.add(row)
        db.flush()
        return row

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with SessionLocal() as db:
            row = db.query(AISession).filter(AISession.session_id == session_id).first()
            if not row:
                return None
            return self._session_to_dict(row)

    def delete_session(self, session_id: str) -> bool:
        with SessionLocal() as db:
            row = db.query(AISession).filter(AISession.session_id == session_id).first()
            if not row:
                return False
            db.delete(row)
            db.commit()
            return True

    @staticmethod
    def _session_to_dict(row: AISession) -> Dict[str, Any]:
        meta = dict(row.session_metadata or {})
        return {
            "session_id": row.session_id,
            "user_id": meta.get("user_id"),
            "messages": list(row.messages or []),
            "session_metadata": meta,
            "created_at": _utc_iso(row.created_at),
            "updated_at": _utc_iso(row.updated_at),
        }

    # ------------------------------------------------------------------
    # Intent classification
    # ------------------------------------------------------------------
    def classify_intent(
        self, message: str, screen_context: Optional[str], itinerary_context: Optional[Dict[str, Any]]
    ) -> str:
        text = message.lower().strip()
        if not text:
            return "ANSWER_QUESTION"

        scores: Dict[str, int] = {}
        for intent, (keywords, context_hints) in _INTENT_RULES.items():
            score = 0
            for kw in keywords:
                if re.search(r"\b" + re.escape(kw.lower()) + r"\b", text):
                    score += 3
            # Screen context strongly biases intent when applicable
            if screen_context and screen_context in context_hints:
                score += 5
            scores[intent] = score

        # Screen-context fallbacks when text is ambiguous
        if screen_context == "plan" and scores.get("GENERATE_ITINERARY", 0) == 0:
            scores["GENERATE_ITINERARY"] = scores.get("GENERATE_ITINERARY", 0) + 3
        if screen_context in ("itinerary_edit", "saved_itinerary_detail") and itinerary_context:
            if scores.get("EDIT_ITINERARY", 0) == 0:
                scores["EDIT_ITINERARY"] = scores.get("EDIT_ITINERARY", 0) + 4
        if screen_context == "explore" and scores.get("FIND_PLACES", 0) == 0:
            scores["FIND_PLACES"] = scores.get("FIND_PLACES", 0) + 3

        best_intent = max(scores, key=lambda k: scores[k])
        if scores[best_intent] == 0:
            return "ANSWER_QUESTION"
        return best_intent

    # ------------------------------------------------------------------
    # Reply generators (Phase 0: heuristic + templated)
    # ------------------------------------------------------------------
    def _generate_reply(
        self,
        intent: str,
        message: str,
        screen_context: Optional[str],
        screen_data: Optional[Dict[str, Any]],
        itinerary_context: Optional[Dict[str, Any]],
        created_itineraries: Optional[List[Dict[str, Any]]],
    ) -> Tuple[str, Optional[ProposedAction], Optional[str]]:
        sd = screen_data or {}
        ctx_it = itinerary_context or {}

        if intent == "GENERATE_ITINERARY":
            origin = sd.get("origin") or "Kathmandu"
            destination = sd.get("destination") or "Pokhara"
            days = sd.get("duration_days") or 3
            text = (
                f"Great! Let's plan a {days}-day road trip from {origin} to {destination}. "
                "I've pre-filled your trip details from the planner screen — just hit Approve and I'll build "
                "a day-by-day itinerary with stops, meals and overnight stays tailored to your pace."
            )
            action = ProposedAction(
                type="generate_itinerary",
                args={
                    "origin": origin,
                    "destination": destination,
                    "num_days": int(days) if isinstance(days, (int, float)) else 3,
                    "screen_data": sd,
                },
                explanation=f"Generate {days}-day itinerary: {origin} → {destination}",
            )
            return text, action, None

        if intent == "EDIT_ITINERARY" and ctx_it:
            title = ctx_it.get("title") or "your itinerary"
            text = (
                f"Understood — I'll apply \"{message}\" to {title}. "
                "Review the proposed changes on the right; if everything looks good, Approve to update "
                "your itinerary and save a new version."
            )
            action = ProposedAction(
                type="apply_edit",
                args={
                    "edit_request": message,
                    "itinerary_id": ctx_it.get("id"),
                    "updated_itinerary": copy.deepcopy(ctx_it),
                },
                explanation=f"Apply edit to {title}",
            )
            return text, action, None

        if intent == "SHOW_RECOMMENDATIONS":
            text = (
                "Here are some places worth checking out. Tap the + button to add any stop to your itinerary."
            )
            action = ProposedAction(
                type="show_recommendations",
                args={
                    "recommendations": [
                        {
                            "place_id": "recommend_1",
                            "place_name": "Popular nearby stop",
                            "justification": "Top-rated en-route attraction matching your interests.",
                            "distance_km": 12.5,
                        }
                    ],
                    "day": 1,
                },
                explanation="Show curated recommendations to add to your trip.",
            )
            return text, action, None

        if intent == "FIND_PLACES":
            text = (
                "I'll search for places matching your request once the places search tool is fully wired "
                "up in Phase 1. For now, try the Explore tab — it has full filtering and search."
            )
            return text, None, "explore"

        if intent == "NAVIGATE":
            targets = {
                "saved": ["saved", "saved itineraries", "my trips"],
                "plan": ["plan", "trip planner", "planner"],
                "explore": ["explore", "discover", "search"],
                "profile": ["profile", "account", "me"],
                "map": ["map"],
            }
            for target, kws in targets.items():
                if any(k in message.lower() for k in kws):
                    return f"Taking you to the {target} section.", None, target
            return "Where would you like to go? Try 'Go to saved itineraries' or 'Open the map'.", None, None

        # ANSWER_QUESTION (default) + generic fallback
        greet = any(h in message.lower() for h in ["hi", "hello", "namaste", "hey"])
        if greet:
            return (
                "Namaste! I'm YatraSathi, your Nepal travel assistant. I can plan itineraries, "
                "edit saved trips, recommend en-route stops, and answer travel questions. What would you like to do?"
            ), None, None

        itinerary_count = len(created_itineraries or [])
        if itinerary_count:
            return (
                f"Got it — asking about Nepal travel. Quick tip: you already have {itinerary_count} saved "
                "itinerary(ies); say 'edit my Pokhara trip' or 'add a day to my road trip' and I'll help refine it."
            ), None, None
        return (
            "I can help with that. For best results, try: 'Plan a 3-day trip from Kathmandu to Pokhara', "
            "'Find vegan restaurants in Chitwan', or 'Edit my saved trip and make it more relaxed'."
        ), None, None

    # ------------------------------------------------------------------
    # Main chat entrypoint
    # ------------------------------------------------------------------
    def chat(
        self,
        session_id: str,
        user_id: Optional[str],
        message: str,
        screen_context: Optional[str] = None,
        screen_data: Optional[Dict[str, Any]] = None,
        itinerary_context: Optional[Dict[str, Any]] = None,
        created_itineraries: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatResponse:
        if not settings.AI_ENABLED:
            return ChatResponse(
                session_id=session_id,
                response_text=(
                    "The AI assistant is currently disabled on the server. "
                    "Set AI_ENABLED=true in your .env file to enable it."
                ),
                messages=[],
            )

        with SessionLocal() as db:
            row = self._get_or_create_session(db, session_id, user_id)

            existing_messages: List[Dict[str, Any]] = list(row.messages or [])

            user_msg = {
                "role": "user",
                "content": message,
                "timestamp": _utc_iso(datetime.now(timezone.utc)),
            }
            existing_messages.append(user_msg)

            intent = self.classify_intent(message, screen_context, itinerary_context)

            reply_text, proposed_action, redirect_screen = self._generate_reply(
                intent,
                message,
                screen_context,
                screen_data,
                itinerary_context,
                created_itineraries,
            )

            assistant_msg = {
                "role": "assistant",
                "content": reply_text,
                "intent": intent,
                "proposed_action": proposed_action.model_dump() if proposed_action else None,
                "redirect_screen": redirect_screen,
                "timestamp": _utc_iso(datetime.now(timezone.utc)),
            }
            existing_messages.append(assistant_msg)

            # Persist metadata snapshot for debugging / context restoration
            meta = dict(row.session_metadata or {})
            meta["last_intent"] = intent
            meta["last_screen_context"] = screen_context
            meta["user_id"] = user_id or meta.get("user_id")
            if itinerary_context is not None:
                meta["active_itinerary_id"] = (itinerary_context or {}).get("id")
            if created_itineraries is not None:
                meta["saved_itinerary_ids"] = [
                    (it or {}).get("id") for it in created_itineraries
                ]

            row.messages = existing_messages
            row.session_metadata = meta
            row.updated_at = datetime.now(timezone.utc)

            db.commit()
            refreshed_meta = dict(row.session_metadata or {})

            return ChatResponse(
                session_id=row.session_id,
                response_text=reply_text,
                proposed_action=proposed_action,
                redirect_screen=redirect_screen,
                messages=list(row.messages or []),
            )

    # ------------------------------------------------------------------
    # Itinerary edit endpoint
    # ------------------------------------------------------------------
    def edit_itinerary(
        self,
        current_itinerary: Dict[str, Any],
        edit_request: str,
        user_id: Optional[str] = None,
    ) -> EditItineraryResponse:
        title = current_itinerary.get("title") or "your itinerary"

        # Phase 0: return a non-destructive proposal containing the same itinerary
        # plus a human-readable explanation.  Real mutation logic is added in Phase 3
        # (Workspace operations executor + proposal warnings).
        proposed = copy.deepcopy(current_itinerary)

        changes = [
            {
                "op": "proposal_only",
                "explanation": (
                    f"Captured edit request for {title}: {edit_request}. "
                    "The AI mutation engine will be wired in Phase 3 — for now, this is a stub proposal."
                ),
            }
        ]
        warnings = [
            "This proposal is from the Phase 0 stub. Real AI-powered itinerary mutations are coming in Phase 3."
        ]
        explanation = (
            f"Here's my draft of the changes for '{edit_request}' on {title}. "
            "Review and Approve to apply (presently a no-op placeholder); in later phases this will "
            "include real stop reordering, POI replacement, and route re-calculation."
        )

        proposed_action = ProposedAction(
            type="apply_edit",
            args={
                "edit_request": edit_request,
                "updated_itinerary": proposed,
            },
            explanation=explanation,
        )

        return EditItineraryResponse(
            proposed_itinerary=proposed,
            explanation=explanation,
            warnings=warnings,
            changes=changes,
            proposed_action=proposed_action,
        )


ai_agent_service = AIAgentService()
