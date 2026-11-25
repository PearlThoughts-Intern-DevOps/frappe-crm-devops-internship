variable "aws_region" {
  description = "AWS region for the Frappe CRM deployment"
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Project identifier used for AWS resource names"
  type        = string
  default     = "frappe-crm"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

variable "container_image_tag" {
  description = "Container image tag deployed to ECS"
  type        = string
  default     = "latest"
}

variable "vpc_cidr" {
  description = "CIDR block for the deployment VPC"
  type        = string
  default     = "10.20.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones used by the deployment"
  type        = list(string)
  default     = ["ap-south-1a", "ap-south-1b"]
}
