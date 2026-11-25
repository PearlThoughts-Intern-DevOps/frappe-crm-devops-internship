
resource "aws_cloudwatch_log_group" "init" {
  name              = "/ecs/${local.name_prefix}/init"
  retention_in_days = 7
}

resource "aws_ecs_task_definition" "init" {
  family                   = "${local.name_prefix}-init"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"

  cpu    = "1024"
  memory = "2048"

  execution_role_arn = aws_iam_role.ecs_execution.arn
  task_role_arn      = aws_iam_role.ecs_task.arn

  volume {
    name = "frappe-sites"

    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.main.id
      transit_encryption = "ENABLED"

      authorization_config {
        access_point_id = aws_efs_access_point.frappe.id
        iam             = "DISABLED"
      }
    }
  }

  container_definitions = jsonencode([
    {
      name      = "frappe-init"
      image     = "${data.aws_ecr_repository.frappe.repository_url}:${var.image_tag}"
      essential = true

      entryPoint = ["/bin/bash", "-c"]

      command = [
        <<-SCRIPT
          set -e
          cd /home/frappe/frappe-bench

          echo "Preparing persistent Frappe sites directory..."
          mkdir -p /mnt/frappe-sites

          for file in apps.txt common_site_config.json; do
            if [ ! -f "/mnt/frappe-sites/$file" ]; then
              cp "/home/frappe/frappe-bench/sites/$file" "/mnt/frappe-sites/$file"
            fi
          done

          rm -rf /home/frappe/frappe-bench/sites
          ln -s /mnt/frappe-sites /home/frappe/frappe-bench/sites

          echo "Configuring Redis..."
          bench set-config -g redis_cache "redis://$REDIS_HOST:$REDIS_PORT"
          bench set-config -g redis_queue "redis://$REDIS_HOST:$REDIS_PORT"
          bench set-config -g redis_socketio "redis://$REDIS_HOST:$REDIS_PORT"

          if [ ! -d "sites/$SITE_NAME" ]; then
            echo "Creating Frappe site..."
            bench new-site "$SITE_NAME" \
              --db-type mariadb \
              --db-host "$DB_HOST" \
              --db-port "$DB_PORT" \
              --db-root-username "$DB_USERNAME" \
              --db-root-password "$DB_PASSWORD" \
              --mariadb-user-host-login-scope "%" \
              --admin-password "$ADMIN_PASSWORD" \
              --install-app crm \
              --set-default
          else
            echo "Frappe site already exists. Skipping creation."
          fi

          echo "Frappe initialization task completed."
        SCRIPT
      ]

      environment = [
        {
          name  = "SITE_NAME"
          value = var.site_name
        },
        {
          name  = "DB_HOST"
          value = aws_db_instance.mariadb.address
        },
        {
          name  = "DB_PORT"
          value = tostring(aws_db_instance.mariadb.port)
        },
        {
          name  = "REDIS_HOST"
          value = aws_elasticache_cluster.main.cache_nodes[0].address
        },
        {
          name  = "REDIS_PORT"
          value = tostring(aws_elasticache_cluster.main.cache_nodes[0].port)
        }
      ]

      secrets = [
        {
          name      = "DB_USERNAME"
          valueFrom = "${aws_db_instance.mariadb.master_user_secret[0].secret_arn}:username::"
        },
        {
          name      = "DB_PASSWORD"
          valueFrom = "${aws_db_instance.mariadb.master_user_secret[0].secret_arn}:password::"
        },
        {
          name      = "ADMIN_PASSWORD"
          valueFrom = aws_secretsmanager_secret.frappe_admin.arn
        }
      ]

      mountPoints = [
        {
          sourceVolume  = "frappe-sites"
          containerPath = "/mnt/frappe-sites"
          readOnly      = false
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"

        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.init.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "init"
        }
      }
    }
  ])

  tags = {
    Name        = "${local.name_prefix}-init-task"
    Environment = var.environment
  }
}
