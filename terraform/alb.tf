# =============================================================================
# Application Load Balancer with Blue-Green Target Groups
# =============================================================================
# Architecture:
# - Internet-facing ALB deployed across 2 public subnets
# - Blue Target Group (Active production traffic initially)
# - Green Target Group (Pre-traffic validation and deployment stage)
# - Production Listener on Port 80
# - Test Listener on Port 8080 (Used by CodeDeploy for pre-shift health tests)
# =============================================================================

resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = false

  tags = {
    Name = "${var.project_name}-alb"
  }
}

# --- Blue Target Group ---
resource "aws_lb_target_group" "blue" {
  name                 = "${var.project_name}-tg-blue"
  port                 = var.container_port
  protocol             = "HTTP"
  vpc_id               = aws_vpc.main.id
  target_type          = "ip"
  deregistration_delay = var.deregistration_delay

  health_check {
    enabled             = true
    path                = var.health_check_path
    port                = "traffic-port"
    protocol            = "HTTP"
    matcher             = "200,301,302"
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  tags = {
    Name  = "${var.project_name}-tg-blue"
    Color = "Blue"
  }
}

# --- Green Target Group ---
resource "aws_lb_target_group" "green" {
  name                 = "${var.project_name}-tg-green"
  port                 = var.container_port
  protocol             = "HTTP"
  vpc_id               = aws_vpc.main.id
  target_type          = "ip"
  deregistration_delay = var.deregistration_delay

  health_check {
    enabled             = true
    path                = var.health_check_path
    port                = "traffic-port"
    protocol            = "HTTP"
    matcher             = "200,301,302"
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  tags = {
    Name  = "${var.project_name}-tg-green"
    Color = "Green"
  }
}

# --- Production Listener (Port 80) ---
resource "aws_lb_listener" "prod" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.blue.arn
  }

  # CRITICAL: Prevent Terraform from reverting CodeDeploy traffic shifting
  lifecycle {
    ignore_changes = [default_action]
  }

  tags = {
    Name = "${var.project_name}-listener-prod"
    Role = "ProductionTraffic"
  }
}

# --- Test Listener (Port 8080) for Blue-Green Pre-Switch Validation ---
resource "aws_lb_listener" "test" {
  load_balancer_arn = aws_lb.main.arn
  port              = 8080
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.green.arn
  }

  # CRITICAL: Prevent Terraform from reverting CodeDeploy traffic shifting
  lifecycle {
    ignore_changes = [default_action]
  }

  tags = {
    Name = "${var.project_name}-listener-test"
    Role = "TestTraffic"
  }
}
