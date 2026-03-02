variable "project_base_name" {
  description = "The base name for the Google Cloud projects."
  type        = string
}

variable "billing_account" {
  description = "The ID of the billing account to associate with the projects."
  type        = string
}

variable "org_id" {
  description = "The ID of the organization to create the projects in."
  type        = string
}

variable "region" {
  description = "The GCP region for the subnets."
  type        = string
  default     = "us-central1"
}
