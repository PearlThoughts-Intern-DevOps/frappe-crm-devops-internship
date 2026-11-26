variable "aws_region" {
  description = "Selected AWS Region for deployment"
  type        = string
  default     = "ap-southeast-2"
}

variable "project_name" {
  description = "Project prefix for resource naming and tagging"
  type        = string
  default     = "frappe-crm-ec2-obs"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "learning"
}

variable "vpc_cidr" {
  description = "CIDR block for the EC2 observability VPC"
  type        = string
  default     = "10.2.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block for the public subnet"
  type        = string
  default     = "10.2.1.0/24"
}

variable "instance_type" {
  description = "EC2 instance type (c7i-flex.large = 2 vCPU, 4 GB RAM, Free Tier eligible)"
  type        = string
  default     = "c7i-flex.large"
}

variable "root_volume_size" {
  description = "Root EBS volume size in GB"
  type        = number
  default     = 30
}

variable "allowed_web_cidr" {
  description = "CIDR allowed to access Frappe CRM HTTP port 80"
  type        = string
  default     = "0.0.0.0/0"
}

variable "allowed_monitoring_cidr" {
  description = "CIDR allowed to access Grafana (3000) and Prometheus (9090)"
  type        = string
  default     = "0.0.0.0/0"
}

variable "git_repo_url" {
  description = "GitHub repository URL to clone on EC2"
  type        = string
  default     = "https://github.com/PearlThoughts-Intern-DevOps/frappe-crm-devops-internship.git"
}

variable "git_branch" {
  description = "Git branch to deploy on EC2"
  type        = string
  default     = "task-ec2-observability-bulbul-das"
}

variable "db_password" {
  description = "MariaDB root password"
  type        = string
  sensitive   = true
  default     = "FrappeEC2RootPass2026!"
}

variable "admin_password" {
  description = "Frappe CRM Administrator password"
  type        = string
  sensitive   = true
  default     = "admin"
}

variable "grafana_admin_password" {
  description = "Grafana admin password"
  type        = string
  sensitive   = true
  default     = "FrappeGrafana2026!"
}
