resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"
}

resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 30
}

# ALB Config
resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.alb_sg_id]
  subnets            = var.public_subnet_ids
}

resource "aws_lb_target_group" "api" {
  name        = "${var.project_name}-api-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = "/health"
    matcher             = "200"
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

# ECS Task Definitions
resource "aws_ecs_task_definition" "api" {
  family                   = "${var.project_name}-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = var.ecs_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn

  container_definitions = jsonencode([
    {
      name      = "api"
      image     = "${var.ecr_repository_url}:latest"
      essential = true
      command   = ["api"]
      portMappings = [
        { containerPort = 8000 }
      ]
      environment = [
        { name = "DATABASE_URL", value = "postgresql+asyncpg://postgres:${var.db_password}@${var.aurora_endpoint}/transactions" },
        { name = "SYNC_DATABASE_URL", value = "postgresql+psycopg://postgres:${var.db_password}@${var.aurora_endpoint}/transactions" },
        { name = "REDIS_URL", value = "redis://${var.redis_endpoint}:${var.redis_port}/0" },
        { name = "UPLOAD_DIR", value = "/data/uploads" },
        { name = "STORAGE_PROVIDER", value = var.storage_provider },
        { name = "S3_BUCKET_NAME", value = var.s3_bucket_name },
        { name = "ENVIRONMENT", value = var.environment }
      ]
      secrets = [
        { name = "GEMINI_API_KEY", valueFrom = "${var.secrets_manager_arn}:GEMINI_API_KEY::" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "api"
        }
      }
    }
  ])
}

# ECS API Service
resource "aws_ecs_service" "api" {
  name            = "${var.project_name}-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_tasks_sg_id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.http]
}

# Workers Task Definition Helper
resource "aws_ecs_task_definition" "worker" {
  count                    = 3
  family                   = "${var.project_name}-worker-${var.worker_queues[count.index]}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.worker_cpu
  memory                   = var.worker_memory
  execution_role_arn       = var.ecs_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn

  container_definitions = jsonencode([
    {
      name      = "worker"
      image     = "${var.ecr_repository_url}:latest"
      essential = true
      command   = [var.worker_cmds[count.index]]
      environment = [
        { name = "DATABASE_URL", value = "postgresql+asyncpg://postgres:${var.db_password}@${var.aurora_endpoint}/transactions" },
        { name = "SYNC_DATABASE_URL", value = "postgresql+psycopg://postgres:${var.db_password}@${var.aurora_endpoint}/transactions" },
        { name = "REDIS_URL", value = "redis://${var.redis_endpoint}:${var.redis_port}/0" },
        { name = "UPLOAD_DIR", value = "/data/uploads" },
        { name = "STORAGE_PROVIDER", value = var.storage_provider },
        { name = "S3_BUCKET_NAME", value = var.s3_bucket_name },
        { name = "SKIP_MIGRATIONS", value = "1" },
        { name = "ENVIRONMENT", value = var.environment }
      ]
      secrets = [
        { name = "GEMINI_API_KEY", valueFrom = "${var.secrets_manager_arn}:GEMINI_API_KEY::" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "worker-${var.worker_queues[count.index]}"
        }
      }
    }
  ])
}

# ECS Worker Services
resource "aws_ecs_service" "worker" {
  count           = 3
  name            = "${var.project_name}-worker-${var.worker_queues[count.index]}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.worker[count.index].arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_tasks_sg_id]
    assign_public_ip = true
  }
}
