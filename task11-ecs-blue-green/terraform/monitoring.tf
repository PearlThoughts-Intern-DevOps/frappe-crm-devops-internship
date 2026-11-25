
# ALB-generated HTTP 5xx errors
resource "aws_cloudwatch_metric_alarm" "alb_5xx" {
  alarm_name          = "${local.name_prefix}-alb-5xx-errors"
  alarm_description   = "ALB is returning HTTP 5xx errors"
  namespace           = "AWS/ApplicationELB"
  metric_name         = "HTTPCode_ELB_5XX_Count"
  statistic           = "Sum"
  period              = 60
  evaluation_periods  = 2
  threshold           = 5
  comparison_operator = "GreaterThanOrEqualToThreshold"

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
  }

  treat_missing_data = "notBreaching"
}

# Application-generated HTTP 5xx errors
resource "aws_cloudwatch_metric_alarm" "target_5xx" {
  alarm_name          = "${local.name_prefix}-target-5xx-errors"
  alarm_description   = "Frappe application targets are returning HTTP 5xx errors"
  namespace           = "AWS/ApplicationELB"
  metric_name         = "HTTPCode_Target_5XX_Count"
  statistic           = "Sum"
  period              = 60
  evaluation_periods  = 2
  threshold           = 5
  comparison_operator = "GreaterThanOrEqualToThreshold"

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
  }

  treat_missing_data = "notBreaching"
}

# Blue target group health
resource "aws_cloudwatch_metric_alarm" "unhealthy_targets" {
  alarm_name          = "${local.name_prefix}-blue-unhealthy-targets"
  alarm_description   = "Blue target group has unhealthy application targets"
  namespace           = "AWS/ApplicationELB"
  metric_name         = "UnHealthyHostCount"
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 2
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
    TargetGroup  = aws_lb_target_group.blue.arn_suffix
  }

  treat_missing_data = "notBreaching"
}

# Green target group health
resource "aws_cloudwatch_metric_alarm" "green_unhealthy_targets" {
  alarm_name          = "${local.name_prefix}-green-unhealthy-targets"
  alarm_description   = "Green target group has unhealthy application targets"
  namespace           = "AWS/ApplicationELB"
  metric_name         = "UnHealthyHostCount"
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 2
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
    TargetGroup  = aws_lb_target_group.green.arn_suffix
  }

  treat_missing_data = "notBreaching"
}
