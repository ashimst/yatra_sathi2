output "resource_group_name" {
  description = "The name of the Azure Resource Group"
  value       = azurerm_resource_group.rg.name
}

output "container_app_name" {
  description = "Azure Container App instance identifier"
  value       = azurerm_container_app.backend.name
}

output "container_app_fqdn" {
  description = "Default public HTTPS URL of the Azure Container App"
  value       = azurerm_container_app.backend.latest_revision_fqdn
}

output "ghcr_image_source" {
  description = "Container image source hosted on GitHub Container Registry"
  value       = "ghcr.io/${lower(var.github_username)}/yatrasathi-backend:latest"
}

output "api_dns_cname_target" {
  description = "CNAME target record for api.yatrasathi.noesisframeworks.com"
  value       = azurerm_container_app.backend.latest_revision_fqdn
}

output "custom_domain_verification_id" {
  description = "Custom domain verification code for DNS TXT record (asuid.<subdomain>)"
  value       = azurerm_container_app_environment.cae.custom_domain_verification_id
}
