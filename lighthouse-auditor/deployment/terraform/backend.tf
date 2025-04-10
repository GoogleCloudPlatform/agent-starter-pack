terraform {
  backend "gcs" {
    bucket = "capstone-455820-terraform-state"
    prefix = "lighthouse-auditor/prod"
  }
}
