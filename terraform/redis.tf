# =============================================================================
# Amazon ElastiCache Redis Tier (Private Subnets)
# =============================================================================

# 1. ElastiCache Subnet Group across Private Subnets
resource "aws_elasticache_subnet_group" "redis" {
  name        = "${var.project_name}-redis-subnet-group"
  description = "Subnet group for Redis cluster"
  subnet_ids  = aws_subnet.private[*].id

  tags = {
    Name = "${var.project_name}-redis-subnet-group"
  }
}

# 2. Redis Replication Group (Handles Session Cache, Background Queues & Websockets)
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "${var.project_name}-redis"
  description                = "Redis cluster for Frappe CRM session caching and background workers"
  node_type                  = "cache.t4g.micro"
  num_cache_clusters         = 1
  port                       = 6379
  parameter_group_name       = "default.redis7"
  subnet_group_name          = aws_elasticache_subnet_group.redis.name
  security_group_ids         = [aws_security_group.redis.id]
  at_rest_encryption_enabled = false
  transit_encryption_enabled = false
  auto_minor_version_upgrade = true

  tags = {
    Name = "${var.project_name}-redis"
  }
}
