terraform {
  backend "gcs" {
    bucket = "asp-e2e-cicd-terraform-state"
    prefix = "cloudbuild"
  }
}
