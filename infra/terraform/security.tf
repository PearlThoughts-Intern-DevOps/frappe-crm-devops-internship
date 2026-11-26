# =============================================================================
# Security Group: No SSH port 22 exposed (uses AWS SSM Session Manager instead)
# Exposes only Frappe CRM (80), Grafana (3000), and Prometheus (9090).
# Loki (3100), Promtail, and all Exporters remain internal to the Docker network.
# =============================================================================

resource "aws_security_group" "ec2_obs" {
  name        = "${var.project_name}-sg"
  description = "Allow HTTP for Frappe CRM and Grafana/Prometheus UI access (SSM used instead of SSH)"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "Frappe CRM Web UI (HTTP)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = [var.allowed_web_cidr]
  }

  ingress {
    description = "Grafana UI"
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = [var.allowed_monitoring_cidr]
  }

  ingress {
    description = "Prometheus UI"
    from_port   = 9090
    to_port     = 9090
    protocol    = "tcp"
    cidr_blocks = [var.allowed_monitoring_cidr]
  }

  egress {
    description = "Allow outbound for Docker Hub pulls, apt updates, and GitHub clone"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-sg"
  }
}
