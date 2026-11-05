# 🚀 YatraSathi Production Serverless Deployment Guide

> **Target Topology**: Azure Container Apps (Serverless, Scale to Zero) + Supabase (PostGIS & pgvector) + Cloudflare Pages (Frontend CDN) + GitHub Actions CI/CD  
> **Target Domain**: `yatrasathi.noesisframeworks.com` & `api.yatrasathi.noesisframeworks.com`  
> **Estimated Idle Cost**: **$0.00 / month** (Tailored specifically for Azure for Students & free tier limits)

---

## 🏗️ Architecture & Cost Breakdown

| Component | Provider / Service | Sizing / Plan | Monthly Cost (Idle / Low Usage) |
|---|---|---|---|
| **Backend API** | **Azure Container Apps** | Consumption Plan (0 to 3 replicas, 0.25 vCPU, 0.5 GiB) | **$0.00** (Free allowance: 180,000 vCPU-s & 360,000 GiB-s/mo) |
| **Container Registry** | **GitHub Container Registry (ghcr.io)** | Free Package Hosting (Direct pull from GitHub) | **$0.00** (100% Free on GitHub) |
| **Database** | **Supabase** | Free Tier (PostgreSQL 16 + PostGIS + pgvector) | **$0.00** |
| **Frontend CDN** | **Cloudflare Pages** | Free Tier (Unlimited bandwidth, Global Edge) | **$0.00** |
| **CI/CD** | **GitHub Actions** | Free Tier (2,000 build min/mo) | **$0.00** |
| **SSL / HTTPS** | **Cloudflare & Azure** | Automated Managed TLS Certificates | **$0.00** |
| **Total** | | | **$0.00 / month** |

> [!TIP]
> **Why GitHub Container Registry (ghcr.io)?**  
> Azure Container Registry (ACR) charges ~$4.80/month just for basic image storage. By using **GitHub Container Registry (`ghcr.io`)**, container storage and bandwidth are **100% free**, bringing your Azure bill to **$0.00**.

---

## 📋 Pre-Flight Checklist

Before you begin, ensure you have:
1. **Azure CLI** installed (`az login`).
2. **Terraform CLI** installed (`terraform -v >= 1.5.0`).
3. **Supabase Account**: [supabase.com](https://supabase.com) (free).
4. **Cloudflare Account**: [cloudflare.com](https://cloudflare.com) (free).
5. **Access to `noesisframeworks.com` DNS management** (in Cloudflare or your domain registrar).

---

## 🛠️ Step 1: Set Up Supabase Database (PostGIS & pgvector)

1. Log into [supabase.com](https://supabase.com) and click **New Project** (select region closest to your users, e.g., `Southeast Asia (Singapore)`).
2. Go to **SQL Editor** and run:
   ```sql
   -- Enable spatial and vector extensions
   CREATE EXTENSION IF NOT EXISTS postgis;
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
3. Copy your database connection string from **Project Settings** $\to$ **Database** $\to$ **Connection string (URI)**. Select **Transaction Pooler (Port 6543)** for serverless workloads:
   ```
   postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=require
   ```
4. Seed the initial Nepal datasets into Supabase from your local workspace:
   ```bash
   python backend/scripts/seed_nepal_data.py
   ```

---

## ☁️ Step 2: Provision Azure Infrastructure with Terraform

The provided Terraform code in `terraform/` automatically configures:
- Azure Resource Group (`rg-yatrasathi-prod`)
- Azure Log Analytics Workspace (30-day retention)
- Azure Container Apps Environment (Serverless Consumption)
- Azure Container App pulling from **`ghcr.io`** with `min_replicas = 0` (scale-to-zero)

### 1. Initialize Terraform
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

### 2. Configure `terraform.tfvars`
Fill in your secrets:
```hcl
app_name              = "yatrasathi"
environment           = "prod"
azure_region          = "southeastasia" # or "eastus"
github_username       = "your_github_username" # e.g. ashimst
github_pat            = ""                     # Leave empty if package will be Public on GitHub
supabase_database_url = "postgresql://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=require"
groq_api_key          = "gsk_your_groq_api_key"
jwt_secret_key        = "your_random_64_character_hex_secret"
custom_domain         = "yatrasathi.noesisframeworks.com"
api_subdomain         = "api.yatrasathi.noesisframeworks.com"
```

### 3. Apply Terraform
```bash
az login
terraform init
terraform plan
terraform apply -auto-approve
```

Terraform outputs will display:
- `ghcr_image_source`: e.g. `ghcr.io/ashimst/yatrasathi-backend:latest`
- `container_app_fqdn`: e.g. `ca-yatrasathi-api-prod.gentlegrass-12345.southeastasia.azurecontainerapps.io`
- `custom_domain_verification_id`: Verification code for DNS TXT record.

---

## 🌐 Step 3: Configure Domain & DNS Records (`noesisframeworks.com`)

Log in to your DNS provider (Cloudflare dashboard for `noesisframeworks.com`):

| Type | Name (Subdomain) | Value / Target | Proxy Status | Purpose |
|---|---|---|---|---|
| **CNAME** | `yatrasathi` | `<your-pages-project>.pages.dev` | **Proxied (Orange Cloud)** | Frontend Web UI |
| **CNAME** | `api.yatrasathi` | `<container_app_fqdn>` | **DNS Only (Grey Cloud)** | Serverless Backend API |
| **TXT** | `asuid.api.yatrasathi` | `<custom_domain_verification_id>` | **DNS Only** | Azure Domain Verification |

> [!NOTE]
> Azure Container Apps requires the `asuid` TXT verification record to validate domain ownership before issuing free managed SSL certificates for `api.yatrasathi.noesisframeworks.com`.

---

## ⚡ Step 4: Set Up Cloudflare Pages (Frontend Hosting)

1. In the **Cloudflare Dashboard**, navigate to **Workers & Pages** $\to$ **Create application** $\to$ **Pages** $\to$ **Connect to Git**.
2. Select your repository.
3. Set build configuration:
   - **Framework preset**: `Vite`
   - **Root directory**: `web`
   - **Build command**: `npm run build`
   - **Build output directory**: `dist`
4. Add Environment Variable:
   - `VITE_API_BASE_URL`: `https://api.yatrasathi.noesisframeworks.com`
5. Click **Save and Deploy**.
6. Under **Custom Domains**, add `yatrasathi.noesisframeworks.com`. Cloudflare will provision an SSL certificate in ~60 seconds.

---

## 🔄 Step 5: Configure GitHub Actions CI/CD Secrets

To enable automated zero-touch deployment on every `git push origin main`:

1. In GitHub, go to **Settings** $\to$ **Secrets and variables** $\to$ **Actions** $\to$ **New repository secret**.
2. Add the following secrets:

### Azure Backend Secrets:
- `AZURE_CREDENTIALS`: Azure Service Principal JSON (generate with: `az ad sp create-for-rbac --name "github-actions-yatrasathi" --role contributor --scopes /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/rg-yatrasathi-prod --sdk-auth`)
- `AZURE_CONTAINER_APP_NAME`: `ca-yatrasathi-api-prod`
- `AZURE_RESOURCE_GROUP`: `rg-yatrasathi-prod`
- `AZURE_CONTAINER_APP_FQDN`: Container App FQDN from Terraform

*(Notice: No ACR login or password needed! GitHub automatically uses `${{ secrets.GITHUB_TOKEN }}` to publish to `ghcr.io`)*

### Making Your GHCR Package Public (Recommended for 100% Free Pulls):
Once the first GitHub Action run pushes the package:
1. Go to your GitHub Profile $\to$ **Packages** $\to$ select `yatrasathi-backend`.
2. Go to **Package settings** $\to$ Scroll to **Danger Zone** $\to$ **Change package visibility** $\to$ Set to **Public**.
3. Now Azure Container Apps can pull the image anonymously with zero authentication credentials needed!
- `AZURE_ACR_LOGIN_SERVER`: Output from Terraform (e.g. `acryatrasathiprod.azurecr.io`)
- `AZURE_ACR_USERNAME`: ACR Admin Username
- `AZURE_ACR_PASSWORD`: ACR Admin Password
- `AZURE_CONTAINER_APP_NAME`: `ca-yatrasathi-api-prod`
- `AZURE_RESOURCE_GROUP`: `rg-yatrasathi-prod`
- `AZURE_CONTAINER_APP_FQDN`: Container App FQDN from Terraform

### Cloudflare Frontend Secrets:
- `CLOUDFLARE_API_TOKEN`: Cloudflare Pages Edit API Token
- `CLOUDFLARE_ACCOUNT_ID`: Your Cloudflare Account ID

---

## ✅ Step 6: Verification & Cold-Start Behavior

1. **Verify Backend Health**:
   ```bash
   curl -I https://api.yatrasathi.noesisframeworks.com/health
   # Returns: HTTP/2 200 OK
   ```
2. **Verify Frontend**:
   Open `https://yatrasathi.noesisframeworks.com` in your browser.
3. **Verify Scale-to-Zero ($0 cost)**:
   - When no visitors access the site for 5 minutes, Azure Container Apps scales down to **0 active replicas**.
   - Inspect replica count in Azure Portal: **Container App** $\to$ **Replicas** shows `0`.
   - When a visitor visits, Azure automatically wakes up a replica in ~2.5 seconds.

