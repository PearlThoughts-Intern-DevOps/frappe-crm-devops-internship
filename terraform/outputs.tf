output "alb_url" {
  description = "Open this URL to reach Frappe CRM"
  value       = "http://${aws_lb.app.dns_name}"
}

output "ecr_repository_url" {
  description = "ECR repository for the Docker image"
  value       = aws_ecr_repository.app.repository_url
}
