variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}
variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.50.0.0/16"
}
