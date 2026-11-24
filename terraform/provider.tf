# =============================================================================
# AWS Provider Configuration
# =============================================================================

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile != "" ? var.aws_profile : null

  default_tags {
    tags = {
      Project            = var.project_name
      Environment        = var.environment
      ManagedBy          = "Terraform"
      DeploymentStrategy = "Blue-Green"
      Application        = "Frappe-CRM"
    }
  }
}
