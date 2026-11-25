# =============================================================================
# ECS Cluster, Task Definition, and Fargate Service
# =============================================================================

# 1. ECS Cluster with Container Insights
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "${var.project_name}-cluster"
  }
}

# 2. CloudWatch Log Group for Application Container
resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 14

  tags = {
    Name = "${var.project_name}-ecs-logs"
  }
}

# 3. ECS Task Definition (Fargate)
resource "aws_ecs_task_definition" "app" {
  family                   = var.project_name
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.fargate_cpu
  memory                   = var.fargate_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = var.project_name
      image     = "${aws_ecr_repository.app.repository_url}:${var.image_tag}"
      essential = true

      portMappings = [
        {
          containerPort = var.container_port
          hostPort      = var.container_port
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "DB_HOST", value = aws_db_instance.mariadb.address },
        { name = "DB_PORT", value = tostring(aws_db_instance.mariadb.port) },
        { name = "DB_NAME", value = var.db_name },
        { name = "DB_USER", value = var.db_username },
        { name = "REDIS_CACHE_URL", value = "redis://${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379" },
        { name = "REDIS_QUEUE_URL", value = "redis://${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379" },
        { name = "REDIS_SOCKETIO_URL", value = "redis://${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379" },
        { name = "SITE_NAME", value = var.site_name },
        { name = "AUTO_MIGRATE", value = "1" }
      ]

      secrets = [
        {
          name      = "DB_PASSWORD"
          valueFrom = aws_secretsmanager_secret.db_secret.arn
        },
        {
          name      = "ADMIN_PASSWORD"
          valueFrom = aws_secretsmanager_secret.admin_secret.arn
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:${var.container_port}${var.health_check_path} || exit 1"]
        interval    = 15
        timeout     = 5
        retries     = 3
        startPeriod = 45
      }
    }
  ])

  tags = {
    Name = "${var.project_name}-task-def"
  }
}

# 4. ECS Service with CodeDeploy Deployment Controller
resource "aws_ecs_service" "app" {
  name            = "${var.project_name}-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.app_count
  launch_type     = "FARGATE"

  # CRITICAL: deployment_controller MUST be CODE_DEPLOY for Blue-Green ALB routing
  deployment_controller {
    type = "CODE_DEPLOY"
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.blue.arn
    container_name   = var.project_name
    container_port   = var.container_port
  }

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  lifecycle {
    ignore_changes = [
      task_definition,
      load_balancer
    ]
  }

  depends_on = [
    aws_lb_listener.prod,
    aws_lb_listener.test,
    aws_iam_role_policy_attachment.ecs_execution_base
  ]

  tags = {
    Name = "${var.project_name}-service"
  }
}
