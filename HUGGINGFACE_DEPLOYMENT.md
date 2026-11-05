# 🚀 Deploying YatraSathi to Hugging Face Spaces (Gradio SDK)

Hugging Face Spaces provides **2 vCPUs and 16 GB RAM for 100% free**. Since Docker is no longer available on the free tier, we use the **Gradio SDK** with our dual-mounting architecture:

- **Gradio Interactive UI** (`/`): A user-friendly dashboard for itinerary planning, place searching, and AI chat.
- **FastAPI REST API Engine** (`/recommend`, `/places`, `/ai`, `/health`, `/docs`): Fully exposed on the same domain with CORS enabled for your **Cloudflare Pages / Vercel** React frontend!

---

## 🛠️ Step 1: Set Up Free PostgreSQL (Supabase or Neon)

Since Hugging Face Spaces filesystem is ephemeral, your database needs to reside on a managed PostgreSQL host with **PostGIS** and **pgvector**.

1. Go to [Supabase](https://supabase.com) and create a free project.
2. In the Supabase **SQL Editor**, enable the extensions:
   ```sql
   CREATE EXTENSION IF NOT EXISTS postgis;
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
3. Get your connection string from **Project Settings** $\to$ **Database** $\to$ **Connection string (URI)**:
   ```
   postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
   ```
4. Restore the pre-populated 29,583 Nepal places dataset (102 MB) from your local machine:
   ```bash
   python scripts/restore_database.py
   ```
   *(Or run `pg_restore -d "<YOUR_SUPABASE_DATABASE_URL>" --clean --if-exists --no-owner --no-privileges -v data/yatra_sathi.dump`)*

---

## 🏔️ Step 2: Create a Hugging Face Space

1. Log into [Hugging Face](https://huggingface.co) and click **New Space**.
2. Configure:
   - **Space Name**: `yatrasathi-nepal` (or your preferred name)
   - **License**: `mit` or `apache-2.0`
   - **Select the Space SDK**: Choose **Gradio**
   - **Space hardware**: **CPU Basic • 2 vCPU • 16 GB • Free**
   - **Visibility**: **Public**
3. Click **Create Space**.

---

## 🔐 Step 3: Add Space Secrets (Environment Variables)

In your Hugging Face Space page:
1. Go to **Settings** $\to$ **Variables and secrets**.
2. Under **Secrets**, add the following:

| Secret Name | Value | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres` | PostGIS + pgvector database |
| `GROQ_API_KEY` | `gsk_your_groq_api_key` | Free LLaMA 3.3 70B trip refinement & chat |
| `JWT_SECRET_KEY` | `your_random_64_character_secret` | Auth & guest tokens |
| `OSRM_URL` | `https://router.project-osrm.org` | Road network routing engine |
| `CORS_ORIGINS` | `*` | Allows your frontend to make API calls |

---

## 📤 Step 4: Push Code to Hugging Face

Clone your new Hugging Face Space repository:

```bash
git clone https://huggingface.co/spaces/<your-username>/yatrasathi-nepal hf_space
cd hf_space
```

Copy the required project files into the Space directory:
- `app.py` (Hugging Face Gradio + FastAPI entrypoint)
- `README.md` (Contains the Hugging Face YAML metadata)
- `requirements.txt` (Python dependencies)
- `backend/` (FastAPI backend codebase)
- `etl/` (Embedding & route calculation helpers)
- `data/` (Optional local reference files)

Commit and push:

```bash
git add .
git commit -m "Deploy YatraSathi to Hugging Face Spaces"
git push
```

Hugging Face will automatically install dependencies, download `all-MiniLM-L6-v2`, connect to your database, and launch!

---

## 🌐 Step 5: Connect Your Cloudflare Pages React Frontend

Your Hugging Face Space has a direct public URL:
`https://<your-username>-<space-name>.hf.space`

You can deploy the React app ([web](file:///c:/Projects/yatra_sathi/web)) on **Cloudflare Pages** or **Vercel** for free:
1. In Cloudflare Pages or Vercel, set the environment variable:
   ```env
   VITE_API_BASE_URL=https://<your-username>-<space-name>.hf.space
   ```
2. Build command: `npm run build`
3. Output directory: `dist`

Now your web frontend runs at edge speed on Cloudflare Pages, calling the 16 GB RAM FastAPI backend on Hugging Face Spaces, with zero hosting cost!
