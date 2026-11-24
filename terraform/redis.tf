# =============================================================================
# Amazon ElastiCache (Redis) Infrastructure
# =============================================================================
# Provisions:
# - In-memory Redis cache and background queue broker for Frappe CRM
# - Private subnet deployment across availability zones
# - Least-privilege security group access limited to ECS Fargate tasks
# =============================================================================

resource "aws_elasticache_subnet_group" "main" {
  name        = "${var.project_name}-redis-subnet-group"
  description = "Private subnet group for Frappe CRM Redis cluster"
  subnet_ids  = aws_subnet.private[*].id

  tags = {
    Name = "${var.project_name}-redis-subnet-group"
  }
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "${var.project_name}-redis"
  engine               = "redis"
  engine_version       = "7.0"
  node_type            = "cache.t4g.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379

  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]

  tags = {
    Name = "${var.project_name}-redis"
  }
}
