variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "public_subnet_ids" {
  type = list(string)
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "alb_sg_id" {
  type = string
}

variable "ecs_tasks_sg_id" {
  type = string
}

variable "ecs_execution_role_arn" {
  type = string
}

variable "ecs_task_role_arn" {
  type = string
}

variable "secrets_manager_arn" {
  type = string
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "aurora_endpoint" {
  type = string
}

variable "redis_endpoint" {
  type = string
}

variable "redis_port" {
  type = number
}

variable "ecr_repository_url" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "api_cpu" {
  type = string
}

variable "api_memory" {
  type = string
}

variable "worker_cpu" {
  type = string
}

variable "worker_memory" {
  type = string
}

variable "worker_queues" {
  type    = list(string)
  default = ["processing", "llm", "reporting"]
}

variable "worker_cmds" {
  type    = list(string)
  default = ["processing_worker", "llm_worker", "reporting_worker"]
}

variable "s3_bucket_name" {
  type        = string
  description = "The name of the uploads S3 bucket"
}

variable "storage_provider" {
  type        = string
  description = "The storage provider to use (local or s3)"
  default     = "s3"
}
