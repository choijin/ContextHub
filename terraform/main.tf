locals {
  runtime_service_account = "contexthub-runtime@${var.project_id}.iam.gserviceaccount.com"
  huggingface_secret      = "projects/${var.project_number}/secrets/contexthub-huggingface-api-token"
}

resource "google_cloud_run_v2_service" "contexthub" {
  name                = var.service_name
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  iap_enabled         = true
  deletion_protection = true

  template {
    service_account                  = local.runtime_service_account
    timeout                          = "3600s"
    max_instance_request_concurrency = 10
    execution_environment            = "EXECUTION_ENVIRONMENT_GEN2"
    session_affinity                 = false

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    containers {
      name       = "frontend"
      image      = var.image_url
      command    = ["streamlit"]
      depends_on = ["api"]
      args = [
        "run",
        "frontend/streamlit_app.py",
        "--server.address",
        "0.0.0.0",
        "--server.port",
        "8080",
        "--server.headless",
        "true",
      ]

      env {
        name  = "CONTEXTHUB_API_BASE_URL"
        value = "http://api:8000"
      }

      ports {
        name           = "http1"
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      startup_probe {
        initial_delay_seconds = 0
        timeout_seconds       = 5
        period_seconds        = 5
        failure_threshold     = 12

        http_get {
          path = "/_stcore/health"
          port = 8080
        }
      }
    }

    containers {
      name    = "api"
      image   = var.image_url
      command = ["uvicorn"]
      args = [
        "contexthub.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
      ]

      env {
        name  = "CONTEXTHUB_ENVIRONMENT"
        value = "cloud-run"
      }

      env {
        name  = "CONTEXTHUB_ALLOW_START_WITHOUT_INDEX"
        value = "false"
      }

      env {
        name  = "CONTEXTHUB_HUGGINGFACE_MODEL"
        value = var.huggingface_model
      }

      env {
        name = "CONTEXTHUB_HUGGINGFACE_API_TOKEN"

        value_source {
          secret_key_ref {
            secret  = local.huggingface_secret
            version = "1"
          }
        }
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      startup_probe {
        initial_delay_seconds = 0
        timeout_seconds       = 5
        period_seconds        = 10
        failure_threshold     = 30

        http_get {
          path = "/ready"
          port = 8000
        }
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

import {
  to = google_cloud_run_v2_service.contexthub
  id = "projects/${var.project_id}/locations/${var.region}/services/${var.service_name}"
}
