variable "vpc_id" {
  type        = string
  description = "The ID of the VPC"
}

variable "project_name" {
  type        = string
  description = "Project prefix for resources"
}

variable "environment" {
  type        = string
  description = "Environment name"
}
