# =============================================================================
# Security Groups Configuration
# =============================================================================

# 1. ALB Security Group (Allows HTTP 80 for Prod and 8080 for Blue-Green Test traffic)
resource "aws_security_group" "alb" {
  name        = "${var.project_name}-alb-sg"
  description = "Allows inbound HTTP traffic on port 80 and test port 8080 to ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "Production traffic"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Pre-traffic test route for Blue-Green deployment validation"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Outbound to anywhere"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-alb-sg"
  }
}

# 2. ECS Tasks Security Group (Allows traffic strictly from ALB)
resource "aws_security_group" "ecs_tasks" {
  name        = "${var.project_name}-ecs-tasks-sg"
  description = "Allows inbound traffic only from the ALB to ECS Fargate tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Frappe CRM app port from ALB only"
    from_port       = var.container_port
    to_port         = var.container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    description = "All outbound traffic for package updates, NAT egress, and DB access"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-ecs-tasks-sg"
  }
}

# 3. RDS MariaDB Security Group (Allows 3306 only from ECS Tasks)
resource "aws_security_group" "db" {
  name        = "${var.project_name}-rds-sg"
  description = "Allows MySQL/MariaDB access only from ECS Tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "MariaDB port from ECS tasks"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-rds-sg"
  }
}

# 4. Redis Security Group (Allows 6379 only from ECS Tasks)
resource "aws_security_group" "redis" {
  name        = "${var.project_name}-redis-sg"
  description = "Allows Redis access only from ECS Tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Redis port from ECS tasks"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-redis-sg"
  }
}
