# =============================================================================
# FinOps: ECS Application Auto Scaling & Off-Hours Cost Optimization Schedule
# =============================================================================
# Implements:
# 1. Application Auto Scaling target for Frappe CRM ECS Fargate service
# 2. Target-tracking scaling policies (CPU >= 70%, Memory >= 75%)
# 3. Off-hours scheduled scaling (Asia/Kolkata):
#    - Work/Demo hours (Mon-Fri 09:00 IST): min 2, max 4 (full multi-AZ HA)
#    - Off-hours nights (Mon-Fri 20:00 IST): min 1, max 2 (50% lower baseline cost, still online)
#    - Weekends (Sat 00:00 IST): min 1, max 2
# =============================================================================

resource "aws_appautoscaling_target" "ecs" {
  max_capacity       = var.ecs_max_capacity
  min_capacity       = var.ecs_min_capacity
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.main.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"

  depends_on = [aws_ecs_service.main]
}

# --- Target Tracking: CPU Utilization (70%) ---
resource "aws_appautoscaling_policy" "ecs_cpu" {
  name               = "${var.project_name}-cpu-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }

    target_value       = 70.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# --- Target Tracking: Memory Utilization (75%) ---
resource "aws_appautoscaling_policy" "ecs_memory" {
  name               = "${var.project_name}-memory-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }

    target_value       = 75.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# --- Scheduled Scaling: Work / Demo Hours (Mon-Fri 09:00 IST -> min 2, max 4) ---
resource "aws_appautoscaling_scheduled_action" "scale_out_business_hours" {
  name               = "${var.project_name}-scale-out-business-hours"
  service_namespace  = aws_appautoscaling_target.ecs.service_namespace
  resource_id        = aws_appautoscaling_target.ecs.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs.scalable_dimension
  schedule           = "cron(0 9 ? * MON-FRI *)"
  timezone           = var.autoscaling_timezone

  scalable_target_action {
    min_capacity = 2
    max_capacity = var.ecs_max_capacity
  }
}

# --- Scheduled Scaling: Off-Hours Nights (Mon-Fri 20:00 IST -> min 1, max 2) ---
resource "aws_appautoscaling_scheduled_action" "scale_in_off_hours" {
  name               = "${var.project_name}-scale-in-off-hours"
  service_namespace  = aws_appautoscaling_target.ecs.service_namespace
  resource_id        = aws_appautoscaling_target.ecs.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs.scalable_dimension
  schedule           = "cron(0 20 ? * MON-FRI *)"
  timezone           = var.autoscaling_timezone

  scalable_target_action {
    min_capacity = var.ecs_min_capacity
    max_capacity = 2
  }
}

# --- Scheduled Scaling: Weekends (Sat 00:00 IST -> min 1, max 2) ---
resource "aws_appautoscaling_scheduled_action" "scale_in_weekends" {
  name               = "${var.project_name}-scale-in-weekends"
  service_namespace  = aws_appautoscaling_target.ecs.service_namespace
  resource_id        = aws_appautoscaling_target.ecs.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs.scalable_dimension
  schedule           = "cron(0 0 ? * SAT *)"
  timezone           = var.autoscaling_timezone

  scalable_target_action {
    min_capacity = var.ecs_min_capacity
    max_capacity = 2
  }
}
