# Odoo GCP Infrastructure
# Terraform configuration for running Odoo on Cloud Run with Cloud SQL

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "asia-northeast1"
}

variable "odoo_db_password" {
  description = "PostgreSQL password for Odoo"
  type        = string
  sensitive   = true
}

variable "odoo_admin_password" {
  description = "Odoo admin master password"
  type        = string
  sensitive   = true
}

# GitHub repository for WIF
variable "github_repo" {
  description = "GitHub repository (org/repo format)"
  type        = string
  default     = "emt-jp/odoo"
}

# Enable required APIs
resource "google_project_service" "services" {
  for_each = toset([
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "vpcaccess.googleapis.com",
    "servicenetworking.googleapis.com",
    "artifactregistry.googleapis.com",
    "iamcredentials.googleapis.com",
    "iam.googleapis.com",
  ])
  project = var.project_id
  service = each.value
}

# Artifact Registry for Docker images
resource "google_artifact_registry_repository" "odoo" {
  location      = var.region
  repository_id = "odoo"
  description   = "Odoo Docker images"
  format        = "DOCKER"
  project       = var.project_id

  depends_on = [google_project_service.services]
}

# Workload Identity Federation for GitHub Actions
resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github-pool"
  project                   = var.project_id
  display_name              = "GitHub Actions Pool"
  description               = "Identity pool for GitHub Actions"

  depends_on = [google_project_service.services]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  project                            = var.project_id
  display_name                       = "GitHub Provider"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
  }

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }

  attribute_condition = "assertion.repository == '${var.github_repo}'"
}

# Service account for GitHub Actions deployments
resource "google_service_account" "github_actions" {
  account_id   = "github-actions-sa"
  display_name = "GitHub Actions Service Account"
  project      = var.project_id
}

# Allow GitHub Actions to impersonate the service account
resource "google_service_account_iam_member" "github_actions_wif" {
  service_account_id = google_service_account.github_actions.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repo}"
}

# IAM roles for GitHub Actions service account
resource "google_project_iam_member" "github_actions_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_project_iam_member" "github_actions_artifact_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_project_iam_member" "github_actions_sa_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

# VPC for private Cloud SQL
resource "google_compute_network" "odoo_vpc" {
  name                    = "odoo-vpc"
  project                 = var.project_id
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "odoo_subnet" {
  name          = "odoo-subnet"
  project       = var.project_id
  region        = var.region
  network       = google_compute_network.odoo_vpc.id
  ip_cidr_range = "10.0.0.0/24"
}

# Private IP for Cloud SQL
resource "google_compute_global_address" "private_ip" {
  name          = "odoo-sql-private-ip"
  project       = var.project_id
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.odoo_vpc.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.odoo_vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip.name]
}

# Cloud SQL PostgreSQL
resource "google_sql_database_instance" "odoo" {
  name             = "odoo-db"
  project          = var.project_id
  region           = var.region
  database_version = "POSTGRES_15"

  depends_on = [google_service_networking_connection.private_vpc_connection]

  settings {
    tier              = "db-custom-2-4096"
    availability_type = "ZONAL"
    disk_size         = 20
    disk_type         = "PD_SSD"

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.odoo_vpc.id
    }

    backup_configuration {
      enabled            = true
      start_time         = "03:00"
      binary_log_enabled = false
      location           = var.region
    }

    maintenance_window {
      day          = 7
      hour         = 3
      update_track = "stable"
    }
  }

  deletion_protection = true
}

resource "google_sql_database" "odoo" {
  name     = "odoo"
  project  = var.project_id
  instance = google_sql_database_instance.odoo.name
}

resource "google_sql_user" "odoo" {
  name     = "odoo"
  project  = var.project_id
  instance = google_sql_database_instance.odoo.name
  password = var.odoo_db_password
}

# Serverless VPC Connector
resource "google_vpc_access_connector" "odoo" {
  name           = "odoo-vpc-connector"
  project        = var.project_id
  region         = var.region
  network        = google_compute_network.odoo_vpc.name
  ip_cidr_range  = "10.8.0.0/28"
  max_throughput = 1000
}

# Secret Manager for sensitive config
resource "google_secret_manager_secret" "odoo_admin_password" {
  secret_id = "odoo-admin-password"
  project   = var.project_id

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "odoo_admin_password" {
  secret      = google_secret_manager_secret.odoo_admin_password.id
  secret_data = var.odoo_admin_password
}

resource "google_secret_manager_secret" "odoo_db_password" {
  secret_id = "odoo-db-password"
  project   = var.project_id

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "odoo_db_password" {
  secret      = google_secret_manager_secret.odoo_db_password.id
  secret_data = var.odoo_db_password
}

# GCS bucket for filestore
resource "google_storage_bucket" "odoo_filestore" {
  name     = "${var.project_id}-odoo-filestore"
  project  = var.project_id
  location = var.region

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      num_newer_versions = 3
    }
  }
}

# Service account for Cloud Run
resource "google_service_account" "odoo" {
  account_id   = "odoo-sa"
  display_name = "Odoo Service Account"
  project      = var.project_id
}

resource "google_project_iam_member" "odoo_sql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.odoo.email}"
}

resource "google_project_iam_member" "odoo_secrets" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.odoo.email}"
}

resource "google_storage_bucket_iam_member" "odoo_filestore" {
  bucket = google_storage_bucket.odoo_filestore.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.odoo.email}"
}

# Outputs
output "cloud_sql_instance" {
  value = google_sql_database_instance.odoo.connection_name
}

output "cloud_sql_private_ip" {
  value = google_sql_database_instance.odoo.private_ip_address
}

output "vpc_connector" {
  value = google_vpc_access_connector.odoo.id
}

output "filestore_bucket" {
  value = google_storage_bucket.odoo_filestore.name
}

output "service_account" {
  value = google_service_account.odoo.email
}

# GitHub Actions outputs
output "wif_provider" {
  description = "Workload Identity Provider for GitHub Actions (WIF_PROVIDER secret)"
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "wif_service_account" {
  description = "Service Account for GitHub Actions (WIF_SERVICE_ACCOUNT secret)"
  value       = google_service_account.github_actions.email
}

output "artifact_registry" {
  description = "Artifact Registry URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.odoo.repository_id}"
}
