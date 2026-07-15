locals {
  name = "reviewer-${var.environment}"
  services = toset([
    "artifactregistry.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "sqladmin.googleapis.com",
  ])
}

resource "google_project_service" "required" {
  for_each           = local.services
  service            = each.value
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "containers" {
  location      = var.region
  repository_id = local.name
  description   = "Reviewer Agent container images"
  format        = "DOCKER"
  depends_on    = [google_project_service.required]
}

resource "google_service_account" "api" {
  account_id   = "${local.name}-api"
  display_name = "Reviewer Agent API"
}

resource "google_service_account" "web" {
  account_id   = "${local.name}-web"
  display_name = "Reviewer Agent web"
}

resource "google_cloud_run_v2_service" "api" {
  count    = var.deploy_services ? 1 : 0
  name     = "${local.name}-api"
  location = var.region

  template {
    service_account = google_service_account.api.email
    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }
    containers {
      image = var.api_image
      resources {
        limits = { cpu = "1", memory = "1Gi" }
      }
      env {
        name  = "APP_ENV"
        value = var.environment
      }
      env {
        name  = "MAX_UPLOAD_BYTES"
        value = "10485760"
      }
    }
  }
  depends_on = [google_project_service.required]
}

resource "google_cloud_run_v2_service" "web" {
  count    = var.deploy_services ? 1 : 0
  name     = "${local.name}-web"
  location = var.region

  template {
    service_account = google_service_account.web.email
    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }
    containers {
      image = var.web_image
      resources {
        limits = { cpu = "1", memory = "512Mi" }
      }
    }
  }
  depends_on = [google_project_service.required]
}

resource "google_cloud_run_v2_service_iam_member" "public_api" {
  count    = var.deploy_services && var.allow_public_access ? 1 : 0
  name     = google_cloud_run_v2_service.api[0].name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "public_web" {
  count    = var.deploy_services && var.allow_public_access ? 1 : 0
  name     = google_cloud_run_v2_service.web[0].name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

