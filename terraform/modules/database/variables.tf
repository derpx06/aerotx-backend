variable "project_name" {
  type        = string
  description = "Project prefix"
}

variable "environment" {
  type        = string
  description = "Environment name"
}

variable "db_subnet_ids" {
  type        = list(string)
  description = "IDs of subnets for the database group"
}

variable "db_security_group_id" {
  type        = string
  description = "Security Group ID of the database"
}

variable "redis_security_group_id" {
  type        = string
  description = "Security Group ID of Redis"
}

variable "db_password" {
  type        = string
  description = "Master database password"
  sensitive   = true
}
