
data "google_project" "cicd_project" {
  project_id = var.cicd_runner_project_id
}

resource "google_service_account_iam_member" "github_oidc_access" {
  service_account_id = resource.google_service_account.cicd_runner_sa.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/projects/${data.google_project.cicd_project.number}/locations/global/workloadIdentityPools/${google_iam_workload_identity_pool.github_pool.workload_identity_pool_id}/attribute.repository/${var.repository_owner}/${var.repository_name}"
  depends_on         = [resource.google_project_service.cicd_services, resource.google_project_service.deploy_project_services]
}

# Allow the GitHub Actions principal to impersonate the CICD runner service account
resource "google_service_account_iam_member" "github_sa_impersonation" {
  service_account_id = resource.google_service_account.cicd_runner_sa.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "principalSet://iam.googleapis.com/projects/${data.google_project.cicd_project.number}/locations/global/workloadIdentityPools/${google_iam_workload_identity_pool.github_pool.workload_identity_pool_id}/attribute.repository/${var.repository_owner}/${var.repository_name}"
  depends_on         = [resource.google_project_service.cicd_services, resource.google_project_service.deploy_project_services]
}

resource "google_iam_workload_identity_pool" "github_pool" {
  workload_identity_pool_id = "${var.project_name}-pool"
  project                   = var.cicd_runner_project_id
  display_name              = "GitHub Actions Pool"
  depends_on         = [resource.google_project_service.cicd_services, resource.google_project_service.deploy_project_services]
}

resource "google_iam_workload_identity_pool_provider" "github_provider" {
  workload_identity_pool_provider_id = "${var.project_name}-oidc"
  project                            = var.cicd_runner_project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github_pool.workload_identity_pool_id
  display_name                       = "GitHub OIDC Provider"
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
  attribute_mapping = {
    "google.subject"         = "assertion.sub"
    "attribute.repository"       = "assertion.repository"
    "attribute.repository_owner" = "assertion.repository_owner"
  }
  attribute_condition = "attribute.repository == '${var.repository_owner}/${var.repository_name}'"
  depends_on          = [resource.google_project_service.cicd_services, resource.google_project_service.deploy_project_services]
}
