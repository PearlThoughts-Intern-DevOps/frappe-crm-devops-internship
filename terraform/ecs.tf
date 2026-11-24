# =============================================================================
# Amazon Elastic Container Service (ECS) Fargate Infrastructure
# =============================================================================
# Provisions:
# - ECS Cluster with Container Insights telemetry enabled
# - ECS Fargate Task Definition configured for Frappe CRM
# - ECS Fargate Service configured with CODE_DEPLOY deployment controller
# - Integration with Blue Target Group on Application Load Balancer
# =============================================================================

# --- ECS Cluster ---
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

# --- ECS Fargate Task Definition ---
resource "aws_ecs_task_definition" "main" {
  family                   = var.project_name
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = tostring(var.fargate_cpu)
  memory                   = tostring(var.fargate_memory)
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "frappe-crm"
      image     = "${aws_ecr_repository.frappe_crm.repository_url}:${var.image_tag}"
      essential = true

      portMappings = [
        {
          containerPort = var.container_port
          hostPort      = var.container_port
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "DB_HOST"
          value = aws_db_instance.mariadb.address
        },
        {
          name  = "DB_PORT"
          value = "3306"
        },
        {
          name  = "DB_NAME"
          value = var.db_name
        },
        {
          name  = "DB_USER"
          value = var.db_username
        },
        {
          name  = "DB_PASSWORD"
          value = var.db_password
        },
        {
          name  = "REDIS_CACHE_URL"
          value = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379"
        },
        {
          name  = "REDIS_QUEUE_URL"
          value = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379"
        },
        {
          name  = "REDIS_SOCKETIO_URL"
          value = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379"
        },
        {
          name  = "SITE_NAME"
          value = var.site_name
        },
        {
          name  = "ADMIN_PASSWORD"
          value = var.admin_password
        },
        {
          name  = "AUTO_MIGRATE"
          value = "1"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "frappe"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/api/method/frappe.ping || exit 1"]
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

# --- ECS Fargate Service ---
resource "aws_ecs_service" "main" {
  name            = "${var.project_name}-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.main.arn
  desired_count   = var.app_count
  launch_type     = "FARGATE"

  # CRITICAL: Blue-Green deployment requires CodeDeploy controller
  deployment_controller {
    type = "CODE_DEPLOY"
  }

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.blue.arn
    container_name   = "frappe-crm"
    container_port   = var.container_port
  }

  # CRITICAL: Prevent Terraform conflicts with CodeDeploy target group & task updates
  lifecycle {
    ignore_changes = [
      task_definition,
      load_balancer
    ]
  }

  depends_on = [
    aws_lb_listener.prod,
    aws_lb_listener.test,
    aws_iam_role_policy_attachment.ecs_execution_policy
  ]

  tags = {
    Name = "${var.project_name}-service"
  }
}
