terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
  }
}

provider "azurerm" {
  features {}
}

# ── 1. RESOURCE GROUP ──────────────────────────────────────────────────────────
resource "azurerm_resource_group" "rg" {
  name     = "rg-${var.app_name}-${var.environment}"
  location = var.azure_region

  tags = {
    Project     = "YatraSathi"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Tier        = "Serverless-Consumption"
  }
}

# ── 2. LOG ANALYTICS WORKSPACE (MONITORING & METRICS) ─────────────────────────
resource "azurerm_log_analytics_workspace" "logs" {
  name                = "log-${var.app_name}-${var.environment}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = azurerm_resource_group.rg.tags
}

# ── 3. AZURE CONTAINER APPS ENVIRONMENT (SERVERLESS CONSUMPTION TIER) ─────────
# Uses serverless Consumption pricing: $0 baseline when idle
resource "azurerm_container_app_environment" "cae" {
  name                       = "cae-${var.app_name}-${var.environment}"
  location                   = azurerm_resource_group.rg.location
  resource_group_name        = azurerm_resource_group.rg.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.logs.id

  tags = azurerm_resource_group.rg.tags
}

# ── 4. AZURE CONTAINER APP (PULLING FROM FREE GITHUB CONTAINER REGISTRY) ───────
resource "azurerm_container_app" "backend" {
  name                         = "ca-${var.app_name}-api-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.cae.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"

  # GitHub Container Registry (ghcr.io) integration
  # If a GitHub PAT is provided (for private packages), register authentication;
  # If the package is Public on GitHub, no registry block is needed.
  dynamic "registry" {
    for_each = var.github_pat != "" ? [1] : []
    content {
      server               = "ghcr.io"
      username             = var.github_username
      password_secret_name = "ghcr-pat"
    }
  }

  dynamic "secret" {
    for_each = var.github_pat != "" ? [1] : []
    content {
      name  = "ghcr-pat"
      value = var.github_pat
    }
  }

  # Encrypted secrets injection for Supabase DB & Groq API
  secret {
    name  = "database-url"
    value = var.supabase_database_url
  }

  secret {
    name  = "groq-api-key"
    value = var.groq_api_key
  }

  secret {
    name  = "jwt-secret-key"
    value = var.jwt_secret_key
  }

  template {
    # CRITICAL FOR AZURE STUDENT / $0 BUDGET:
    # min_replicas = 0 spins down container completely when idle
    min_replicas = 0
    max_replicas = 3

    container {
      name   = "yatrasathi-api"
      image  = "ghcr.io/${lower(var.github_username)}/yatrasathi-backend:latest"
      # 0.5 vCPU / 1 GiB minimum: the image loads torch + the embedding model.
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "PORT"
        value = "8000"
      }

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }

      env {
        name  = "PUBLIC_BASE_URL"
        value = var.api_public_url
      }

      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }

      env {
        name        = "GROQ_API_KEY"
        secret_name = "groq-api-key"
      }

      env {
        name        = "JWT_SECRET_KEY"
        secret_name = "jwt-secret-key"
      }

      env {
        name  = "AI_ENABLED"
        value = "true"
      }

      env {
        name  = "DEBUG"
        value = "false"
      }

      env {
        name  = "CORS_ORIGINS"
        value = "https://${var.custom_domain},https://yatrasathi.noesisframeworks.com,https://noesisframeworks.com"
      }
    }
  }

  ingress {
    allow_insecure_connections = false
    external_enabled           = true
    target_port                = 8000

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  tags = azurerm_resource_group.rg.tags

  # CI deploys immutable :<sha> images; don't let `terraform apply` revert them to :latest.
  lifecycle {
    ignore_changes = [template[0].container[0].image]
  }

  depends_on = [
    azurerm_container_app_environment.cae
  ]
}
