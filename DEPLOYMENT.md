# 🚀 YatraSathi Production Deployment Guide

This document provides complete, step-by-step instructions for deploying **YatraSathi Nepal** across various hosting environments.

---

## 🏗️ Architecture Overview

| Component | Technology | Default Port | Production Role |
|---|---|---|---|
| **Web Frontend** | React 19, TypeScript, Vite, Tailwind CSS, Leaflet | `3000` (dev) / `80` (prod) | Interactive travel planner, offline-ready print briefs, photo journals |
| **Backend API** | FastAPI, Uvicorn, LangGraph, Decision Engine | `8000` | Travel recommendations, OSRM routing, AI editing, auth & saved yatras |
| **Database** | PostgreSQL 15/16 + **PostGIS** + **pgvector** | `5432` | Geo-spatial indexing, 384-dim semantic embeddings, user profiles & itineraries |
| **Routing** | OSRM (Open Source Routing Machine) | Remote / `5000` | Road network routing and drive duration calculations |
| **LLM Provider** | Groq (`llama-3.3-70b-versatile`) | API | Natural language travel companionship & real-time itinerary refinement |

---

## 📋 Pre-Deployment Checklist

Before deploying, ensure you have:
1. **Groq API Key**: Obtain a free API key at [console.groq.com](https://console.groq.com).
2. **PostgreSQL with PostGIS & pgvector**: Either self-hosted via Docker or managed (e.g. Supabase, Neon, Render Postgres).
3. **JWT Secret Key**: Generate a 64-character secret using:
   ```bash
   openssl rand -hex 32
   ```

---

## ⚡ Option 1: 1-Command Docker Compose (Recommended for VPS / Cloud Instances)

Ideal for DigitalOcean Droplet, Hetzner, AWS EC2, Linode, or any Linux server with Docker.

### 1. Clone & Enter Repository
```bash
git clone https://github.com/ashimst/yatra_sathi.git
cd yatra_sathi
```

### 2. Configure Environment
```bash
cp .env.production.example .env
```
Edit `.env` and configure:
```env
GROQ_API_KEY=gsk_your_actual_groq_key
JWT_SECRET_KEY=your_generated_random_secret_key
POSTGRES_PASSWORD=your_secure_db_password
```

### 3. Build & Launch Containers
```bash
docker compose up -d --build
```
This launches 3 synchronized containers:
- `yatrasathi_db`: PostgreSQL 16 with PostGIS & pgvector auto-initialized
- `yatrasathi_backend`: FastAPI ASGI server with auto-healthchecks
- `yatrasathi_web`: High-performance Nginx Alpine container serving the built React app and reverse-proxying API endpoints

### 4. Seed the Nepal Destinations Data
Restore the curated database dump (61 MB of Nepal places, coordinates, and embeddings):
```bash
docker exec -i yatrasathi_db pg_restore -U postgres -d yatra_sathi --clean --if-exists < data/yatra_sathi.dump
```

### 5. Access the Application
- **Web App**: `http://<your-server-ip>:3000` (or port `80` if configured)
- **API Health**: `http://<your-server-ip>:8000/health`
- **Swagger Documentation**: `http://<your-server-ip>:8000/docs`

---

## 🌐 Option 2: Serverless / Cloud PaaS (Zero Ops & Recruiter Showcase)

Deploy in under 10 minutes with free-tier providers.

### Step 2.1: Database (Supabase or Neon)
1. Create a free account at [Supabase](https://supabase.com) or [Neon](https://neon.tech).
2. Create a new PostgreSQL database.
3. In the SQL Editor, enable the two extensions:
   ```sql
   CREATE EXTENSION IF NOT EXISTS postgis;
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
4. Restore the destination dump using your local machine or terminal:
   ```bash
   pg_restore --clean --if-exists --no-owner --no-privileges -d "<YOUR_SUPABASE_OR_NEON_DATABASE_URL>" -v data/yatra_sathi.dump
   ```
   *(Or run `python scripts/restore_database.py` with `DATABASE_URL` set in `.env`)*.

---

### Step 2.2: Backend (Render or Railway)

#### Via Render (Using `render.yaml` Blueprint)
1. Push your repository to GitHub.
2. In [Render Dashboard](https://dashboard.render.com), click **New +** → **Blueprint**.
3. Connect your repository. Render automatically reads [render.yaml](file:///c:/Projects/yatra_sathi/render.yaml).
4. Supply your `GROQ_API_KEY` and database credentials in the prompts.
5. Click **Apply**. Your backend will be deployed with URL: `https://yatrasathi-backend.onrender.com`.

#### Via Railway
1. Go to [Railway.app](https://railway.app), click **New Project** → **Deploy from GitHub repo**.
2. Select the repository. Railway will detect the [Procfile](file:///c:/Projects/yatra_sathi/Procfile) or [Dockerfile](file:///c:/Projects/yatra_sathi/backend/Dockerfile).
3. Under **Variables**, add:
   - `DATABASE_URL`: Your database connection string
   - `GROQ_API_KEY`: Your Groq API key
   - `JWT_SECRET_KEY`: Secret string
   - `CORS_ORIGINS`: `*` (or your frontend domain)
   - `OSRM_URL`: `https://router.project-osrm.org`

---

### Step 2.3: Frontend (Cloudflare Pages, Vercel, or Netlify)

#### Option A: Via Cloudflare Pages (Recommended - 100% Free & Global Edge)
1. In the [Cloudflare Dashboard](https://dash.cloudflare.com/), navigate to **Workers & Pages** → **Create application** → **Pages** → **Connect to Git**.
2. Select your `yatra_sathi` repository.
3. In the **Set up builds and deployments** page:
   - **Project name**: `yatrasathi` (or preferred name)
   - **Production branch**: `main` (or `master`)
   - **Framework preset**: `Vite`
   - **Root directory**: `web`
   - **Build command**: `npm run build`
   - **Build output directory**: `dist`
4. Expand **Environment variables** and add:
   - Variable name: `VITE_API_BASE_URL`
   - Value: `https://yatrasathi-backend.onrender.com` (your deployed backend URL)
   - *(Optional)* Variable name: `NODE_VERSION`, Value: `20`
5. Click **Save and Deploy**.
   - Cloudflare will build the site and deploy it globally.
   - SPA routing (`/plan`, `/explore`, `/share/:id`) and asset caching are handled automatically by [`web/public/_redirects`](file:///c:/Projects/yatra_sathi/web/public/_redirects) and [`web/public/_headers`](file:///c:/Projects/yatra_sathi/web/public/_headers).

#### Option B: Deploying to Cloudflare Pages via CLI (Wrangler)
If deploying directly from your machine or CI/CD without Git connection:
```bash
cd web
npm run build
npx wrangler pages deploy dist --project-name=yatrasathi
```

#### Option C: Via Vercel
1. Go to [Vercel](https://vercel.com) and click **Add New** → **Project**.
2. Import your GitHub repository.
3. Configure the build settings:
   - **Root Directory**: `web`
   - **Framework Preset**: `Vite`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Under **Environment Variables**, add:
   ```env
   VITE_API_BASE_URL=https://yatrasathi-backend.onrender.com
   ```
5. Click **Deploy**.

---

## 🔒 Production Security & Hardening Checklist

1. **HTTPS Enforcement**: Always front public traffic with SSL/TLS (automatic on Vercel, Netlify, Render, or via Let's Encrypt / Certbot on VPS).
2. **Restrict CORS in Production**:
   Update `CORS_ORIGINS` in your backend environment:
   ```env
   CORS_ORIGINS=https://yatrasathi.com,https://your-frontend.vercel.app
   ```
3. **JWT Secret**: Never use default keys. Ensure `JWT_SECRET_KEY` is long and random.
4. **Database Connection Pooling**:
   When connecting serverless functions or multiple workers to PostgreSQL, use connection pooling (e.g. Supabase PgBouncer or Neon connection pooler URL on port 6543).

---

## 🩺 Monitoring & Diagnostics

- **Health Check Endpoint**:
  ```bash
  curl https://api.yourdomain.com/health
  ```
  Expected response:
  ```json
  {
    "status": "ok",
    "service": "YatraSathi Backend",
    "version": "1.0.0",
    "destinations_count": 528,
    "ai_enabled": true
  }
  ```
- **Backend Logs (Docker)**:
  ```bash
  docker compose logs -f backend
  ```
- **Database Logs**:
  ```bash
  docker compose logs -f db
  ```
