output "ecr_repository_url" {
  description = "ECR repository URL for the Frappe CRM image"
  value       = aws_ecr_repository.crm.repository_url
}

output "ecr_repository_arn" {
  description = "ECR repository ARN"
  value       = aws_ecr_repository.crm.arn
}
