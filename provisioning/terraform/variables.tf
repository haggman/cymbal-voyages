# Variables the Qwiklabs runtime injects at Start Lab time.
#
# ⚠️ RULE (carried from mkt015): every variable here must be one the platform
# actually supplies, under the exact name the platform uses. A required variable
# the runtime does not know about fails the apply — for every student at once.
#
# MEASURED on mkt013–mkt015 (live Start Lab log, 2026-08-18), the ENTIRE command line is:
#   terraform apply -var gcp_project_id=... -var gcp_zone=... -var gcp_region=... -auto-approve
# Three variables. Everything else arrives only because qwiklabs.yaml declares it
# under startup_script.custom_properties (here: username).

variable "gcp_project_id" {
  description = "Project the lab platform provisions for the student (shared by both partners of a pair)."
  type        = string
}

variable "gcp_region" {
  description = <<-EOT
    Region for the Cloud Run services. Constrained to us-central1:
      * the two images live in us-central1-docker.pkg.dev/class-demo-labs (pull is
        cross-region-capable, but only us-central1 was tested);
      * tools.yaml pins the embedding model to Vertex AI us-central1;
      * every number in the lab was produced with the services in us-central1.
    Gemini 3.x itself is served from `global` (GOOGLE_CLOUD_LOCATION on the
    orchestrator), and the BigQuery dataset is the US multi-region; neither
    depends on this variable.
  EOT
  type        = string
  default     = "us-central1"

  validation {
    condition     = var.gcp_region == "us-central1"
    error_message = "Region must be us-central1 (the only region the services and images were tested in)."
  }
}

variable "gcp_zone" {
  description = "Injected by Qwiklabs. Nothing consumes it (no VMs); declared so the apply accepts it."
  type        = string
  default     = "us-central1-a"
}

# -----------------------------------------------------------------------------
# username — same handling as mkt013–mkt015.
# -----------------------------------------------------------------------------
# LOCAL PART ONLY ("student-03-abc123") when qwiklabs.yaml passes
# user_0.local_username; FULL ADDRESS when it passes user_0.username. main.tf
# appends the domain only when it is absent, so either reference works.
#
# What it is used for here: three explicit role grants to the student
# (geminidataanalytics.dataAgentCreator / dataAgentUser, discoveryengine.admin)
# so no task depends on Owner implying them. A wrong value fails the IAM grant
# LOUDLY at apply time (unknown user) — unlike mkt015, there is no silent mode.
# -----------------------------------------------------------------------------
variable "username" {
  description = <<-EOT
    The student's lab username, either "student-03-abc123" (user_0.local_username)
    or "student-03-abc123@qwiklabs.net" (user_0.username).
    ⚠️ NOT injected automatically; arrives only via startup_script.custom_properties.
    Do NOT use data.google_client_openid_userinfo — that is the runner, not the student.
  EOT
  type        = string

  validation {
    condition     = length(regexall("@", var.username)) <= 1 && length(trimspace(var.username)) > 0
    error_message = "username must be the local part (student-03-abc123) or one full address (student-03-abc123@qwiklabs.net)."
  }
}

variable "student_email_domain" {
  description = "Domain appended to var.username when it has none. A variable only so the config can be applied by hand in a personal project."
  type        = string
  default     = "qwiklabs.net"
}

# ---------------------------------------------------------------------------
# Tunables — not injected by the platform; the defaults ARE the shipped lab.
# ---------------------------------------------------------------------------

variable "data_bucket" {
  description = "Bucket holding the frozen lab data. Regenerated data goes to a NEW prefix (v2), never over v1."
  type        = string
  default     = "class-demo"
}

variable "data_prefix" {
  description = "Prefix under data_bucket: out/<table>/*.parquet, schemas/<table>.json, brand_corpus/*.pdf."
  type        = string
  default     = "cymbal-voyages/v1"
}

variable "image_repo" {
  description = "Public-read Artifact Registry repo the lab images are pulled from (no grant needed)."
  type        = string
  default     = "us-central1-docker.pkg.dev/class-demo-labs/cymbal-voyages"
}

variable "toolbox_tag" {
  description = "MCP Toolbox for Databases mirror tag. Pinned; never latest."
  type        = string
  default     = "1.12.0"
}

variable "orchestrator_tag" {
  description = "Orchestrator image tag. Pinned; never latest. 1.0.1 (Sep 19) = 1.0.0 + exponential backoff on Gemini calls (429s seen on a busy night)."
  type        = string
  default     = "1.0.1"
}

variable "orchestrator_model" {
  description = "Model the orchestrator uses to explain decisions (served from the global location)."
  type        = string
  default     = "gemini-3.5-flash"
}
