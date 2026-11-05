variable "app_name" {
  type        = string
  description = "Application identifier prefix used in resource naming"
  default     = "yatrasathi"
}

variable "environment" {
  type        = string
  description = "Deployment environment name (e.g., prod, staging, demo)"
  default     = "prod"
}

variable "azure_region" {
  type        = string
  description = "Target Azure datacenter region (e.g. southeastasia, eastus, westeurope)"
  default     = "southeastasia"
}

variable "github_username" {
  type        = string
  description = "GitHub username or organization owning the ghcr.io package (e.g. ashimst)"
}

variable "github_pat" {
  type        = string
  description = "Optional GitHub Personal Access Token with read:packages scope (leave empty if the ghcr.io package is public)"
  default     = ""
  sensitive   = true
}

variable "supabase_database_url" {
  type        = string
  description = "Full connection string to Supabase PostgreSQL (with PostGIS and pgvector enabled)"
  sensitive   = true
}

variable "groq_api_key" {
  type        = string
  description = "Groq Cloud API key for System 2 ReAct itinerary synthesis"
  sensitive   = true
}

variable "jwt_secret_key" {
  type        = string
  description = "Cryptographic secret for traveler JWT authentication tokens"
  sensitive   = true
}

variable "custom_domain" {
  type        = string
  description = "Primary company frontend domain"
  default     = "yatrasathi.noesisframeworks.com"
}

variable "api_subdomain" {
  type        = string
  description = "API endpoint subdomain"
  default     = "api.yatrasathi.noesisframeworks.com"
}
