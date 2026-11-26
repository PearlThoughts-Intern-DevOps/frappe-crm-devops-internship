# =============================================================================
# Amazon CloudWatch Monitoring, Alarms, and Observability Dashboard
# =============================================================================
# Provisions:
# 1. Centralized Log Group for ECS Fargate Task logs with cost-controlled retention
# 2. SNS Alert Topic for critical notifications
# 3. CloudWatch Metric Alarms with automated CodeDeploy rollback hooks:
#    - ECS High CPU Utilization (> 80%)
#    - ECS High Memory Utilization (> 85%)
#    - ALB 5XX Target Errors (> 0, triggers CodeDeploy auto-rollback)
#    - Target Group Unhealthy Host Count (>= 1, triggers CodeDeploy auto-rollback)
#    - High Target Response Latency (> 2.0s)
# 4. Operations Dashboard with multi-metric visualization
# =============================================================================

# --- CloudWatch Log Group ---
resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 14

  tags = {
    Name = "/ecs/${var.project_name}"
  }
}

# --- SNS Topic for Alerts ---
resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-alerts"

  tags = {
    Name = "${var.project_name}-alerts"
  }
}

# --- CloudWatch Metric Alarms ---

# 1. ALB Target 5XX Error Alarm (Rollback trigger)
resource "aws_cloudwatch_metric_alarm" "alb_5xx" {
  alarm_name          = "${var.project_name}-alb-5xx-alarm"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Triggered when Frappe CRM target returns HTTP 5XX error. Triggers CodeDeploy automatic rollback."
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
  }

  tags = {
    Name     = "${var.project_name}-alb-5xx-alarm"
    Rollback = "Enabled"
  }
}

# 2. Unhealthy Host Count Alarm (Rollback trigger)
resource "aws_cloudwatch_metric_alarm" "unhealthy_hosts" {
  alarm_name          = "${var.project_name}-unhealthy-hosts-alarm"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "UnHealthyHostCount"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Maximum"
  threshold           = 1
  alarm_description   = "Triggered when a Frappe CRM container fails health checks. Triggers CodeDeploy rollback."
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    TargetGroup  = aws_lb_target_group.blue.arn_suffix
    LoadBalancer = aws_lb.main.arn_suffix
  }

  tags = {
    Name     = "${var.project_name}-unhealthy-hosts-alarm"
    Rollback = "Enabled"
  }
}

# 3. High ECS CPU Utilization Alarm
resource "aws_cloudwatch_metric_alarm" "ecs_cpu_high" {
  alarm_name          = "${var.project_name}-ecs-cpu-high"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 60
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Triggered when ECS Fargate tasks CPU exceeds 80% for 2 minutes."
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.main.name
  }

  tags = {
    Name = "${var.project_name}-ecs-cpu-high"
  }
}

# 4. High ECS Memory Utilization Alarm
resource "aws_cloudwatch_metric_alarm" "ecs_memory_high" {
  alarm_name          = "${var.project_name}-ecs-memory-high"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = 60
  statistic           = "Average"
  threshold           = 85
  alarm_description   = "Triggered when ECS Fargate tasks Memory exceeds 85% for 2 minutes."
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.main.name
  }

  tags = {
    Name = "${var.project_name}-ecs-memory-high"
  }
}

# 5. High Target Response Time Alarm
resource "aws_cloudwatch_metric_alarm" "target_response_time" {
  alarm_name          = "${var.project_name}-target-response-time"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Average"
  threshold           = 2.0
  alarm_description   = "Triggered when average target response time exceeds 2.0 seconds."
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
  }

  tags = {
    Name = "${var.project_name}-target-response-time"
  }
}

# --- CloudWatch Unified Observability Dashboard ---
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_name}-ecs-bluegreen-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", "ServiceName", aws_ecs_service.main.name, "ClusterName", aws_ecs_cluster.main.name, { color = "#ff7f0e", label = "ECS CPU Utilization %" }],
            ["AWS/ECS", "MemoryUtilization", "ServiceName", aws_ecs_service.main.name, "ClusterName", aws_ecs_cluster.main.name, { color = "#2ca02c", label = "ECS Memory Utilization %" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "ECS Fargate Compute Utilization (CPU & Memory %)"
          period  = 60
          yAxis = {
            left = { min = 0, max = 100 }
          }
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", aws_lb.main.arn_suffix, { stat = "Sum", color = "#1f77b4", label = "Total Requests" }],
            ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", aws_lb.main.arn_suffix, { stat = "Average", color = "#d62728", label = "Avg Response Time (s)" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Application Load Balancer Traffic & Latency"
          period  = 60
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "HealthyHostCount", "TargetGroup", aws_lb_target_group.blue.arn_suffix, "LoadBalancer", aws_lb.main.arn_suffix, { stat = "Maximum", color = "#0000ff", label = "Blue Target Group Healthy Hosts" }],
            ["AWS/ApplicationELB", "HealthyHostCount", "TargetGroup", aws_lb_target_group.green.arn_suffix, "LoadBalancer", aws_lb.main.arn_suffix, { stat = "Maximum", color = "#00aa00", label = "Green Target Group Healthy Hosts" }],
            ["AWS/ApplicationELB", "UnHealthyHostCount", "TargetGroup", aws_lb_target_group.blue.arn_suffix, "LoadBalancer", aws_lb.main.arn_suffix, { stat = "Maximum", color = "#ff0000", label = "Blue Unhealthy Hosts" }],
            ["AWS/ApplicationELB", "UnHealthyHostCount", "TargetGroup", aws_lb_target_group.green.arn_suffix, "LoadBalancer", aws_lb.main.arn_suffix, { stat = "Maximum", color = "#990000", label = "Green Unhealthy Hosts" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Blue vs Green Target Group Host Health Status"
          period  = 60
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "HTTPCode_Target_2XX_Count", "LoadBalancer", aws_lb.main.arn_suffix, { stat = "Sum", color = "#2ca02c", label = "HTTP 2XX Success" }],
            ["AWS/ApplicationELB", "HTTPCode_Target_4XX_Count", "LoadBalancer", aws_lb.main.arn_suffix, { stat = "Sum", color = "#ff7f0e", label = "HTTP 4XX Client Errors" }],
            ["AWS/ApplicationELB", "HTTPCode_Target_5XX_Count", "LoadBalancer", aws_lb.main.arn_suffix, { stat = "Sum", color = "#d62728", label = "HTTP 5XX Target Errors" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Target HTTP Response Codes (2XX vs 4XX vs 5XX)"
          period  = 60
        }
      }
    ]
  })
}
