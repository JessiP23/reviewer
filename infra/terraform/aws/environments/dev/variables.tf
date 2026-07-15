variable "project_name" {
  type        = string
  description = "Short name used in AWS resources."
  default     = "reviewer"
}

variable "environment" {
  type        = string
  description = "Deployment environment."
  default     = "dev"
}

variable "aws_region" {
  type        = string
  description = "AWS region for regional resources."
  default     = "us-east-2"
}

variable "enable_database" {
  type        = bool
  description = "Create billable Aurora Serverless v2 resources."
  default     = false
}

variable "deploy_compute" {
  type        = bool
  description = "Deploy Lambda functions after an image has been pushed to ECR."
  default     = false
}

variable "lambda_image_uri" {
  type        = string
  description = "Immutable ECR image URI including its sha256 digest."
  default     = ""
}

variable "aurora_engine_version" {
  type        = string
  description = "Aurora PostgreSQL version supporting Serverless v2 auto-pause."
  default     = "16.4"
}

variable "database_name" {
  type        = string
  description = "PostgreSQL database name."
  default     = "reviewer"
}

variable "max_upload_bytes" {
  type        = number
  description = "API upload limit; kept below Lambda's synchronous payload ceiling."
  default     = 4000000
}

variable "document_retention_days" {
  type        = number
  description = "Delete source documents after this many days."
  default     = 7
}

variable "protect_database" {
  type        = bool
  description = "Enable deletion protection and final snapshots outside disposable dev."
  default     = false
}

