# Outputs. qwiklabs.yaml surfaces some of them to students as
# project_0.startup_script.<name>; the rest are for whoever reads the
# provisioning log. Names are referenced from qwiklabs.yaml — rename both together.

# ---- student-visible (templated into the lab text) --------------------------
output "audience_tools_mcp_url" {
  description = "Task 3: paste into Custom MCP server, authentication None."
  value       = "${google_cloud_run_v2_service.audience_tools.uri}/mcp"
}

output "orchestrator_url" {
  description = "Orchestrator service URL (the card's url is this + /a2a/orchestrator)."
  value       = google_cloud_run_v2_service.orchestrator.uri
}

output "orchestrator_card_object" {
  description = "Task 6: the trimmed card students paste into Custom agent via A2A."
  value       = "gs://${google_storage_bucket.lab.name}/${google_storage_bucket_object.orchestrator_card.name}"
}

output "orchestrator_card_json" {
  description = "The same trimmed card, inline."
  value       = local.orchestrator_card
}

output "dataset" {
  value = "${local.project}.${local.dataset}"
}

# ---- for the provisioning log / check.sh -------------------------------------
output "audience_tools_url" {
  value = google_cloud_run_v2_service.audience_tools.uri
}

output "orchestrator_url_expected" {
  description = "What AGENT_URL was set to. Must equal orchestrator_url; if not, the card points at the wrong host."
  value       = local.orch_url
}

output "lab_bucket" {
  value = google_storage_bucket.lab.name
}

output "brand_corpus_data_store" {
  description = "Created UNATTACHED to any app; Task 4 attaches it."
  value       = google_discovery_engine_data_store.brand_corpus.name
}

output "brand_corpus_import_operation" {
  description = "Long-running import (~10 min). check.sh polls it."
  value       = try(jsondecode(data.http.corpus_import.response_body).name, data.http.corpus_import.response_body)
}

output "identity_provider" {
  description = "Gemini Enterprise identity provider at location global. Expect GSUITE (console: Google Identity)."
  value       = google_discovery_engine_acl_config.google_identity.idp_config[0].idp_type
}

output "warehouse_job" {
  description = "BigQuery script job (load, train, score). Still running when apply returns: bq show -j <id>."
  value       = "${local.project}:${local.bq_location}.${google_bigquery_job.warehouse.job_id}"
}

output "apply_started_at" {
  description = "Plan timestamp, for the timing log."
  value       = plantimestamp()
}
