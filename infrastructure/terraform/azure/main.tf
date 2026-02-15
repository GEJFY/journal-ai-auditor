# =============================================================================
# JAIA Azure Infrastructure
# =============================================================================
# Azure AI Foundry (GPT-5.2) を使用した監査AIシステム
#
# 使用方法:
#   cd infrastructure/terraform/azure
#   az login
#   terraform init
#   terraform plan
#   terraform apply
# =============================================================================

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
  }

  # リモートステート設定（本番環境用）
  # backend "azurerm" {
  #   resource_group_name  = "jaia-terraform-rg"
  #   storage_account_name = "jaiatfstate"
  #   container_name       = "tfstate"
  #   key                  = "azure/terraform.tfstate"
  # }
}

# =============================================================================
# Provider Configuration
# =============================================================================

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
    key_vault {
      purge_soft_delete_on_destroy = true
    }
  }
}

# =============================================================================
# Variables
# =============================================================================

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "japaneast"
}

variable "environment" {
  description = "Environment name (development, staging, production)"
  type        = string
  default     = "development"

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be development, staging, or production."
  }
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "jaia"
}

variable "openai_model" {
  description = "Azure OpenAI model deployment name"
  type        = string
  default     = "gpt-5-2"
}

# =============================================================================
# Resource Group
# =============================================================================

resource "azurerm_resource_group" "main" {
  name     = "rg-${var.app_name}-${var.environment}"
  location = var.location

  tags = {
    Application = "JAIA"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# =============================================================================
# Virtual Network
# =============================================================================

resource "azurerm_virtual_network" "main" {
  name                = "vnet-${var.app_name}-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  address_space       = ["10.0.0.0/16"]

  tags = azurerm_resource_group.main.tags
}

resource "azurerm_subnet" "app" {
  name                 = "snet-app"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.1.0/24"]

  delegation {
    name = "containerapp-delegation"
    service_delegation {
      name    = "Microsoft.App/environments"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

resource "azurerm_subnet" "private" {
  name                 = "snet-private"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.2.0/24"]

  service_endpoints = ["Microsoft.Storage", "Microsoft.KeyVault", "Microsoft.CognitiveServices"]
}

# =============================================================================
# Azure AI Foundry Service
# =============================================================================

resource "azurerm_cognitive_account" "openai" {
  name                = "aoai-${var.app_name}-${var.environment}"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  kind                = "OpenAI"
  sku_name            = "S0"

  custom_subdomain_name = "aoai-${var.app_name}-${var.environment}"

  network_acls {
    default_action = var.environment == "production" ? "Deny" : "Allow"
    ip_rules       = []
    virtual_network_rules {
      subnet_id = azurerm_subnet.private.id
    }
  }

  tags = azurerm_resource_group.main.tags
}

# GPT-5.2 デプロイメント（Azure AI Foundry）
resource "azurerm_cognitive_deployment" "gpt5" {
  name                 = "gpt-5-2-deployment"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "gpt-5.2-chat"
    version = "2025-12-11"
  }

  scale {
    type     = "GlobalStandard"
    capacity = 10
  }
}

# =============================================================================
# Container App Environment
# =============================================================================

resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-${var.app_name}-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 90

  tags = azurerm_resource_group.main.tags
}

resource "azurerm_container_app_environment" "main" {
  name                       = "cae-${var.app_name}-${var.environment}"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  infrastructure_subnet_id = azurerm_subnet.app.id

  tags = azurerm_resource_group.main.tags
}

# =============================================================================
# Container Registry
# =============================================================================

resource "azurerm_container_registry" "main" {
  name                = "acr${var.app_name}${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = var.environment == "production" ? "Premium" : "Basic"
  admin_enabled       = true

  tags = azurerm_resource_group.main.tags
}

# =============================================================================
# Key Vault
# =============================================================================

data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "main" {
  name                        = "kv-${var.app_name}-${var.environment}"
  location                    = azurerm_resource_group.main.location
  resource_group_name         = azurerm_resource_group.main.name
  enabled_for_disk_encryption = true
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  soft_delete_retention_days  = 7
  purge_protection_enabled    = var.environment == "production"

  sku_name = "standard"

  network_acls {
    default_action = var.environment == "production" ? "Deny" : "Allow"
    bypass         = "AzureServices"
  }

  tags = azurerm_resource_group.main.tags
}

resource "azurerm_key_vault_access_policy" "admin" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  secret_permissions = [
    "Get", "List", "Set", "Delete", "Purge"
  ]
}

# =============================================================================
# Storage Account
# =============================================================================

resource "azurerm_storage_account" "main" {
  name                     = "st${var.app_name}${var.environment}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = var.environment == "production" ? "GRS" : "LRS"

  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = 30
    }
  }

  network_rules {
    default_action             = var.environment == "production" ? "Deny" : "Allow"
    virtual_network_subnet_ids = [azurerm_subnet.private.id]
    bypass                     = ["AzureServices"]
  }

  tags = azurerm_resource_group.main.tags
}

resource "azurerm_storage_container" "data" {
  name                  = "jaia-data"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "reports" {
  name                  = "jaia-reports"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

# =============================================================================
# Container App
# =============================================================================

resource "azurerm_container_app" "backend" {
  name                         = "ca-${var.app_name}-backend"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  template {
    container {
      name   = "backend"
      image  = "${azurerm_container_registry.main.login_server}/${var.app_name}-backend:latest"
      cpu    = 1.0
      memory = "2Gi"

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      env {
        name  = "LLM_PROVIDER"
        value = "azure_foundry"
      }

      env {
        name  = "LLM_MODEL"
        value = "gpt-5.2"
      }

      env {
        name  = "AZURE_FOUNDRY_ENDPOINT"
        value = azurerm_cognitive_account.openai.endpoint
      }

      env {
        name        = "AZURE_FOUNDRY_API_KEY"
        secret_name = "azure-openai-key"
      }

      liveness_probe {
        transport = "HTTP"
        path      = "/api/v1/health"
        port      = 8001
      }

      readiness_probe {
        transport = "HTTP"
        path      = "/api/v1/health"
        port      = 8001
      }
    }

    min_replicas = var.environment == "production" ? 2 : 1
    max_replicas = var.environment == "production" ? 10 : 3
  }

  secret {
    name  = "azure-openai-key"
    value = azurerm_cognitive_account.openai.primary_access_key
  }

  ingress {
    external_enabled = true
    target_port      = 8001
    transport        = "http"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  registry {
    server               = azurerm_container_registry.main.login_server
    username             = azurerm_container_registry.main.admin_username
    password_secret_name = "acr-password"
  }

  secret {
    name  = "acr-password"
    value = azurerm_container_registry.main.admin_password
  }

  tags = azurerm_resource_group.main.tags

  depends_on = [azurerm_cognitive_deployment.gpt5]
}

# =============================================================================
# Outputs
# =============================================================================

output "resource_group_name" {
  description = "Resource group name"
  value       = azurerm_resource_group.main.name
}

output "container_registry_url" {
  description = "Container registry URL"
  value       = azurerm_container_registry.main.login_server
}

output "container_app_url" {
  description = "Container App URL"
  value       = "https://${azurerm_container_app.backend.ingress[0].fqdn}"
}

output "openai_endpoint" {
  description = "Azure AI Foundry endpoint"
  value       = azurerm_cognitive_account.openai.endpoint
}

output "key_vault_uri" {
  description = "Key Vault URI"
  value       = azurerm_key_vault.main.vault_uri
}

output "storage_account_name" {
  description = "Storage account name"
  value       = azurerm_storage_account.main.name
}
