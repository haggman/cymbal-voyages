# Version pins.
#
# Terraform 1.12.1 and google 7.35.0 are carried from mkt013–mkt015, all proven
# at Start Lab. Do not float them.
#
# DELTA FROM mkt015:
#   * GONE google-beta. Nothing here needs it. Every Discovery Engine resource
#     used (data_store, acl_config) and google_project_service_identity are in
#     the GA provider at 7.35.0 (read from the source at that tag, 2026-09-19).
#   * NEW  hashicorp/http. Used by exactly ONE data source: the brand-corpus
#     documents:import call. There is no Terraform resource for importing
#     documents into a data store. See "BRAND CORPUS" in main.tf.
#   * NEW  hashicorp/time. Two time_sleep resources that absorb API-enable and
#     IAM propagation. Both are off the corpus's critical path except the first.

terraform {
  required_version = ">= 1.12.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "7.35.0"
    }
    http = {
      source  = "hashicorp/http"
      version = "3.5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "3.7.2"
    }
    time = {
      source  = "hashicorp/time"
      version = "0.13.1"
    }
  }
}
