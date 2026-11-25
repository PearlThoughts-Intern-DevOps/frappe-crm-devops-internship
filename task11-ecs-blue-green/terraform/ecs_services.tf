
# Common network configuration for Fargate services
locals {
  ecs_network_configuration = {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }
}

# Frappe web service - managed by CodeDeploy for blue-green deployments
resource "aws_ecs_service" "web" {
  name            = "${local.name_prefix}-web"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.web.arn
  desired_count   = 0
  launch_type     = "FARGATE"

  deployment_controller {
    type = "CODE_DEPLOY"
  }

  network_configuration {
    subnets          = local.ecs_network_configuration.subnets
    security_groups  = local.ecs_network_configuration.security_groups
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.blue.arn
    container_name   = "frappe-web"
    container_port   = var.container_port
  }

  health_check_grace_period_seconds = 120

  depends_on = [
    aws_lb_listener.http,
    aws_efs_mount_target.private
  ]

  tags = {
    Name = "${local.name_prefix}-web-service"
  }
}

# Background worker service
resource "aws_ecs_service" "worker" {
  name            = "${local.name_prefix}-worker"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = 0
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = local.ecs_network_configuration.subnets
    security_groups  = local.ecs_network_configuration.security_groups
    assign_public_ip = true
  }

  depends_on = [aws_efs_mount_target.private]

  tags = {
    Name = "${local.name_prefix}-worker-service"
  }
}

# Scheduler service
resource "aws_ecs_service" "scheduler" {
  name            = "${local.name_prefix}-scheduler"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.scheduler.arn
  desired_count   = 0
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = local.ecs_network_configuration.subnets
    security_groups  = local.ecs_network_configuration.security_groups
    assign_public_ip = true
  }

  depends_on = [aws_efs_mount_target.private]

  tags = {
    Name = "${local.name_prefix}-scheduler-service"
  }
}

# Socket.IO service
resource "aws_ecs_service" "websocket" {
  name            = "${local.name_prefix}-websocket"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.websocket.arn
  desired_count   = 0
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = local.ecs_network_configuration.subnets
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.websocket.arn
    container_name   = "frappe-websocket"
    container_port   = 9000
  }

  depends_on = [
    aws_lb_listener_rule.websocket,
    aws_efs_mount_target.private
  ]

  tags = {
    Name = "${local.name_prefix}-websocket-service"
  }
}
