# ==========================================
# ROOT MODULE ORCHESTRATION
# ==========================================

module "vpc" {
  source       = "./modules/vpc"
  project_name = var.project_name
  environment  = var.environment
}

module "security_groups" {
  source       = "./modules/security_groups"
  vpc_id       = module.vpc.vpc_id
  project_name = var.project_name
  environment  = var.environment
}

module "s3" {
  source       = "./modules/s3"
  project_name = var.project_name
  environment  = var.environment
}

module "iam" {
  source         = "./modules/iam"
  project_name   = var.project_name
  environment    = var.environment
  s3_bucket_arn  = module.s3.bucket_arn
  s3_bucket_name = module.s3.bucket_name
}

module "database" {
  source                  = "./modules/database"
  project_name            = var.project_name
  environment             = var.environment
  db_subnet_ids           = module.vpc.database_subnet_ids
  db_security_group_id    = module.security_groups.db_sg_id
  redis_security_group_id = module.security_groups.redis_sg_id
  db_password             = var.db_password
}

module "ecs" {
  source                 = "./modules/ecs"
  project_name           = var.project_name
  environment            = var.environment
  vpc_id                 = module.vpc.vpc_id
  public_subnet_ids      = module.vpc.public_subnet_ids
  private_subnet_ids     = module.vpc.private_subnet_ids
  alb_sg_id              = module.security_groups.alb_sg_id
  ecs_tasks_sg_id        = module.security_groups.ecs_tasks_sg_id
  ecs_execution_role_arn = module.iam.ecs_execution_role_arn
  ecs_task_role_arn      = module.iam.ecs_task_role_arn
  secrets_manager_arn    = module.iam.secrets_manager_arn
  db_password            = var.db_password
  aurora_endpoint        = module.database.aurora_endpoint
  redis_endpoint         = module.database.redis_endpoint
  redis_port             = module.database.redis_port
  ecr_repository_url     = var.ecr_repository_url
  aws_region             = var.aws_region
  api_cpu                = var.api_cpu
  api_memory             = var.api_memory
  worker_cpu             = var.worker_cpu
  worker_memory          = var.worker_memory
  worker_queues          = var.worker_queues
  worker_cmds            = var.worker_cmds
  s3_bucket_name         = module.s3.bucket_name
  storage_provider       = var.storage_provider
}
