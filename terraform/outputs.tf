output "alb_dns_name" {
  value       = module.ecs.alb_dns_name
  description = "The public DNS name of the Application Load Balancer"
}

output "aurora_endpoint" {
  value       = module.database.aurora_endpoint
  description = "The connection endpoint for the Aurora Serverless DB cluster"
}

output "redis_endpoint" {
  value       = module.database.redis_endpoint
  description = "The connection address of the Serverless Redis cache"
}

output "secrets_manager_arn" {
  value       = module.iam.secrets_manager_arn
  description = "The ARN of the secrets manager storing the GEMINI_API_KEY"
}
