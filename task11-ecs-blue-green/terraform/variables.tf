
variable "aws_region" {
  description = "AWS deployment region"
  type        = string
  default     = "ap-southeast-2"
}

variable "project_name" {
  description = "Project name used for AWS resources"
  type        = string
  default     = "frappe-crm-task11"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.20.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDR blocks in separate Availability Zones"
  type        = list(string)
  default     = ["10.20.1.0/24", "10.20.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "Private subnet CIDR blocks in separate Availability Zones"
  type        = list(string)
  default     = ["10.20.11.0/24", "10.20.12.0/24"]
}

variable "container_port" {
  description = "Frappe web container port"
  type        = number
  default     = 8000
}

variable "ecr_repository_name" {
  description = "Existing ECR repository name"
  type        = string
  default     = "frappe-crm"
}

variable "image_tag" {
  description = "Hardened Docker image tag"
  type        = string
  default     = "15-hardened-2-amd64"
}
variable "site_name" {
  description = "Frappe site name created during initialization"
  type        = string
  default     = "crm.local"
}
