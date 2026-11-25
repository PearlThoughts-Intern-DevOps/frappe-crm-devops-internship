
resource "aws_db_subnet_group" "main" {
  name       = "${local.name_prefix}-db-subnets"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "${local.name_prefix}-db-subnets"
  }
}

resource "aws_db_instance" "mariadb" {
  identifier = "${local.name_prefix}-mariadb"

  engine         = "mariadb"
  engine_version = "10.6.28"
  instance_class = "db.t3.micro"

  allocated_storage     = 20
  max_allocated_storage = 30
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = "frappe"
  username = "frappeadmin"

  manage_master_user_password = true

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.database.id]
  publicly_accessible    = false

  multi_az                   = false
  backup_retention_period    = 1
  auto_minor_version_upgrade = true

  deletion_protection = false
  skip_final_snapshot = true

  tags = {
    Name        = "${local.name_prefix}-mariadb"
    Environment = var.environment
  }
}
