
resource "aws_efs_file_system" "main" {
  creation_token = "${local.name_prefix}-efs"
  encrypted      = true

  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }

  tags = {
    Name        = "${local.name_prefix}-efs"
    Environment = var.environment
  }
}

resource "aws_efs_mount_target" "private" {
  count = length(aws_subnet.private)

  file_system_id  = aws_efs_file_system.main.id
  subnet_id       = aws_subnet.private[count.index].id
  security_groups = [aws_security_group.efs.id]
}

resource "aws_efs_access_point" "frappe" {
  file_system_id = aws_efs_file_system.main.id

  posix_user {
    uid = 1000
    gid = 0
  }

  root_directory {
    path = "/frappe-sites"

    creation_info {
      owner_uid   = 1000
      owner_gid   = 0
      permissions = "0775"
    }
  }

  tags = {
    Name = "${local.name_prefix}-frappe-access-point"
  }
}
