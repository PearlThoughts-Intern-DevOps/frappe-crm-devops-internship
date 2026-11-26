data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "frappe_obs" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.ec2_obs.id]
  iam_instance_profile        = aws_iam_instance_profile.ec2_ssm.name
  associate_public_ip_address = true

  # FinOps: Standard CPU credits prevent unexpected T3 unlimited surplus billing
  credit_specification {
    cpu_credits = "standard"
  }

  # Security: Enforce IMDSv2 + hop limit 2 so Docker containers can safely use metadata if needed
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
  }

  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.root_volume_size
    encrypted             = true
    delete_on_termination = true

    tags = {
      Name = "${var.project_name}-root-ebs"
    }
  }

  user_data = templatefile("${path.module}/scripts/user_data.sh.tftpl", {
    git_repo_url           = var.git_repo_url
    git_branch             = var.git_branch
    db_password            = var.db_password
    admin_password         = var.admin_password
    grafana_admin_password = var.grafana_admin_password
  })

  lifecycle {
    ignore_changes = [ami, user_data]
  }

  tags = {
    Name = "${var.project_name}-server"
  }
}
