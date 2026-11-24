# =============================================================================
# Security Groups (Least-Privilege Isolation)
# =============================================================================
# 1. ALB Security Group: Ingress 80 (Prod) & 8080 (Test) from Internet
# 2. ECS Security Group: Ingress 8000 strictly from ALB Security Group
# 3. Database Security Group: Ingress 3306 strictly from ECS Security Group
# 4. Redis Security Group: Ingress 6379 strictly from ECS Security Group
# =============================================================================

# --- ALB Security Group ---
resource "aws_security_group" "alb" {
  name        = "${var.project_name}-alb-sg"
  description = "Security group for Frappe CRM Application Load Balancer"
  vpc_id      = aws_vpc.main.id

  # Production HTTP Traffic
  ingress {
    description = "Production HTTP listener"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Blue-Green Test Listener (Pre-traffic switch validation)
  ingress {
    description = "Blue-Green test listener for pre-traffic shifting"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Egress to ECS tasks
  egress {
    description = "Allow all outbound traffic from ALB"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-alb-sg"
  }
}

# --- ECS Fargate Security Group ---
resource "aws_security_group" "ecs" {
  name        = "${var.project_name}-ecs-sg"
  description = "Security group for Frappe CRM ECS Fargate tasks"
  vpc_id      = aws_vpc.main.id

  # Ingress port 8000 exclusively from ALB
  ingress {
    description     = "Allow traffic from ALB on container port 8000"
    from_port       = var.container_port
    to_port         = var.container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # Outbound to AWS APIs (ECR, CloudWatch), NAT Gateway, RDS, Redis
  egress {
    description = "Allow outbound to NAT, AWS services, and databases"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-ecs-sg"
  }
}

# --- Database Security Group (RDS MariaDB) ---
resource "aws_security_group" "db" {
  name        = "${var.project_name}-db-sg"
  description = "Security group for Frappe CRM RDS MariaDB"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Allow MariaDB access strictly from ECS Fargate tasks"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  egress {
    description = "Allow outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-db-sg"
  }
}

# --- Redis Security Group (ElastiCache) ---
resource "aws_security_group" "redis" {
  name        = "${var.project_name}-redis-sg"
  description = "Security group for Frappe CRM Redis cache and queue"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Allow Redis access strictly from ECS Fargate tasks"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  egress {
    description = "Allow outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-redis-sg"
  }
}
