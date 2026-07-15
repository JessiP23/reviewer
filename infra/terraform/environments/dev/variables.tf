variable "project_id" {
  description = "Google Cloud project ID."
  type        = string
}

variable "region" {
  description = "Primary deployment region."
  type        = string
  default     = "us-east1"
}

variable "environment" {
  description = "Environment suffix used in resource names."
  type        = string
  default     = "dev"
}

variable "deploy_services" {
  description = "Create Cloud Run services after images have been pushed."
  type        = bool
  default     = false
}

variable "api_image" {
  description = "Immutable reviewer API image URI."
  type        = string
  default     = ""
}

variable "web_image" {
  description = "Immutable web image URI."
  type        = string
  default     = ""
}

variable "allow_public_access" {
  description = "Demo only. Production should use authenticated ingress."
  type        = bool
  default     = false
}

