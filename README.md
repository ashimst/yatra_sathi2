# YatraSathi (यात्रा साथी)

A travel-planning companion for Nepal. YatraSathi builds multi-day itineraries
along real road corridors, recommends places using geospatial and semantic
search over ~7,700 places, and includes an AI assistant, a photo-memory
scrapbook, and a community trail-conditions board.

## Features

- **Trip planner (`/plan`)**: routes between two places via OSRM, picks
  attractions, meals and stays within a corridor around the route, and builds a
  day-by-day itinerary based on pace, budget and interests. An AI co-pilot can
  edit the itinerary from natural-language requests; edits are shown as a diff
  before they're applied.
- **Explore & map (`/explore`, `/map`)**: browse and search places. Semantic
  ranking uses 384-dimensional `BAAI/bge-small-en-v1.5` embeddings stored in
  PostgreSQL with pgvector.
- **AI assistant**: Groq-hosted LLM with tool calls for place search and
  geocoding. Chat history is stored per user.
- **Memories (`/memories`)**: upload trip photos with captions; images are
  validated by file signature and stored under random file names.
- **Trail Watch (`/trail-watch`)**: travelers post trail hazards so others can
  see them. YatraSathi is an independent platform: reports are **not** sent to
  any authority or conservation body, and no affiliation is implied. In an
  emergency, call Nepal Police (100) or the Tourist Police (1144).
- **Saved & shared trips**: save itineraries to your account and share a
  read-only public link.

## Architecture

```
yatra_sathi/
├── backend/          FastAPI app (Python 3.11)
│   ├── app/
│   │   ├── api/      REST routers (auth, places, recommend, route, ai, itineraries,
│   │   │             memories, trail-watch, uploads)
│   │   ├── core/     JWT/bcrypt security, auth dependencies, rate limiting
│   │   ├── config/   pydantic-settings configuration (fail-fast in production)
│   │   ├── db/       SQLAlchemy engine & sessions
│   │   ├── models/   ORM models
│   │   └── services/ recommendation, embeddings, routing, uploads, AI tools
│   ├── data/seeds/   curated seed datasets (trails, waypoints, heritage, festivals)
│   └── scripts/      seeding
├── etl/              OpenStreetMap → normalized/enriched places → embeddings
├── scripts/          DB setup/restore, ETL runner, embedding generation, data fixes
├── web/              React 19 + TypeScript + Vite + Tailwind + Leaflet
├── mobile/           Flutter client
├── tests/            pytest suite (e2e, adversarial, security)
├── terraform/        Azure Container Apps infrastructure
├── docker/           PostgreSQL + PostGIS + pgvector image for local dev
└── docker-compose.yml  local development stack
```

**Production stack:** Azure Container Apps (API) · Supabase PostgreSQL with
PostGIS + pgvector · Cloudflare Pages (web). See [DEPLOYMENT.md](DEPLOYMENT.md).

## Local development

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 16 with PostGIS and pgvector (or Docker)

### Option A: Docker Compose

```bash
# .env in the project root must define POSTGRES_PASSWORD (GROQ_API_KEY optional)
docker compose up --build
```
Web: http://localhost:3000 · API: http://localhost:8000 (docs at `/docs`)

### Option B: run services directly

```bash
python -m venv venv
source venv/bin/activate            # Windows: .\venv\Scripts\activate

# CPU-only torch avoids downloading CUDA libraries
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r backend/requirements-dev.txt

cp .env.example .env                # then set DATABASE_URL, GROQ_API_KEY, ...
python -m uvicorn backend.app.main:app --reload --port 8000
```

```bash
cd web
npm install
npm run dev                         # http://localhost:5173
```

### Loading data
Restore the pre-built database dump (`python scripts/restore_database.py`,
dump distributed separately, not in git) or rebuild from OpenStreetMap with
`python scripts/run_pipeline.py`, then run `python scripts/generate_embeddings.py`.
`EMBEDDING_MODEL` must match the model used for the stored vectors.

## Testing

```bash
pytest                 # backend: e2e, adversarial and security suites
cd web && npm run build && npm run lint
```

## Configuration

All settings are environment variables; see [.env.example](.env.example) for
development and [.env.production.example](.env.production.example) for
production. With `ENVIRONMENT=production` the API refuses to start if the JWT
secret is missing or weak, CORS allows `*`, or required keys are missing.

## Data sources

Place data is derived from OpenStreetMap (© OpenStreetMap contributors, ODbL)
and enriched by the ETL pipeline in `etl/`.
