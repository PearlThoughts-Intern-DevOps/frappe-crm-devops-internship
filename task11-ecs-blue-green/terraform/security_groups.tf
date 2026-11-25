
# ALB: accepts public HTTP traffic
resource "aws_security_group" "alb" {
  name        = "${local.name_prefix}-alb-sg"
  description = "Allow HTTP traffic to the Application Load Balancer"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP from internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Traffic to application targets"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix}-alb-sg"
  }
}

# ECS: accepts application traffic only from the ALB
resource "aws_security_group" "ecs" {
  name        = "${local.name_prefix}-ecs-sg"
  description = "Allow Frappe traffic only from the ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Frappe web traffic from ALB"
    from_port       = var.container_port
    to_port         = var.container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    description     = "Socket.IO traffic from ALB"
    from_port       = 9000
    to_port         = 9000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    description = "Outbound application traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix}-ecs-sg"
  }
}

# MariaDB: accepts connections only from ECS
resource "aws_security_group" "database" {
  name        = "${local.name_prefix}-database-sg"
  description = "Allow MariaDB traffic only from ECS"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "MariaDB from ECS"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  tags = {
    Name = "${local.name_prefix}-database-sg"
  }
}

# Redis: accepts connections only from ECS
resource "aws_security_group" "redis" {
  name        = "${local.name_prefix}-redis-sg"
  description = "Allow Redis traffic only from ECS"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Redis from ECS"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  tags = {
    Name = "${local.name_prefix}-redis-sg"
  }
}

# EFS: accepts NFS connections only from ECS
resource "aws_security_group" "efs" {
  name        = "${local.name_prefix}-efs-sg"
  description = "Allow NFS traffic only from ECS"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "NFS from ECS"
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  tags = {
    Name = "${local.name_prefix}-efs-sg"
  }
}
