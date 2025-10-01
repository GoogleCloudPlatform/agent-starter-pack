terraform {
  backend "gcs" {
    bucket = "agent-starter-pack-cicd-terraform-state"
    prefix = "cloudbuild"
  }
}
