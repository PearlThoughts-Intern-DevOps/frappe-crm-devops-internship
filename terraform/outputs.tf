output "ec2_public_ip" {
  value = aws_instance.frappe.public_ip
}

output "ec2_instance_id" {
  value = aws_instance.frappe.id
}

output "s3_bucket_name" {
  value = aws_s3_bucket.storage.id
}

output "crm_url" {
  value = "https://${var.domain}"
}