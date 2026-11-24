# =============================================================================
# Amazon Relational Database Service (RDS MariaDB)
# =============================================================================
# Provisions:
# - MariaDB database engine (v10.11) with utf8mb4 encoding tuned for Frappe CRM
# - Private database subnet group across 2 AZs
# - gp3 encrypted storage with auto-scaling
# - Ingress strictly allowed from ECS Fargate tasks security group
# =============================================================================

resource "aws_db_subnet_group" "main" {
  name        = "${var.project_name}-db-subnet-group"
  description = "Private database subnet group for Frappe CRM"
  subnet_ids  = aws_subnet.private[*].id

  tags = {
    Name = "${var.project_name}-db-subnet-group"
  }
}

resource "aws_db_parameter_group" "mariadb" {
  name        = "${var.project_name}-mariadb-params"
  family      = "mariadb10.11"
  description = "Frappe CRM MariaDB parameter group for utf8mb4 encoding"

  parameter {
    name  = "character_set_server"
    value = "utf8mb4"
  }

  parameter {
    name  = "collation_server"
    value = "utf8mb4_unicode_ci"
  }

  parameter {
    name  = "max_allowed_packet"
    value = "67108864" # 64MB required for Frappe document attachments and schema
  }

  tags = {
    Name = "${var.project_name}-mariadb-params"
  }
}

resource "aws_db_instance" "mariadb" {
  identifier     = "${var.project_name}-db"
  engine         = "mariadb"
  engine_version = "10.11"
  instance_class = var.db_instance_class

  allocated_storage     = 20
  max_allocated_storage = 50
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  parameter_group_name   = aws_db_parameter_group.mariadb.name

  publicly_accessible = false
  skip_final_snapshot = true
  deletion_protection = false

  tags = {
    Name = "${var.project_name}-db"
  }
}
