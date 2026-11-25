resource "aws_ecs_service" "crm" {
  name            = "${local.name_prefix}-service"
  cluster         = aws_ecs_cluster.crm.id
  task_definition = aws_ecs_task_definition.crm.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  deployment_controller {
    type = "CODE_DEPLOY"
  }

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.blue.arn
    container_name   = "crm"
    container_port   = 8000
  }

  lifecycle {
    ignore_changes = [
      task_definition,
      load_balancer
    ]
  }

  tags = local.common_tags

  depends_on = [
    aws_iam_role_policy_attachment.ecs_execution
  ]
}
