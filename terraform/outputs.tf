# =============================================================================
# Terraform Outputs
# =============================================================================

output "alb_dns_name" {
  description = "Application Load Balancer DNS hostname"
  value       = aws_lb.main.dns_name
}

output "production_url" {
  description = "Production application URL (Port 80)"
  value       = "http://${aws_lb.main.dns_name}"
}

output "test_validation_url" {
  description = "Pre-traffic test URL for Blue-Green deployment validation (Port 8080)"
  value       = "http://${aws_lb.main.dns_name}:8080"
}

output "ecr_repository_url" {
  description = "Amazon ECR container repository URL"
  value       = aws_ecr_repository.app.repository_url
}

output "ecs_cluster_name" {
  description = "Name of the ECS Fargate cluster"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "Name of the ECS Fargate service"
  value       = aws_ecs_service.app.name
}

output "codedeploy_application_name" {
  description = "AWS CodeDeploy application name"
  value       = var.enable_codedeploy ? aws_codedeploy_app.ecs[0].name : "frappe-crm-codedeploy-app (pending subscription)"
}

output "codedeploy_deployment_group_name" {
  description = "AWS CodeDeploy deployment group name"
  value       = var.enable_codedeploy ? aws_codedeploy_deployment_group.ecs[0].deployment_group_name : "frappe-crm-dg (pending subscription)"
}

output "rds_endpoint" {
  description = "RDS MariaDB connection endpoint"
  value       = aws_db_instance.mariadb.endpoint
}

output "redis_endpoint" {
  description = "Amazon ElastiCache Redis primary endpoint"
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group for Frappe CRM"
  value       = aws_cloudwatch_log_group.ecs.name
}
