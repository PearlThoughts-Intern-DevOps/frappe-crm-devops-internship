# =============================================================================
# Amazon RDS MariaDB Database Tier (Multi-AZ in Private Subnets)
# =============================================================================

# 1. DB Subnet Group across Private Subnets
resource "aws_db_subnet_group" "main" {
  name        = "${var.project_name}-db-subnet-group"
  description = "Subnet group for RDS MariaDB instance"
  subnet_ids  = aws_subnet.private[*].id

  tags = {
    Name = "${var.project_name}-db-subnet-group"
  }
}

# 2. MariaDB Parameter Group with utf8mb4 for Frappe Framework
resource "aws_db_parameter_group" "mariadb" {
  name        = "${var.project_name}-mariadb10-params"
  family      = "mariadb10.11"
  description = "Custom parameter group configured for Frappe CRM utf8mb4 charset"

  parameter {
    name  = "character_set_server"
    value = "utf8mb4"
  }

  parameter {
    name  = "collation_server"
    value = "utf8mb4_unicode_ci"
  }

  tags = {
    Name = "${var.project_name}-db-params"
  }
}

# 3. RDS MariaDB 10.11 Instance
resource "aws_db_instance" "mariadb" {
  identifier             = "${var.project_name}-mariadb"
  engine                 = "mariadb"
  engine_version         = "10.11.8"
  instance_class         = var.db_instance_class
  allocated_storage      = 20
  max_allocated_storage  = 50
  storage_type           = "gp3"
  db_name                = var.db_name
  username               = var.db_username
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.main.name
  parameter_group_name   = aws_db_parameter_group.mariadb.name
  vpc_security_group_ids = [aws_security_group.db.id]
  skip_final_snapshot    = true
  deletion_protection    = false
  publicly_accessible    = false

  tags = {
    Name = "${var.project_name}-mariadb"
  }
}

# 4. Secrets Manager for Secure Password Storage
resource "aws_secretsmanager_secret" "db_secret" {
  name                    = "${var.project_name}-db-password-${formatdate("YYYYMMDDhhmmss", timestamp())}"
  recovery_window_in_days = 0

  lifecycle {
    ignore_changes = [name]
  }

  tags = {
    Name = "${var.project_name}-db-secret"
  }
}

resource "aws_secretsmanager_secret_version" "db_secret_val" {
  secret_id     = aws_secretsmanager_secret.db_secret.id
  secret_string = var.db_password
}

resource "aws_secretsmanager_secret" "admin_secret" {
  name                    = "${var.project_name}-admin-password-${formatdate("YYYYMMDDhhmmss", timestamp())}"
  recovery_window_in_days = 0

  lifecycle {
    ignore_changes = [name]
  }

  tags = {
    Name = "${var.project_name}-admin-secret"
  }
}

resource "aws_secretsmanager_secret_version" "admin_secret_val" {
  secret_id     = aws_secretsmanager_secret.admin_secret.id
  secret_string = var.admin_password
}
