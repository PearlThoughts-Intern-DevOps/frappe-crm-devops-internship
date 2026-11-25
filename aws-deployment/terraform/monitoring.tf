resource "aws_cloudwatch_metric_alarm" "ecs_cpu" {
  alarm_name          = "${local.name_prefix}-high-cpu"
  alarm_description   = "ECS CPU utilization is too high"
  namespace           = "AWS/ECS"
  metric_name         = "CPUUtilization"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  threshold           = 80
  comparison_operator = "GreaterThanThreshold"

  dimensions = {
    ClusterName = aws_ecs_cluster.crm.name
    ServiceName = aws_ecs_service.crm.name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "ecs_memory" {
  alarm_name          = "${local.name_prefix}-high-memory"
  alarm_description   = "ECS memory utilization is too high"
  namespace           = "AWS/ECS"
  metric_name         = "MemoryUtilization"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  threshold           = 85
  comparison_operator = "GreaterThanThreshold"

  dimensions = {
    ClusterName = aws_ecs_cluster.crm.name
    ServiceName = aws_ecs_service.crm.name
  }

  tags = local.common_tags
}
