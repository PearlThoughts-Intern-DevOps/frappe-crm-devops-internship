
# Reference the existing ECR repository
data "aws_ecr_repository" "frappe" {
  name = var.ecr_repository_name
}

# Frappe web application task
resource "aws_ecs_task_definition" "web" {
  family                   = "${local.name_prefix}-web"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"

  cpu    = "1024"
  memory = "2048"

  execution_role_arn = aws_iam_role.ecs_execution.arn
  task_role_arn      = aws_iam_role.ecs_task.arn

  volume {
    name = "frappe-sites"

    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.main.id
      transit_encryption = "ENABLED"

      authorization_config {
        access_point_id = aws_efs_access_point.frappe.id
        iam             = "DISABLED"
      }
    }
  }

  container_definitions = jsonencode([
    {
      name      = "frappe-web"
      image     = "${data.aws_ecr_repository.frappe.repository_url}:${var.image_tag}"
      essential = true

      healthCheck = {
        command = [
          "CMD-SHELL",
          "curl -fsS http://127.0.0.1:8000/ -o /dev/null || exit 1"
        ]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 180
      }

      portMappings = [
        {
          containerPort = var.container_port
          hostPort      = var.container_port
          protocol      = "tcp"
        }
      ]

      mountPoints = [
        {
          sourceVolume  = "frappe-sites"
          containerPath = "/home/frappe/frappe-bench/sites"
          readOnly      = false
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"

        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.web.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "web"
        }
      }
    }
  ])

  tags = {
    Name        = "${local.name_prefix}-web-task"
    Environment = var.environment
  }
}
