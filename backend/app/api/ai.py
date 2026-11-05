"""
YatraSathi Dual-System Agentic Controller (System 1 & System 2 Architecture)

System 1 (In-Process SLM & Tool Engine):
- KEV 0.6B (decision_service): Fast sub-50ms agentic handoff arbiter, RAG reranker,
  POI quality gater, and picture solver.
- Cactus Needle (needle_agent): Sub-second grammar-constrained tool execution,
  unstructured-to-structured slot extraction, and deterministic itinerary mutation.

System 2 (Deep Reasoning & Narrative Synthesis):
- Groq / Large LLM: Multi-day high-level itinerary planning, narrative synthesis,
  complex trade-off explanation, and ambiguity resolution.
"""
from __future__ import annotations

import logging
import re
import json
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional

from backend.app.config.settings import settings
from backend.app.core.deps import get_current_user
from backend.app.db.database import get_db
from backend.app.models.session import AISession
from backend.app.models.user import User
from backend.app.services.place_service import place_service
from backend.app.services.decision_service import decision_service
from backend.app.services.needle_agent import needle_agent, search_places, get_place_details, find_nearby_restaurant

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["ai"])

MAX_MESSAGE_CHARS = 2000
MAX_TOOL_LIMIT = 8
MAX_TOOL_ARG_CHARS = 200
HISTORY_TURNS_FOR_LLM = 6


class ChatRequest(BaseModel):
    # Client-chosen conversation id; always scoped to the signed-in user
    # server-side, so two users can never share a session.
    session_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    itinerary_context: Optional[Dict[str, Any]] = None


class EditItineraryRequest(BaseModel):
    current_itinerary: Dict[str, Any]
    edit_request: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)


# ─────────────────────────────────────────────────────────────────────────────
# PER-USER CHAT SESSION PERSISTENCE (ai_sessions table)
# ─────────────────────────────────────────────────────────────────────────────
def _session_key(user: User, client_session_id: str) -> str:
    return f"{user.id}:{client_session_id}"


def _load_session(db: Session, user: User, client_session_id: str) -> Optional[AISession]:
    return db.query(AISession).filter(AISession.session_id == _session_key(user, client_session_id)).first()


def _get_history(record: Optional[AISession]) -> List[Dict[str, Any]]:
    return list(record.messages or []) if record else []


def _append_turn(db: Session, user: User, client_session_id: str, user_msg: str, assistant_msg: str) -> None:
    """Persist a user/assistant turn, keeping only the most recent messages."""
    try:
        record = _load_session(db, user, client_session_id)
        if record is None:
            record = AISession(
                session_id=_session_key(user, client_session_id),
                messages=[],
                session_metadata={"user_id": str(user.id)},
            )
            db.add(record)
        history = _get_history(record)
        history.extend([
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": assistant_msg},
        ])
        # Reassign (not mutate) so SQLAlchemy detects the JSON change.
        record.messages = history[-settings.AI_SESSION_MAX_MESSAGES:]
        db.commit()
    except Exception:
        db.rollback()
        logger.warning("Failed to persist AI chat turn", exc_info=True)


def _clamp_int(value: Any, default: int, lo: int, hi: int) -> int:
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return default


def _clean_str(value: Any) -> str:
    return str(value or "")[:MAX_TOOL_ARG_CHARS]


# ─────────────────────────────────────────────────────────────────────────────
# AGENT TOOL DEFINITIONS (OpenAI / Groq Schema for System 2 Escalations)
# ─────────────────────────────────────────────────────────────────────────────
AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_places",
            "description": "Search verified Nepal destinations, heritage temples, Thakali/Newari kitchens, cafes, hotels, viewpoints, and hidden gems.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search keyword, city, cuisine, or attraction name (e.g. 'Mustang Thakali', 'Australian Camp', 'Bandipur hotel', 'Boudha cafe')"
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional category filter: 'Restaurant', 'Cafe', 'Hotel', 'Guest House', 'Viewpoint', 'Religious Site', 'Waterfall', 'Lake'"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of places to return (default 4, max 8)"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "geocode_location",
            "description": "Resolve any Nepal city, district, mountain pass, or landmark into GPS latitude and longitude.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location_name": {
                        "type": "string",
                        "description": "Name of the place in Nepal (e.g. 'Pokhara', 'Mustang', 'Poon Hill', 'Rara Lake', 'Bandipur')"
                    }
                },
                "required": ["location_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_scenic_visual",
            "description": "Generate or retrieve an authentic, photorealistic visual representation of a Nepal destination, mountain sunrise, or cultural experience.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location_or_experience": {
                        "type": "string",
                        "description": "Description of the scene to visualize (e.g. 'Sunrise over Annapurna from Sarangkot', 'Cozy evening in Marpha Thakali kitchen', 'Boudhanath stupa at twilight')"
                    }
                },
                "required": ["location_or_experience"]
            }
        }
    }
]


def tool_search_places(query: str, category: Optional[str] = None, limit: int = 4) -> List[Dict[str, Any]]:
    """System 1 Tool execution via Needle with KEV 0.6B POI Image Gating."""
    results = search_places(query=query, category=category, limit=limit)
    # Apply KEV 0.6B POI Image Gater to filter out repetitive stock photos
    for p in results:
        gate_res = decision_service.gate_poi_image(
            name=p.get("name", ""),
            category=p.get("category", ""),
            image_url=p.get("image_url"),
            is_hidden_gem=p.get("is_hidden_gem", False),
        )
        p["image_url"] = gate_res.suggested_image_url if gate_res.keep_image else None
    return results


def tool_geocode_location(location_name: str) -> Dict[str, Any]:
    return place_service.geocode_location(location_name)


def tool_generate_visual(location_or_experience: str) -> str:
    """Uses Needle structured entity extraction & KEV Archetype Classifier."""
    return decision_service.resolve_visual_experience(location_or_experience)


# ─────────────────────────────────────────────────────────────────────────────
# CHAT AGENT ROUTE (DUAL SYSTEM 1 & SYSTEM 2 CONTROLLER)
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/chat")
async def ai_chat(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Unified Agentic Controller.
    
    1. System 1 (KEV 0.6B) evaluates user intent and complexity for Agentic Handoff.
    2. If simple/deterministic (search, nearby dining, itinerary stop edit):
       -> Cactus Needle executes structured tools in sub-50ms.
    3. If complex multi-constraint planning or narrative synthesis:
       -> Escalates to System 2 (Groq LLM Planner) for high-level reasoning.
    """
    msg = req.message
    session_history = _get_history(_load_session(db, user, req.session_id))

    def remember(reply_text: str) -> None:
        _append_turn(db, user, req.session_id, msg, reply_text)

    # STEP 1: KEV 0.6B Agentic Handoff Arbiter
    handoff = decision_service.decide_agentic_handoff(
        user_message=msg,
        itinerary_context=req.itinerary_context,
    )
    logger.info(f"[AGENTIC HANDOFF] Target={handoff.target_system}, Intent={handoff.intent}, Tool={handoff.recommended_tool}")

    # STEP 2: FAST PATH -> System 1 (Cactus Needle Tool Execution)
    if handoff.target_system == "system_1_needle" and not handoff.requires_synthesis:
        # A. Structured Itinerary Modification via Needle
        if handoff.intent == "edit_itinerary" and req.itinerary_context:
            needle_res = needle_agent.parse_and_execute_edit(
                user_request=msg,
                current_itinerary=req.itinerary_context,
            )
            if needle_res.get("success"):
                action = needle_res.get("action", "modified")
                target = needle_res.get("target_place") or needle_res.get("added_place") or "stop"
                reply = f"Namaste! I've updated your itinerary: {action} '{target}' on Day {needle_res.get('day')}."
                remember(reply)
                
                return {
                    "response": reply,
                    "places": [],
                    "visual_url": None,
                    "intent": "system_1_needle_edit",
                    "action_executed": action,
                    "updated_itinerary": needle_res["result"].get("itinerary"),
                }

        # B. Direct Search / POI Discovery via Needle
        if handoff.recommended_tool == "search_places":
            q_clean = re.sub(r"(?:find|search|show me|look for|where can i eat|cafes in|hotels in|best)\s*", "", msg, flags=re.I).strip()
            places = tool_search_places(query=q_clean or msg, limit=4)
            if places:
                top_names = ", ".join([p["name"] for p in places[:3]])
                reply = f"Namaste! Here are verified destinations matching your request: {top_names}."
                remember(reply)
                return {
                    "response": reply,
                    "places": places,
                    "visual_url": None,
                    "intent": "system_1_needle_search",
                }

    # STEP 3: DEEP PATH -> System 2 (Groq LLM Planner & Synthesizer)
    groq_key = settings.GROQ_API_KEY
    if not groq_key:
        # Fallback to local System 1 response if no cloud key
        places = tool_search_places(query=msg, limit=4)
        fallback_text = "Namaste! I've curated verified destinations along your route across Nepal."
        return {
            "response": fallback_text,
            "places": places,
            "visual_url": None,
            "intent": "system_1_offline_fallback"
        }

    system_prompt = """You are Yatra Sathi's expert Himalayan travel agent and expedition copilot (System 2 Planner).
You work in tandem with Cactus Needle (System 1 execution engine) and KEV 0.6B decision service.
You specialize in Nepal tourism: heritage architecture, hidden viewpoints, authentic regional cuisine (Thakali, Newari, Tibetan), mountain teahouses, and offbeat gems.

Your Guidelines:
1. Always be warmly welcoming ('Namaste!').
2. When the user asks for recommendations (food, cafes, stays, viewpoints, waterfalls), CALL THE `search_places` TOOL to provide real verified options.
3. If they ask about places in a region, call `search_places` with that region/cuisine keyword.
4. If they ask to visualize or see a place, CALL `generate_scenic_visual`.
5. Emphasize authentic local experiences, respectful cultural tips, and realistic travel times (mountain roads in Nepal travel at 30-40 km/h).
6. Keep conversational answers engaging, inspiring, and concise (3-4 sentences), highlighting signature foods and views."""

    messages = [{"role": "system", "content": system_prompt}]
    for h in session_history[-HISTORY_TURNS_FOR_LLM:]:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": msg})

    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json"
    }

    gathered_places = []
    generated_visual = None

    async with httpx.AsyncClient(timeout=30.0) as client:
        for _ in range(3):
            payload = {
                "model": settings.LLM_MODEL,
                "messages": messages,
                "tools": AGENT_TOOLS,
                "tool_choice": "auto",
                "temperature": 0.4,
                "max_tokens": 1000
            }

            try:
                res = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
                if res.status_code != 200:
                    logger.warning(f"Groq agent call returned {res.status_code}: {res.text}")
                    break

                res_data = res.json()
                choice = res_data["choices"][0]
                model_msg = choice["message"]
                messages.append(model_msg)

                tool_calls = model_msg.get("tool_calls")
                if not tool_calls:
                    final_text = model_msg.get("content") or "Namaste! How may I assist your Himalayan expedition?"
                    remember(final_text)
                    return {
                        "response": final_text,
                        "places": gathered_places,
                        "visual_url": generated_visual,
                        "intent": "system_2_llm_synthesized"
                    }

                for tc in tool_calls:
                    fn_name = tc["function"]["name"]
                    tc_id = tc["id"]
                    # Tool arguments are model output and therefore untrusted.
                    try:
                        fn_args = json.loads(tc["function"].get("arguments") or "{}")
                        if not isinstance(fn_args, dict):
                            fn_args = {}
                    except (json.JSONDecodeError, TypeError):
                        fn_args = {}

                    logger.info("[TOOL CALL] %s(%s)", fn_name, fn_args)

                    if fn_name == "search_places":
                        places_res = tool_search_places(
                            query=_clean_str(fn_args.get("query")),
                            category=_clean_str(fn_args.get("category")) or None,
                            limit=_clamp_int(fn_args.get("limit"), 4, 1, MAX_TOOL_LIMIT),
                        )
                        gathered_places.extend(places_res)
                        tool_output = json.dumps([
                            {"name": p["name"], "category": p["category"], "must_try": p.get("must_try"), "rating": p.get("rating")}
                            for p in places_res
                        ])
                    elif fn_name == "geocode_location":
                        geo_res = tool_geocode_location(_clean_str(fn_args.get("location_name")))
                        tool_output = json.dumps(geo_res)
                    elif fn_name == "generate_scenic_visual":
                        vis_url = tool_generate_visual(_clean_str(fn_args.get("location_or_experience")))
                        generated_visual = vis_url
                        tool_output = json.dumps({"visual_url": vis_url, "status": "rendered"})
                    else:
                        tool_output = json.dumps({"error": f"Unknown tool {fn_name}"})

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "content": tool_output
                    })

            except Exception:
                logger.exception("Agent execution failed")
                break

    fallback_text = "Namaste! I've curated options for your journey across Nepal. Feel free to ask about scenic viewpoints, authentic dining, or custom routes!"
    remember(fallback_text)

    return {
        "response": fallback_text,
        "places": gathered_places,
        "visual_url": generated_visual,
        "intent": "system_2_fallback"
    }


# ─────────────────────────────────────────────────────────────────────────────
# EDIT ITINERARY ROUTE (POWERED BY CACTUS NEEDLE)
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/edit-itinerary")
async def edit_itinerary(req: EditItineraryRequest):
    """
    Direct Itinerary Edit Endpoint powered by Cactus Needle (System 1).
    Takes unstructured natural language, parses intent into structured slots,
    and executes deterministic itinerary mutations with zero hallucinations.
    """
    edit_req = req.edit_request
    it = req.current_itinerary

    logger.info(f"[CACTUS NEEDLE EDIT] Processing request: '{edit_req}'")
    needle_res = needle_agent.parse_and_execute_edit(
        user_request=edit_req,
        current_itinerary=it,
    )

    if needle_res.get("safety_rejection"):
        logger.warning(f"[SAFETY REJECTION RETURNED] {needle_res.get('message')}")
        return {
            "success": False,
            "safety_rejection": True,
            "safety_warning": needle_res.get("safety_warning"),
            "scope": needle_res.get("scope", "minor_swap"),
            "message": needle_res.get("message"),
            "updated_itinerary": it,
        }

    if needle_res.get("success"):
        action = needle_res.get("action", "modified")
        scope = needle_res.get("scope", "minor_swap")
        target_day = needle_res.get("day", 1)
        removed_name = needle_res.get("target_place")
        added_name = needle_res.get("added_place")

        if removed_name and added_name:
            message = f"Replaced '{removed_name}' with '{added_name}' on Day {target_day}."
        elif added_name:
            message = f"Added '{added_name}' on Day {target_day}."
        elif removed_name:
            message = f"Removed '{removed_name}' from Day {target_day}."
        else:
            message = f"Updated Day {target_day} of your itinerary."

        # Only facts we actually know are returned; no estimated metrics are
        # invented. Clients should hide metric fields that are absent.
        return {
            "success": True,
            "scope": scope,
            "message": message,
            "updated_itinerary": needle_res["result"].get("itinerary", it),
            "diff": {
                "action": action,
                "scope": scope,
                "dayNum": target_day,
                "removedName": removed_name,
                "addedName": added_name,
            }
        }

    return {
        "success": False,
        "message": needle_res.get("error", "Cactus Needle could not apply the requested modification."),
        "updated_itinerary": it,
    }


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve the caller's chat session history."""
    record = _load_session(db, user, session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "messages": _get_history(record)}


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Clear the caller's chat session."""
    record = _load_session(db, user, session_id)
    if record is not None:
        db.delete(record)
        db.commit()
    return {"status": "cleared"}
