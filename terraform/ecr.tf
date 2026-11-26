# =============================================================================
# Amazon Elastic Container Registry (ECR)
# =============================================================================
# Provisions:
# - Private ECR repository for Frappe CRM container images
# - Automated image scanning on push for security vulnerability detection
# - AES-256 server-side encryption
# - Lifecycle policy to prune untagged/old images and optimize storage costs
# =============================================================================

resource "aws_ecr_repository" "frappe_crm" {
  name                 = var.ecr_repository_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name = "${var.project_name}-ecr"
  }
}

resource "aws_ecr_lifecycle_policy" "frappe_crm" {
  repository = aws_ecr_repository.frappe_crm.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images older than 7 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 7
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Keep last 15 tagged images for rollback flexibility"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v", "sha-", "task-", "latest"]
          countType     = "imageCountMoreThan"
          countNumber   = 15
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
