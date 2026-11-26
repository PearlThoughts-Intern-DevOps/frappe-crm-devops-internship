# =============================================================================
# Terraform Outputs
# =============================================================================

output "alb_dns_name" {
  description = "Public URL for Frappe CRM Production Application"
  value       = "http://${aws_lb.main.dns_name}"
}

output "alb_test_listener_url" {
  description = "URL for Blue-Green Pre-Switch Validation (Test Listener Port 8080)"
  value       = "http://${aws_lb.main.dns_name}:8080"
}

output "ecr_repository_url" {
  description = "Amazon ECR Repository URL for pushing Frappe CRM container images"
  value       = aws_ecr_repository.frappe_crm.repository_url
}

output "ecs_cluster_name" {
  description = "Amazon ECS Cluster Name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "Amazon ECS Service Name"
  value       = aws_ecs_service.main.name
}

output "codedeploy_app_name" {
  description = "AWS CodeDeploy Application Name"
  value       = aws_codedeploy_app.ecs.name
}

output "codedeploy_deployment_group_name" {
  description = "AWS CodeDeploy Deployment Group Name"
  value       = aws_codedeploy_deployment_group.ecs.deployment_group_name
}

output "cloudwatch_log_group" {
  description = "Amazon CloudWatch Log Group for ECS Task Logs"
  value       = aws_cloudwatch_log_group.ecs.name
}

output "cloudwatch_dashboard_name" {
  description = "Amazon CloudWatch Monitoring Dashboard Name"
  value       = aws_cloudwatch_dashboard.main.dashboard_name
}

output "rds_endpoint" {
  description = "Amazon RDS MariaDB Endpoint"
  value       = aws_db_instance.mariadb.endpoint
}

output "redis_endpoint" {
  description = "Amazon ElastiCache Redis Primary Endpoint"
  value       = "${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379"
}

output "ecs_autoscaling_range" {
  description = "ECS Fargate Auto Scaling Min/Max Capacity Range"
  value       = "${var.ecs_min_capacity} to ${var.ecs_max_capacity} tasks (${var.autoscaling_timezone})"
}
