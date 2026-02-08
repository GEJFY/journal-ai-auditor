# =============================================================================
# JAIA GCP Infrastructure
# =============================================================================
# Vertex AI (Gemini 3.0) を使用した監査AIシステム
#
# 使用方法:
#   cd infrastructure/terraform/gcp
#   gcloud auth application-default login
#   terraform init
#   terraform plan
#   terraform apply
# =============================================================================

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.10"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.10"
    }
  }

  # リモートステート設定（本番環境用）
  # backend "gcs" {
  #   bucket = "jaia-terraform-state"
  #   prefix = "gcp/terraform.tfstate"
  # }
}

# =============================================================================
# Variables
# =============================================================================

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "asia-northeast1"
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

variable "gemini_model" {
  description = "Vertex AI Gemini model"
  type        = string
  default     = "gemini-3.0-flash-preview"
}

# =============================================================================
# Provider Configuration
# =============================================================================

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# =============================================================================
# Enable Required APIs
# =============================================================================

resource "google_project_service" "services" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "aiplatform.googleapis.com",
    "secretmanager.googleapis.com",
    "compute.googleapis.com",
    "vpcaccess.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
  ])

  service            = each.key
  disable_on_destroy = false
}

# =============================================================================
# VPC Network
# =============================================================================

resource "google_compute_network" "main" {
  name                    = "${var.app_name}-${var.environment}-vpc"
  auto_create_subnetworks = false

  depends_on = [google_project_service.services]
}

resource "google_compute_subnetwork" "main" {
  name          = "${var.app_name}-${var.environment}-subnet"
  ip_cidr_range = "10.0.0.0/24"
  network       = google_compute_network.main.id
  region        = var.region

  private_ip_google_access = true

  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# VPC Access Connector for Cloud Run
resource "google_vpc_access_connector" "main" {
  name          = "${var.app_name}-${var.environment}-connector"
  region        = var.region
  ip_cidr_range = "10.8.0.0/28"
  network       = google_compute_network.main.name

  depends_on = [google_project_service.services]
}

# =============================================================================
# Artifact Registry
# =============================================================================

resource "google_artifact_registry_repository" "main" {
  location      = var.region
  repository_id = "${var.app_name}-${var.environment}"
  format        = "DOCKER"
  description   = "JAIA container images"

  labels = {
    environment = var.environment
  }

  depends_on = [google_project_service.services]
}

# =============================================================================
# Cloud Storage
# =============================================================================

resource "google_storage_bucket" "data" {
  name          = "${var.project_id}-${var.app_name}-${var.environment}-data"
  location      = var.region
  force_destroy = var.environment != "production"

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type = "Delete"
    }
  }

  labels = {
    environment = var.environment
    application = var.app_name
  }
}

resource "google_storage_bucket" "reports" {
  name          = "${var.project_id}-${var.app_name}-${var.environment}-reports"
  location      = var.region
  force_destroy = var.environment != "production"

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  labels = {
    environment = var.environment
    application = var.app_name
  }
}

# =============================================================================
# Secret Manager
# =============================================================================

resource "google_secret_manager_secret" "anthropic_api_key" {
  secret_id = "${var.app_name}-${var.environment}-anthropic-api-key"

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
  }

  depends_on = [google_project_service.services]
}

resource "google_secret_manager_secret" "openai_api_key" {
  secret_id = "${var.app_name}-${var.environment}-openai-api-key"

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
  }

  depends_on = [google_project_service.services]
}

resource "google_secret_manager_secret" "google_api_key" {
  secret_id = "${var.app_name}-${var.environment}-google-api-key"

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
  }

  depends_on = [google_project_service.services]
}

# =============================================================================
# Service Account
# =============================================================================

resource "google_service_account" "cloud_run" {
  account_id   = "${var.app_name}-${var.environment}-run"
  display_name = "JAIA Cloud Run Service Account"
}

# Vertex AI アクセス権限
resource "google_project_iam_member" "vertex_ai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

# Storage アクセス権限
resource "google_project_iam_member" "storage_admin" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

# Secret Manager アクセス権限
resource "google_project_iam_member" "secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

# =============================================================================
# Cloud Run Service
# =============================================================================

resource "google_cloud_run_v2_service" "backend" {
  name     = "${var.app_name}-backend"
  location = var.region

  template {
    service_account = google_service_account.cloud_run.email

    scaling {
      min_instance_count = var.environment == "production" ? 2 : 0
      max_instance_count = var.environment == "production" ? 10 : 3
    }

    vpc_access {
      connector = google_vpc_access_connector.main.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.main.repository_id}/${var.app_name}-backend:latest"

      ports {
        container_port = 8001
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      env {
        name  = "LLM_PROVIDER"
        value = "vertex_ai"
      }

      env {
        name  = "LLM_MODEL"
        value = var.gemini_model
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }

      env {
        name  = "GCP_LOCATION"
        value = var.region
      }

      env {
        name = "GOOGLE_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.google_api_key.secret_id
            version = "latest"
          }
        }
      }

      startup_probe {
        http_get {
          path = "/api/v1/health"
          port = 8001
        }
        initial_delay_seconds = 10
        timeout_seconds       = 5
        period_seconds        = 10
        failure_threshold     = 3
      }

      liveness_probe {
        http_get {
          path = "/api/v1/health"
          port = 8001
        }
        period_seconds    = 30
        timeout_seconds   = 5
        failure_threshold = 3
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  labels = {
    environment = var.environment
    application = var.app_name
  }

  depends_on = [
    google_project_service.services,
    google_artifact_registry_repository.main,
  ]
}

# Cloud Run の公開アクセス設定（development/stagingのみ）
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  count = var.environment != "production" ? 1 : 0

  location = var.region
  name     = google_cloud_run_v2_service.backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# =============================================================================
# Cloud Armor (WAF) - 本番環境用
# =============================================================================

resource "google_compute_security_policy" "waf" {
  count = var.environment == "production" ? 1 : 0

  name = "${var.app_name}-${var.environment}-waf"

  # SQL Injection 対策
  rule {
    action   = "deny(403)"
    priority = 1000
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('sqli-stable')"
      }
    }
    description = "Block SQL injection attacks"
  }

  # XSS 対策
  rule {
    action   = "deny(403)"
    priority = 1001
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('xss-stable')"
      }
    }
    description = "Block XSS attacks"
  }

  # レート制限
  rule {
    action   = "throttle"
    priority = 2000
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      rate_limit_threshold {
        count        = 100
        interval_sec = 60
      }
    }
    description = "Rate limiting"
  }

  # デフォルト許可
  rule {
    action   = "allow"
    priority = 2147483647
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default allow rule"
  }
}

# =============================================================================
# Outputs
# =============================================================================

output "cloud_run_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_v2_service.backend.uri
}

output "artifact_registry_url" {
  description = "Artifact Registry URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.main.repository_id}"
}

output "data_bucket_name" {
  description = "Data storage bucket name"
  value       = google_storage_bucket.data.name
}

output "reports_bucket_name" {
  description = "Reports storage bucket name"
  value       = google_storage_bucket.reports.name
}

output "service_account_email" {
  description = "Cloud Run service account email"
  value       = google_service_account.cloud_run.email
}
