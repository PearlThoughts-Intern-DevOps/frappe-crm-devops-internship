resource "aws_ecs_cluster" "crm" {
  name = "${local.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "crm" {
  name              = "/ecs/${local.name_prefix}"
  retention_in_days = 7

  tags = local.common_tags
}

resource "aws_ecs_task_definition" "crm" {
  family                   = "${local.name_prefix}-app"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "1024"
  memory                   = "2048"

  execution_role_arn = aws_iam_role.ecs_execution.arn
  task_role_arn      = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "crm"
      image     = "${aws_ecr_repository.crm.repository_url}:${var.container_image_tag}"
      essential = true

      portMappings = [{
        containerPort = 8000
        hostPort      = 8000
        protocol      = "tcp"
      }]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.crm.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "crm"
        }
      }
    }
  ])

  tags = local.common_tags
}
