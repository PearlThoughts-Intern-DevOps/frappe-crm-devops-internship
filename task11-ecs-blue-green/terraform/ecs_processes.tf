
resource "aws_ecs_task_definition" "worker" {
  family                   = "${local.name_prefix}-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"

  cpu    = "512"
  memory = "1024"

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
      name      = "frappe-worker"
      image     = "${data.aws_ecr_repository.frappe.repository_url}:${var.image_tag}"
      essential = true

      command = ["bench", "worker", "--queue", "short,default,long"]

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
          "awslogs-group"         = aws_cloudwatch_log_group.worker.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "worker"
        }
      }
    }
  ])

  tags = {
    Name        = "${local.name_prefix}-worker-task"
    Environment = var.environment
  }
}

resource "aws_ecs_task_definition" "scheduler" {
  family                   = "${local.name_prefix}-scheduler"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"

  cpu    = "256"
  memory = "512"

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
      name      = "frappe-scheduler"
      image     = "${data.aws_ecr_repository.frappe.repository_url}:${var.image_tag}"
      essential = true

      command = ["bench", "schedule"]

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
          "awslogs-group"         = aws_cloudwatch_log_group.scheduler.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "scheduler"
        }
      }
    }
  ])

  tags = {
    Name        = "${local.name_prefix}-scheduler-task"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "websocket" {
  name              = "/ecs/${local.name_prefix}/websocket"
  retention_in_days = 7
}

resource "aws_ecs_task_definition" "websocket" {
  family                   = "${local.name_prefix}-websocket"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"

  cpu    = "256"
  memory = "512"

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
      name      = "frappe-websocket"
      image     = "${data.aws_ecr_repository.frappe.repository_url}:${var.image_tag}"
      essential = true

      command = [
        "node",
        "/home/frappe/frappe-bench/apps/frappe/socketio.js"
      ]

      portMappings = [
        {
          containerPort = 9000
          hostPort      = 9000
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
          "awslogs-group"         = aws_cloudwatch_log_group.websocket.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "websocket"
        }
      }
    }
  ])

  tags = {
    Name        = "${local.name_prefix}-websocket-task"
    Environment = var.environment
  }
}
