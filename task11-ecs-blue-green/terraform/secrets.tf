
resource "random_password" "frappe_admin" {
  length           = 24
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "aws_secretsmanager_secret" "frappe_admin" {
  name                    = "${local.name_prefix}-frappe-admin"
  description             = "Frappe CRM Administrator password"
  recovery_window_in_days = 7

  tags = {
    Name        = "${local.name_prefix}-frappe-admin"
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "frappe_admin" {
  secret_id     = aws_secretsmanager_secret.frappe_admin.id
  secret_string = random_password.frappe_admin.result
}
