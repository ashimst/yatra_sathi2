"""
YatraSathi Nepal - Hugging Face Spaces Entrypoint (Gradio SDK)

This entrypoint serves dual roles:
1. Full REST API: Exposes all FastAPI endpoints (/health, /recommend, /places, /ai, /docs)
   for external frontends (Cloudflare Pages, Vercel, mobile apps).
2. Interactive Gradio UI: Directly accessible in the Hugging Face Space for trip planning,
   destination exploration, and AI travel companionship.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional, Any

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import gradio as gr
import uvicorn

# Import backend application and services
from backend.app.main import app as fastapi_app
from backend.app.services.place_service import place_service
from backend.app.services.recommendation_service import recommendation_service
from backend.app.db.database import SessionLocal
from backend.app.models.place import Place


# ─────────────────────────────────────────────────────────────────────────────
# Pre-defined Major Nepal Hubs
# ─────────────────────────────────────────────────────────────────────────────
POPULAR_LOCATIONS = {
    "Kathmandu": (27.7172, 85.3240),
    "Pokhara": (28.2096, 83.9856),
    "Chitwan (Sauraha)": (27.5816, 84.4947),
    "Lumbini": (27.4839, 83.2758),
    "Nagarkot": (27.7174, 85.5204),
    "Bandipur": (27.9304, 84.4172),
    "Janakpur": (26.7271, 85.9407),
    "Bhaktapur": (27.6710, 85.4298),
    "Patan (Lalitpur)": (27.6744, 85.3247),
    "Dhulikhel": (27.6200, 85.5539),
    "Gorkha": (28.0055, 84.6300),
}


# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions for Gradio UI
# ─────────────────────────────────────────────────────────────────────────────

async def plan_itinerary_gradio(
    origin_name: str,
    dest_name: str,
    num_days: int,
    travel_style: str,
    budget: str,
    interests: List[str]
) -> str:
    """Generate day-by-day itinerary via recommendation_service."""
    try:
        origin_coords = POPULAR_LOCATIONS.get(origin_name, (27.7172, 85.3240))
        dest_coords = POPULAR_LOCATIONS.get(dest_name, (28.2096, 83.9856))

        result = await recommendation_service.get_route_recommendations(
            origin_lat=origin_coords[0],
            origin_lng=origin_coords[1],
            dest_lat=dest_coords[0],
            dest_lng=dest_coords[1],
            user_preferences=interests,
            num_days=int(num_days),
            travel_style=travel_style.lower(),
            budget=budget.lower(),
            generate_itinerary=True
        )

        route_info = result.get("route", {})
        distance = route_info.get("distance_km", 0)
        duration_hrs = round(route_info.get("duration_minutes", 0) / 60, 1)
        itinerary = result.get("itinerary", {})
        days = itinerary.get("days", [])

        md = []
        md.append(f"## 🗺️ {num_days}-Day Itinerary: {origin_name} $\\to$ {dest_name}")
        md.append(f"**Total Distance**: ~{distance:.1f} km &nbsp;|&nbsp; **Estimated Driving Time**: ~{duration_hrs} hrs &nbsp;|&nbsp; **Pace**: {travel_style} &nbsp;|&nbsp; **Budget**: {budget}\n")

        if not days:
            pois = result.get("recommendations", [])
            md.append("### Recommended En-Route Stops:")
            for p in pois[:15]:
                md.append(f"- **{p.get('name', 'Place')}** ({p.get('category', 'Spot')}): {p.get('description', '')[:140]}...")
            return "\n".join(md)

        for day in days:
            day_num = day.get("day", 1)
            title = day.get("title", f"Day {day_num}")
            theme = day.get("theme", "")
            md.append(f"### 📍 Day {day_num}: {title}")
            if theme:
                md.append(f"*{theme}*\n")

            stops = day.get("stops", [])
            for stop in stops:
                time_slot = stop.get("time_slot", "").capitalize()
                place_name = stop.get("name", "Stop")
                category = stop.get("category", "Activity")
                desc = stop.get("description", "")
                md.append(f"- **{time_slot}** — **{place_name}** (`{category}`): {desc}")

            hotel = day.get("lodging") or day.get("hotel")
            if hotel:
                h_name = hotel.get("name") if isinstance(hotel, dict) else str(hotel)
                md.append(f"- 🏨 **Overnight**: {h_name}")
            md.append("")

        return "\n".join(md)

    except Exception as e:
        return f"⚠️ Error generating itinerary: {str(e)}"


def search_destinations_gradio(query: str, category: Optional[str]) -> List[List[Any]]:
    """Search destinations in the 29K Nepal places database."""
    try:
        with SessionLocal() as db:
            q = db.query(Place).filter(Place.name.isnot(None))
            if query and query.strip():
                q = q.filter(Place.name.ilike(f"%{query.strip()}%"))
            if category and category != "All":
                q = q.filter(Place.category == category)
            
            results = q.limit(30).all()
            table_data = []
            for p in results:
                table_data.append([
                    p.name or "N/A",
                    p.category or "place",
                    p.district or "Nepal",
                    round(p.latitude, 4) if p.latitude else 0.0,
                    round(p.longitude, 4) if p.longitude else 0.0,
                    (p.description or "")[:120] + ("..." if p.description and len(p.description) > 120 else "")
                ])
            return table_data
    except Exception as e:
        return [["Database Connection Note", "DB", "Config", 0, 0, f"Configure DATABASE_URL to query live DB ({e})"]]


async def chat_companion_gradio(message: str, history: List[dict]) -> str:
    """Interactive travel assistant powered by curated place search & Groq."""
    try:
        # Search places directly
        places_data = place_service.search_places(message, limit=3)
        places = places_data.get("places", [])
        if places and any(w in message.lower() for w in ["place", "where", "visit", "recommend", "hotel", "food", "temple", "lake"]):
            details = "\n".join([f"• **{p['name']}** ({p.get('category','Spot')}): {p.get('description','')[:100]}..." for p in places])
            return f"Here are great recommendations across Nepal matching your request:\n\n{details}"

        # Otherwise answer via general context
        groq_api_key = os.getenv("GROQ_API_KEY")
        if groq_api_key:
            import httpx
            messages = [
                {"role": "system", "content": "You are YatraSathi, a warm and deeply knowledgeable Himalayan travel guide for Nepal. Provide concise, vivid, practical advice."}
            ]
            for h in history[-4:]:
                role = h.get("role", "user")
                content = h.get("content", "")
                if role in ("user", "assistant"):
                    messages.append({"role": role, "content": content})
            messages.append({"role": "user", "content": message})

            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"},
                    json={
                        "model": os.getenv("LLM_MODEL", "qwen/qwen3.8-27b"),
                        "messages": messages,
                        "temperature": 0.4,
                        "max_tokens": 500
                    }
                )
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"]
                return "Happy travels in Nepal! What destinations are you exploring?"

        return f"YatraSathi Guide: You asked about '{message}'. To enable full conversational LLM responses, set the GROQ_API_KEY secret in Space settings."

    except Exception as e:
        return f"I'm here to help with your Nepal travels! (Notice: {e})"


# ─────────────────────────────────────────────────────────────────────────────
# Build Gradio UI
# ─────────────────────────────────────────────────────────────────────────────

def create_gradio_demo():
    custom_theme = gr.themes.Soft(
        primary_hue="emerald",
        secondary_hue="teal",
        neutral_hue="slate"
    )

    with gr.Blocks(theme=custom_theme, title="YatraSathi Nepal — Intelligent Travel Companion") as demo:
        gr.Markdown(
            """
            # 🏔️ YatraSathi Nepal (यात्रा साथी)
            ### *Intelligent Himalayan Travel Companion, Route Recommender & AI Planner*
            
            Welcome to the live engine of **YatraSathi**. This space hosts both the **FastAPI REST API** and this interactive UI.
            """
        )

        with gr.Tabs():
            # ──────── TAB 1: TRIP PLANNER ────────
            with gr.TabItem("🧭 Itinerary Planner"):
                gr.Markdown("#### Generate optimized multi-day routes across Nepal using geospatial corridors and pgvector scoring.")
                with gr.Row():
                    with gr.Column(scale=1):
                        origin_input = gr.Dropdown(
                            choices=list(POPULAR_LOCATIONS.keys()),
                            value="Kathmandu",
                            label="Origin"
                        )
                        dest_input = gr.Dropdown(
                            choices=list(POPULAR_LOCATIONS.keys()),
                            value="Pokhara",
                            label="Destination"
                        )
                        days_input = gr.Slider(
                            minimum=1,
                            maximum=10,
                            value=3,
                            step=1,
                            label="Trip Duration (Days)"
                        )
                        pace_input = gr.Radio(
                            choices=["Relaxed", "Balanced", "Fast-paced"],
                            value="Balanced",
                            label="Travel Pace"
                        )
                        budget_input = gr.Radio(
                            choices=["Budget", "Medium", "Luxury"],
                            value="Medium",
                            label="Budget Level"
                        )
                        interests_input = gr.CheckboxGroup(
                            choices=["Nature", "Heritage", "Adventure", "Spiritual", "Photography", "Local Food"],
                            value=["Nature", "Heritage", "Photography"],
                            label="Interests"
                        )
                        plan_button = gr.Button("🚀 Generate Itinerary", variant="primary")

                    with gr.Column(scale=2):
                        itinerary_output = gr.Markdown(
                            value="*Select your trip parameters on the left and click **Generate Itinerary** to preview your custom Himalayan journey.*"
                        )

                plan_button.click(
                    fn=plan_itinerary_gradio,
                    inputs=[origin_input, dest_input, days_input, pace_input, budget_input, interests_input],
                    outputs=itinerary_output
                )

            # ──────── TAB 2: EXPLORE DESTINATIONS ────────
            with gr.TabItem("🗺️ Destination Explorer"):
                gr.Markdown("#### Search and browse 29,583 Nepal destinations, temples, viewpoints, and hidden gems.")
                with gr.Row():
                    search_query = gr.Textbox(
                        placeholder="Search by name (e.g., Phewa Lake, Pashupatinath, Annapurna, Lumbini)...",
                        label="Destination Search",
                        scale=3
                    )
                    category_filter = gr.Dropdown(
                        choices=["All", "attraction", "lodging", "restaurant", "viewpoint", "temple", "lake"],
                        value="All",
                        label="Category",
                        scale=1
                    )
                    search_btn = gr.Button("🔍 Search", scale=1)

                places_table = gr.Dataframe(
                    headers=["Name", "Category", "District", "Latitude", "Longitude", "Description"],
                    datatype=["str", "str", "str", "number", "number", "str"],
                    value=lambda: search_destinations_gradio("Pokhara", "All"),
                    interactive=False
                )

                search_btn.click(
                    fn=search_destinations_gradio,
                    inputs=[search_query, category_filter],
                    outputs=places_table
                )

            # ──────── TAB 3: AI TRAVEL ASSISTANT ────────
            with gr.TabItem("💬 Ask AI Companion"):
                gr.Markdown("#### Chat with YatraSathi's AI assistant about local customs, best seasons, permits, packing, and road conditions.")
                gr.ChatInterface(
                    fn=chat_companion_gradio,
                    type="messages",
                    examples=[
                        "What is the best route from Kathmandu to Pokhara with scenic stops?",
                        "What permits do I need for trekking in Annapurna?",
                        "Recommend top traditional Newari foods to try in Bhaktapur.",
                        "What should I pack for Chitwan National Park in November?"
                    ]
                )

            # ──────── TAB 4: API & ARCHITECTURE ────────
            with gr.TabItem("🔌 REST API & Frontend"):
                gr.Markdown(
                    """
                    ### 🌐 Connecting Your Frontend & Client Apps
                    This Hugging Face Space runs the full production **FastAPI backend** on the exact same port!
                    
                    - **Swagger UI Documentation**: [Open /docs](/docs)
                    - **System Health Check**: [Check /health](/health)
                    - **Base API URL for Frontend**:
                      ```bash
                      VITE_API_BASE_URL=https://<your-hf-username>-<your-space-name>.hf.space
                      ```
                    
                    #### 🚀 Endpoints Available for External Clients:
                    | Method | Endpoint | Description |
                    |---|---|---|
                    | `GET` | `/health` | System status, destination count & AI readiness |
                    | `POST` | `/recommend` | Route corridor buffer POI search & day-by-day planner |
                    | `GET` | `/places/search?q=...` | Full-text destination search |
                    | `POST` | `/ai/chat` | Intent classification & AI companion chat |
                    | `GET` | `/docs` | Interactive Swagger API schema |
                    """
                )

        gr.Markdown(
            "---\n*Built with ❤️ for travelers exploring Nepal. Powered by FastAPI, PostgreSQL PostGIS/pgvector, Groq LLaMA 3.3, and Gradio on Hugging Face Spaces.*"
        )

    return demo


# ─────────────────────────────────────────────────────────────────────────────
# Mount Gradio onto FastAPI
# ─────────────────────────────────────────────────────────────────────────────
demo = create_gradio_demo()
app = gr.mount_gradio_app(fastapi_app, demo, path="/")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    print(f"Starting YatraSathi on port {port}...")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
