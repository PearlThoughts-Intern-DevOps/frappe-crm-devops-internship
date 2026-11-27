# =============================================================================
# Application Load Balancer with Blue and Green Target Groups
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

# 1. Blue Target Group (Production traffic initially)
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
    matcher             = "200"
    interval            = 20
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  tags = {
    Name  = "${var.project_name}-tg-blue"
    Color = "blue"
  }
}

# 2. Green Target Group (Replacement traffic for Blue-Green validation)
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
    matcher             = "200"
    interval            = 20
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  tags = {
    Name  = "${var.project_name}-tg-green"
    Color = "green"
  }
}

# 3. Production Listener (Port 80)
resource "aws_lb_listener" "prod" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.blue.arn
  }

  lifecycle {
    ignore_changes = [default_action] # CodeDeploy dynamically shifts traffic between Blue and Green
  }

  tags = {
    Name = "${var.project_name}-prod-listener"
  }
}

# 4. Test Listener (Port 8080) for Pre-Shift Validation
resource "aws_lb_listener" "test" {
  load_balancer_arn = aws_lb.main.arn
  port              = 8080
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.green.arn
  }

  lifecycle {
    ignore_changes = [default_action] # CodeDeploy dynamically swaps target groups during rollout
  }

  tags = {
    Name = "${var.project_name}-test-listener"
  }
}
