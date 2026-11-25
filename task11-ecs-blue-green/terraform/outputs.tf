
output "alb_dns_name" {
  description = "Public DNS name of the Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_web_service_name" {
  description = "Frappe web ECS service name"
  value       = aws_ecs_service.web.name
}

output "database_endpoint" {
  description = "RDS MariaDB endpoint"
  value       = aws_db_instance.mariadb.address
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = aws_elasticache_cluster.main.cache_nodes[0].address
}

output "efs_file_system_id" {
  description = "Persistent Frappe EFS file system ID"
  value       = aws_efs_file_system.main.id
}

output "frappe_site_name" {
  description = "Frappe site name"
  value       = var.site_name
}
