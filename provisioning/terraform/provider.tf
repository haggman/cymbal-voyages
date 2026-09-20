provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
  zone    = var.gcp_zone
}

# ⚠️ Used by exactly one resource: google_project_service_identity.discoveryengine
# (beta-only at 7.35.0; see versions.tf).
provider "google-beta" {
  project = var.gcp_project_id
  region  = var.gcp_region
  zone    = var.gcp_zone
}
