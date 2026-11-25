
resource "aws_codedeploy_app" "frappe" {
  name             = "${local.name_prefix}-app"
  compute_platform = "ECS"
}

resource "aws_codedeploy_deployment_group" "frappe" {
  app_name               = aws_codedeploy_app.frappe.name
  deployment_group_name  = "${local.name_prefix}-blue-green"
  service_role_arn       = aws_iam_role.codedeploy.arn
  deployment_config_name = "CodeDeployDefault.ECSAllAtOnce"

  deployment_style {
    deployment_type   = "BLUE_GREEN"
    deployment_option = "WITH_TRAFFIC_CONTROL"
  }

  blue_green_deployment_config {
    deployment_ready_option {
      action_on_timeout = "CONTINUE_DEPLOYMENT"
    }

    terminate_blue_instances_on_deployment_success {
      action                           = "TERMINATE"
      termination_wait_time_in_minutes = 5
    }
  }

  load_balancer_info {
    target_group_pair_info {
      prod_traffic_route {
        listener_arns = [aws_lb_listener.http.arn]
      }

      target_group {
        name = aws_lb_target_group.blue.name
      }

      target_group {
        name = aws_lb_target_group.green.name
      }
    }
  }

  alarm_configuration {
    enabled = true

    alarms = [
      aws_cloudwatch_metric_alarm.alb_5xx.alarm_name,
      aws_cloudwatch_metric_alarm.target_5xx.alarm_name,
      aws_cloudwatch_metric_alarm.unhealthy_targets.alarm_name,
      aws_cloudwatch_metric_alarm.green_unhealthy_targets.alarm_name
    ]

    ignore_poll_alarm_failure = false
  }

  auto_rollback_configuration {
    enabled = true

    events = [
      "DEPLOYMENT_FAILURE",
      "DEPLOYMENT_STOP_ON_ALARM",
      "DEPLOYMENT_STOP_ON_REQUEST"
    ]
  }

  ecs_service {
    cluster_name = aws_ecs_cluster.main.name
    service_name = aws_ecs_service.web.name
  }

  depends_on = [
    aws_ecs_service.web,
    aws_lb_listener.http
  ]
}
