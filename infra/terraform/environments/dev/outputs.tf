output "artifact_registry_repository" {
  value = google_artifact_registry_repository.containers.name
}

output "api_url" {
  value = var.deploy_services ? google_cloud_run_v2_service.api[0].uri : null
}

output "web_url" {
  value = var.deploy_services ? google_cloud_run_v2_service.web[0].uri : null
}

