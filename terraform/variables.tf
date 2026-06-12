variable "aws_region" {
  type        = string
  description = "AWS region to deploy resources"
  default     = "us-east-1"
}

variable "project_name" {
  type        = string
  description = "Project name prefix for resources"
  default     = "ai-txn-pipeline"
}

variable "environment" {
  type        = string
  description = "Target deployment environment (staging/production)"
  default     = "production"
}

variable "db_password" {
  type        = string
  description = "Master password for the Aurora PostgreSQL database"
  sensitive   = true
}

variable "ecr_repository_url" {
  type        = string
  description = "URL of the Amazon ECR repository housing the application Docker image"
}

# ECS API Sizing
variable "api_cpu" {
  type        = string
  description = "CPU allocated to the FastAPI task (e.g. 256, 512, 1024)"
  default     = "512"
}

variable "api_memory" {
  type        = string
  description = "Memory allocated to the FastAPI task (e.g. 512, 1024, 2048)"
  default     = "1024"
}

# ECS Workers Sizing
variable "worker_cpu" {
  type        = string
  description = "CPU allocated to Celery worker tasks"
  default     = "512"
}

variable "worker_memory" {
  type        = string
  description = "Memory allocated to Celery worker tasks"
  default     = "1024"
}

# Worker queues mapping
variable "worker_queues" {
  type    = list(string)
  default = ["processing", "llm", "reporting"]
}

variable "worker_cmds" {
  type    = list(string)
  default = ["processing_worker", "llm_worker", "reporting_worker"]
}

variable "storage_provider" {
  type        = string
  description = "The storage provider to use (local or s3)"
  default     = "s3"
}
