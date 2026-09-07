output "service_uri" {
  description = "Private Cloud Run URL for ContextHub."
  value       = google_cloud_run_v2_service.contexthub.uri
}

output "latest_ready_revision" {
  description = "Latest Cloud Run revision that became ready."
  value       = google_cloud_run_v2_service.contexthub.latest_ready_revision
}
