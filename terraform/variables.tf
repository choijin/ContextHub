variable "project_id" {
  description = "Google Cloud project that hosts ContextHub."
  type        = string
  default     = "contexthub-rag-app"
}

variable "region" {
  description = "Google Cloud region for the Cloud Run service."
  type        = string
  default     = "us-central1"
}

variable "project_number" {
  description = "Numeric Google Cloud project identifier used by Secret Manager."
  type        = string
  default     = "825051407585"
}

variable "service_name" {
  description = "Cloud Run service name."
  type        = string
  default     = "contexthub"
}

variable "image_url" {
  description = "Immutable Artifact Registry image URL deployed to both containers."
  type        = string
}

variable "huggingface_model" {
  description = "Hugging Face inference model used by the API container."
  type        = string
  default     = "openai/gpt-oss-20b:fastest"
}
