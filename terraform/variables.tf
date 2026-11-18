variable "aws_region" {
  default = "ap-south-1"
}

variable "project_name" {
  default = "frappe-crm"
}

variable "vpc_cidr" {
  default = "10.0.0.0/16"
}

variable "subnet_cidr" {
  default = "10.0.1.0/24"
}

variable "instance_type" {
  default = "t3.medium"
}

variable "domain" {
  type = string
}

variable "email" {
  type = string
}