
resource "aws_ecs_cluster" "main" {
  name = "${local.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name        = "${local.name_prefix}-cluster"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "web" {
  name              = "/ecs/${local.name_prefix}/web"
  retention_in_days = 7

  tags = {
    Name = "${local.name_prefix}-web-logs"
  }
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/ecs/${local.name_prefix}/worker"
  retention_in_days = 7

  tags = {
    Name = "${local.name_prefix}-worker-logs"
  }
}

resource "aws_cloudwatch_log_group" "scheduler" {
  name              = "/ecs/${local.name_prefix}/scheduler"
  retention_in_days = 7

  tags = {
    Name = "${local.name_prefix}-scheduler-logs"
  }
}
