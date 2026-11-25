variable "region" {
  description = "AWS region"
  type        = string
  default     = "ap-south-1"
}

variable "project" {
  description = "Name prefix for all resources (the GitHub workflow uses the default, frappe-crm)"
  type        = string
  default     = "frappe-crm"
}

variable "task_cpu" {
  description = "Fargate task CPU units"
  type        = string
  default     = "2048"
}

variable "task_memory" {
  description = "Fargate task memory in MiB"
  type        = string
  default     = "4096"
}

variable "db_root_password" {
  description = "MariaDB root password"
  type        = string
  sensitive   = true
}

variable "admin_password" {
  description = "Frappe Administrator password"
  type        = string
  sensitive   = true
}
