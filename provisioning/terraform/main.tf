# =============================================================================
# mkt016 — From Question to Campaign (Cymbal Voyages). Start Lab provisioning.
# =============================================================================
# SHAPE COPIED FROM mkt015 (cymbalgoal-database-intelligence/terraform), which is
# proven at Start Lab: the three injected variables + `username`, the domain
# tolerance on username, runtime.yaml, the version pins, and the rule that every
# API string must be verified before it goes in (a bad one halts the room).
# The services are a straight translation of services/scripts/deploy_services.sh
# (tested Sep 19 in a Qwiklabs project; test_services.sh passed).
#
# ⚠️ DELTA FROM mkt015 — every difference listed so a diff is legible:
#   1. GONE  AlloyDB, network, PSA. No VPC anything. google-beta stays, but for
#            ONE resource only: google_project_service_identity (beta-only).
#   2. NEW   Brand corpus: a Discovery Engine data store (native resource) plus
#            ONE REST call, documents:import, through the hashicorp/http data
#            source (no curl/gcloud on the runner). There is no Terraform
#            resource for importing documents. This is the only non-native
#            step in the tree. It goes FIRST: the Layout Parser import takes
#            ~10 min (spike S8) and is the long pole of Start Lab.
#   3. NEW   google_discovery_engine_acl_config: identity provider = Google
#            Identity (idp_type GSUITE) at location global. Without it the
#            custom MCP data store wizard blocks ("You must configure your access
#            control settings"). Replaces a Task 0 click.
#   4. NEW   BigQuery warehouse: 15 tables created by google_bigquery_table
#            (schemas, descriptions, partitioning and clustering read at plan
#            time from gs://class-demo/.../schemas/, the frozen source of truth,
#            never a local copy), then ONE BigQuery script job that loads the
#            Parquet, trains the propensity model and re-scores customers.
#   5. NEW   Two Cloud Run services from public prebuilt images, min instances 1,
#            no unauthenticated access, run.invoker for the Discovery Engine
#            service agent. No builds at Start Lab.
#   6. NEW   The trimmed orchestrator agent card, written to gs://<project>-lab/.
#
# ⚠️ TWO THINGS FINISH AFTER `terraform apply` RETURNS — by design:
#   * the BigQuery script job (google_bigquery_job only waits for the job to
#     EXIST, not to finish; measured behaviour of the provider at 7.35.0), and
#   * the corpus import (a long-running operation; the http call only starts it).
# Nothing downstream in this file needs either to be finished: the services
# query BigQuery at call time. provisioning/check.sh reports both. "Everything
# ready" in the timing log means BOTH done, not the apply returning.
#
# WHAT THIS FILE DELIBERATELY DOES NOT DO (student steps, by design — plan §5):
#   * Create/activate the Gemini Enterprise app, feature toggles   -> Task 0
#   * Build the BigQuery data agent                                -> Task 1
#   * Create the Audience Tools custom MCP data store              -> Task 3
#   * Attach the brand corpus to the app                           -> Task 4
#   * Register the orchestrator by card                            -> Task 6
# The corpus data store is therefore created UNATTACHED: at Start Lab there is no
# app for it to be connected to, so Task 1's bare assistant cannot read it
# (plan decision 5 / R6). In the API an app's "connectors" are just the engine's
# dataStoreIds list; there is no separate per-connector "disabled" flag.
# =============================================================================

locals {
  project = var.gcp_project_id
  region  = var.gcp_region
  pn      = data.google_project.current.number

  student_email = can(regex("@", var.username)) ? var.username : "${var.username}@${var.student_email_domain}"

  dataset      = "cymbal_voyages"
  bq_location  = "US" # US multi-region, as in the spike and in tools.yaml
  data_uri     = "gs://${var.data_bucket}/${var.data_prefix}"
  schemas_path = "${var.data_prefix}/schemas"

  # Discovery Engine (Gemini Enterprise) service agent. Gemini Enterprise calls
  # both Cloud Run services with a Google-signed ID token as this identity.
  ge_agent = "service-${local.pn}@gcp-sa-discoveryengine.iam.gserviceaccount.com"

  toolbox_svc = "audience-tools"
  orch_svc    = "orchestrator"
  # Cloud Run URLs are deterministic, so the orchestrator can be told its own URL
  # on the first deploy (it writes it into the card it serves).
  orch_url = "https://${local.orch_svc}-${local.pn}.${local.region}.run.app"

  corpus_id   = "cymbal-voyages-brand-corpus"
  corpus_uris = ["${local.data_uri}/brand_corpus/*.pdf"]
}

data "google_project" "current" {
  project_id = var.gcp_project_id
}

data "google_client_config" "runner" {}

# =============================================================================
# 1. BRAND CORPUS — FIRST. The only thing on this path is the Discovery Engine
#    API enable and a short settle, so Terraform starts it in the first wave.
# =============================================================================
resource "google_project_service" "discoveryengine" {
  service            = "discoveryengine.googleapis.com"
  disable_on_destroy = false
}

# A freshly enabled API can answer SERVICE_DISABLED for a few seconds. 30 s is
# cheap insurance on the one path that must not fail and must not start late.
resource "time_sleep" "discoveryengine_settle" {
  depends_on      = [google_project_service.discoveryengine]
  create_duration = "30s"
}

resource "google_discovery_engine_data_store" "brand_corpus" {
  location                    = "global" # Gemini Enterprise's location in the spike
  data_store_id               = local.corpus_id
  display_name                = "Cymbal Voyages Brand Corpus"
  industry_vertical           = "GENERIC"
  content_config              = "CONTENT_REQUIRED" # unstructured documents
  solution_types              = ["SOLUTION_TYPE_SEARCH"]
  create_advanced_site_search = false

  # Layout Parser, as in the spike: 7 of the 12 PDFs rely on tables, including
  # the legal claims list that Task 4's banned-phrase beat depends on. Chunking
  # values are the console's defaults when "Layout parser" is chosen.
  document_processing_config {
    default_parsing_config {
      layout_parsing_config {}
    }
    chunking_config {
      layout_based_chunking_config {
        chunk_size                = 500
        include_ancestor_headings = true
      }
    }
  }

  depends_on = [time_sleep.discoveryengine_settle]
}

# -----------------------------------------------------------------------------
# 🔴 THE ONE NON-NATIVE STEP: start the import.
# -----------------------------------------------------------------------------
# POST .../dataStores/<id>/branches/default_branch/documents:import, reading the
# PDFs DIRECTLY from the class-demo bucket (no copy; the lab project's Discovery
# Engine service agent could read it in the spike). The response is a
# long-running operation; the import itself runs ~10 min AFTER this returns.
#
# Why the http data source: the runner may have no curl/gcloud for local-exec
# (never proven either way on the Qwiklabs runner). hashicorp/http is a normal
# provider download, like random. The bearer token is the runner's own.
#
# Behaviour to know:
#   * The data store's `name` is unknown until it exists, so this read is
#     deferred to apply time and runs right after the create. Good.
#   * Data sources are re-read on every plan/refresh. A second plan or a destroy
#     would POST the import again; with INCREMENTAL reconciliation that is a
#     harmless re-sync of the same 12 files.
#   * It waits for the Discovery Engine agent's storage grant (below): the
#     import creates a staging bucket in the project as that agent.
#   * retry covers 5xx/429 and connection errors (a store created seconds ago
#     can briefly 404/503). Any non-200 after that FAILS the apply on purpose:
#     an empty corpus is otherwise invisible until Task 4, an hour into the lab.
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# 🔴 MEASURED 2026-09-19 (first manual apply, fresh Qwiklabs project): the import
# 403'd with "service-PN@gcp-sa-discoveryengine... does not have
# storage.buckets.create ... buckets/PN_..._us_import_content". The Layout
# Parser import stages content in a bucket it creates IN THE LAB PROJECT, as the
# Discovery Engine service agent. The console flow (spike S8) evidently
# provisions that agent first; a bare API call does not wait for it. So:
#   service identity -> storage.admin on the project for the agent -> 60 s
#   IAM settle -> import.
# The data store create runs in parallel with that chain, so the import starts
# ~1.5 min into the apply instead of ~1 min.
# -----------------------------------------------------------------------------
resource "google_project_iam_member" "ge_agent_storage" {
  project    = local.project
  role       = "roles/storage.admin" # needs storage.buckets.create for the staging bucket
  member     = "serviceAccount:${local.ge_agent}"
  depends_on = [google_project_service_identity.discoveryengine]
}

resource "time_sleep" "ge_agent_settle" {
  depends_on      = [google_project_iam_member.ge_agent_storage]
  create_duration = "60s"
}

data "http" "corpus_import" {
  depends_on = [time_sleep.ge_agent_settle]

  url    = "https://discoveryengine.googleapis.com/v1/${google_discovery_engine_data_store.brand_corpus.name}/branches/default_branch/documents:import"
  method = "POST"

  request_headers = {
    Authorization         = sensitive("Bearer ${data.google_client_config.runner.access_token}") # keeps the token out of logs
    "Content-Type"        = "application/json"
    "X-Goog-User-Project" = local.project
  }

  request_body = jsonencode({
    gcsSource = {
      inputUris  = local.corpus_uris
      dataSchema = "content"
    }
    reconciliationMode = "INCREMENTAL"
  })

  retry {
    attempts     = 5
    min_delay_ms = 5000
    max_delay_ms = 20000
  }

  lifecycle {
    postcondition {
      condition     = self.status_code == 200
      error_message = "Brand corpus import did not start (HTTP ${self.status_code}): ${self.response_body}"
    }
  }
}

# =============================================================================
# 2. GEMINI ENTERPRISE IDENTITY PROVIDER = Google Identity
# =============================================================================
# Console: Gemini Enterprise → Settings → Authentication → global → Google
# Identity. API: projects.locations.updateAclConfig, idpConfig.idpType = GSUITE.
# Project-level setting per location, so it can be set before the student
# creates the app in Task 0. ⚠️ UNPROVEN until the first test run: (a) that it
# is accepted before Gemini Enterprise is activated, (b) that Task 0's
# activation does not reset it. If (a) fails, delete this block and restore the
# Task 0 step; it is the only thing that depends on nothing else.
resource "google_discovery_engine_acl_config" "google_identity" {
  location = "global"

  idp_config {
    idp_type = "GSUITE"
  }

  depends_on = [time_sleep.discoveryengine_settle]
}

# =============================================================================
# 3. APIs (everything except Discovery Engine, which is above)
# =============================================================================
# ⚠️ Every string is a real service name (handoff list, SC2's deploy script).
# Do not add from a console label; get it from `gcloud services list` first.
resource "google_project_service" "apis" {
  for_each = toset([
    "bigquery.googleapis.com",
    "bigqueryconnection.googleapis.com",   # handoff list; nothing here uses a connection. Trim candidate.
    "aiplatform.googleapis.com",           # model training/embeddings (Toolbox meaning match), Gemini for both services
    "geminidataanalytics.googleapis.com",  # Task 1 BigQuery data agent
    "cloudaicompanion.googleapis.com",     # Gemini in BigQuery (data agent authoring)
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",     # cross-project pull worked in the spike; kept so the pull never depends on it
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "serviceusage.googleapis.com",
    "storage.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
  ])
  service            = each.value
  disable_on_destroy = false
}

# =============================================================================
# 4. SERVICE IDENTITIES AND IAM
# =============================================================================
# Make the Discovery Engine service agent exist before anything binds it
# (= gcloud beta services identity create). ⚠️ google-beta: this resource is
# not registered in the GA provider at 7.35.0 (validate error, 2026-09-19).
resource "google_project_service_identity" "discoveryengine" {
  provider   = google-beta
  service    = "discoveryengine.googleapis.com"
  depends_on = [google_project_service.discoveryengine]
}

# The student (both partners share these credentials). Owner already covers
# these today; granted explicitly so no task depends on Owner implying them.
resource "google_project_iam_member" "student" {
  for_each = toset([
    "roles/geminidataanalytics.dataAgentCreator",
    "roles/geminidataanalytics.dataAgentUser",
    "roles/discoveryengine.admin",
  ])
  project = local.project
  role    = each.value
  member  = "user:${local.student_email}"
}

resource "google_service_account" "audience_tools" {
  account_id   = "audience-tools-sa"
  display_name = "Audience Tools (MCP Toolbox) runtime"
  depends_on   = [google_project_service.apis]
}

resource "google_service_account" "orchestrator" {
  account_id   = "orchestrator-sa"
  display_name = "Orchestrator (ADK, A2A) runtime"
  depends_on   = [google_project_service.apis]
}

# Roles exactly as deploy_services.sh grants them (docs/services.md Part 2).
resource "google_project_iam_member" "audience_tools" {
  for_each = toset([
    "roles/bigquery.jobUser",
    "roles/bigquery.dataViewer",
    "roles/bigquery.dataEditor",          # activate_segment MERGEs the receipt row
    "roles/secretmanager.secretAccessor", # tools.yaml
    "roles/aiplatform.user",              # meaning match embeds the hint with gemini-embedding-001
  ])
  project = local.project
  role    = each.value
  member  = "serviceAccount:${google_service_account.audience_tools.email}"
}

resource "google_project_iam_member" "orchestrator" {
  for_each = toset([
    "roles/bigquery.jobUser",
    "roles/bigquery.dataViewer", # reads the policy table; no write roles
    "roles/aiplatform.user",
  ])
  project = local.project
  role    = each.value
  member  = "serviceAccount:${google_service_account.orchestrator.email}"
}

# Cloud Run checks at deploy time that the runtime SA can read the mounted
# secret. Fresh grants take a few seconds to propagate; this sleep is off the
# corpus's critical path (it runs alongside the import and the BigQuery job).
# 🔴 MEASURED 2026-09-19: with a 30 s settle and only the project-level grant,
# audience-tools failed on first apply with "Error code 7 ... internal error"
# (gRPC 7 = PERMISSION_DENIED) while orchestrator (no secret) deployed fine.
# So: also grant accessor ON THE SECRET, and settle 60 s. Still off the
# corpus's critical path.
resource "google_secret_manager_secret_iam_member" "audience_tools" {
  secret_id = google_secret_manager_secret.tools.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.audience_tools.email}"
}

resource "time_sleep" "iam_settle" {
  depends_on = [
    google_project_iam_member.audience_tools,
    google_project_iam_member.orchestrator,
    google_secret_manager_secret_iam_member.audience_tools,
  ]
  create_duration = "60s"
}

# =============================================================================
# 5. BIGQUERY WAREHOUSE
# =============================================================================
# Table definitions come from the FROZEN bucket, read at plan time, not from a
# local copy: in the spike a stale local schemas/ applied old table
# descriptions, and one of them used to give the lab's answer away. The data
# agent reads these descriptions.
#
# If the runner cannot read class-demo, THIS is where the apply fails, at plan
# time, loudly — before anything is created. The same identity then runs the
# load job, so the read is needed anyway.
data "google_storage_bucket_object_content" "tables_index" {
  bucket = var.data_bucket
  name   = "${local.schemas_path}/_tables.json"
}

locals {
  tables_index = jsondecode(data.google_storage_bucket_object_content.tables_index.content)
  # `activations` is created empty from its schema (an empty Parquet file is a
  # load error); every other table is loaded.
  loaded_tables = sort([for t in keys(local.tables_index) : t if t != "activations"])
}

data "google_storage_bucket_object_content" "schema" {
  for_each = local.tables_index
  bucket   = var.data_bucket
  name     = "${local.schemas_path}/${each.key}.json"
}

resource "google_bigquery_dataset" "cv" {
  dataset_id                 = local.dataset
  location                   = local.bq_location
  description                = "Cymbal Voyages marketing warehouse (mkt016 From Question to Campaign)"
  delete_contents_on_destroy = true
  depends_on                 = [google_project_service.apis]
}

resource "google_bigquery_table" "t" {
  for_each            = local.tables_index
  dataset_id          = google_bigquery_dataset.cv.dataset_id
  table_id            = each.key
  description         = each.value.description
  deletion_protection = false

  # REQUIRED relaxed to NULLABLE, as sql/load.sh does: Parquet columns arrive as
  # OPTIONAL and a REQUIRED target column rejects them. REPEATED stays REPEATED
  # (enable_list_inference on the load).
  schema = jsonencode([
    for f in jsondecode(data.google_storage_bucket_object_content.schema[each.key].content) :
    merge(f, { mode = lookup(f, "mode", "NULLABLE") == "REQUIRED" ? "NULLABLE" : lookup(f, "mode", "NULLABLE") })
  ])

  dynamic "time_partitioning" {
    for_each = try(each.value.partition, null) == null ? [] : [each.value]
    content {
      type  = try(time_partitioning.value.partition_type, "DAY")
      field = time_partitioning.value.partition
    }
  }

  clustering = try(each.value.cluster, null)
}

# One script, sequential by construction: load every table into the tables
# above (their schemas and descriptions are kept; LOAD DATA INTO appends into an
# existing definition), then train (56 s measured) and re-score (the lab quotes
# post-scoring numbers: avg propensity 0.16, 10.3% >= 0.30).
# TRUNCATE first only so an instructor can re-run the SQL by hand safely.
locals {
  load_sql = join("\n", [
    for t in local.loaded_tables : <<-SQL
      TRUNCATE TABLE `${local.project}.${local.dataset}.${t}`;
      LOAD DATA INTO `${local.project}.${local.dataset}.${t}`
        FROM FILES (format = 'PARQUET', uris = ['${local.data_uri}/out/${t}/*.parquet'], enable_list_inference = true);
    SQL
  ])

  warehouse_sql = join("\n", [
    "-- mkt016 Start Lab: load, train, score. Generated by provisioning/terraform/main.tf.",
    local.load_sql,
    replace(file("${path.module}/files/train_propensity.sql"), "PROJECT_ID", local.project),
    replace(file("${path.module}/files/predict_propensity.sql"), "PROJECT_ID", local.project),
  ])
}

resource "random_id" "job" {
  byte_length = 4
}

resource "google_bigquery_job" "warehouse" {
  job_id   = "cv_warehouse_${random_id.job.hex}"
  location = local.bq_location
  labels   = { lab = "mkt016", step = "warehouse" }

  query {
    query          = local.warehouse_sql
    use_legacy_sql = false
    # A script with DDL/DML: the defaults (CREATE_IF_NEEDED / WRITE_EMPTY) are
    # invalid without a destination table, so both are blanked.
    create_disposition = ""
    write_disposition  = ""
  }

  depends_on = [google_bigquery_table.t]
}

# =============================================================================
# 6. CLOUD RUN SERVICES (reproduces services/scripts/deploy_services.sh)
# =============================================================================
resource "google_secret_manager_secret" "tools" {
  secret_id = "audience-tools-config"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

# services/toolbox/tools.yaml, UNCHANGED (copied into files/ by
# provisioning/sync.sh). It reads the project from the service's environment,
# so the file the Builder reads in Task 3 is byte-for-byte the mounted file.
resource "google_secret_manager_secret_version" "tools" {
  secret      = google_secret_manager_secret.tools.id
  secret_data = file("${path.module}/files/tools.yaml")
}

resource "google_cloud_run_v2_service" "audience_tools" {
  name                = local.toolbox_svc
  location            = local.region
  deletion_protection = false

  template {
    service_account = google_service_account.audience_tools.email

    scaling {
      min_instance_count = 1 # Patrick's rule: cold starts break connectors
    }

    containers {
      image = "${var.image_repo}/toolbox:${var.toolbox_tag}"
      args  = ["--tools-file=/secrets/tools.yaml", "--address=0.0.0.0", "--port=8080"]

      ports {
        container_port = 8080
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = local.project
      }

      volume_mounts {
        name       = "tools-config"
        mount_path = "/secrets"
      }
    }

    # = gcloud --set-secrets /secrets/tools.yaml=audience-tools-config:<version>
    volumes {
      name = "tools-config"
      secret {
        secret = google_secret_manager_secret.tools.secret_id
        items {
          version = google_secret_manager_secret_version.tools.version
          path    = "tools.yaml"
        }
      }
    }
  }

  depends_on = [google_project_service.apis, time_sleep.iam_settle]
}

resource "google_cloud_run_v2_service" "orchestrator" {
  name                = local.orch_svc
  location            = local.region
  deletion_protection = false

  template {
    service_account = google_service_account.orchestrator.email

    scaling {
      min_instance_count = 1
    }

    containers {
      image = "${var.image_repo}/orchestrator:${var.orchestrator_tag}"

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }

      dynamic "env" {
        for_each = {
          GOOGLE_CLOUD_PROJECT      = local.project
          GOOGLE_CLOUD_LOCATION     = "global" # Gemini 3.x 404s in us-central1
          GOOGLE_GENAI_USE_VERTEXAI = "TRUE"
          BQ_PROJECT                = local.project
          BQ_DATASET                = local.dataset
          ORCHESTRATOR_MODEL        = var.orchestrator_model
          AGENT_URL                 = local.orch_url
        }
        content {
          name  = env.key
          value = env.value
        }
      }
    }
  }

  depends_on = [google_project_service.apis, time_sleep.iam_settle]
}

# Gemini Enterprise calls both services as its service agent. No
# unauthenticated access anywhere (Cloud Run's default without an allUsers grant).
resource "google_cloud_run_v2_service_iam_member" "ge_invoker" {
  for_each = {
    audience_tools = google_cloud_run_v2_service.audience_tools.name
    orchestrator   = google_cloud_run_v2_service.orchestrator.name
  }
  name       = each.value
  location   = local.region
  role       = "roles/run.invoker"
  member     = "serviceAccount:${local.ge_agent}"
  depends_on = [google_project_service_identity.discoveryengine]
}

# =============================================================================
# 7. THE TRIMMED AGENT CARD (Task 6)
# =============================================================================
# Students never copy the served card (newer A2A format; Gemini Enterprise's
# "Custom agent via A2A" rejects it). They paste this one: the repo's
# agent.card.template.json with __AGENT_URL__ replaced, exactly as
# deploy_services.sh does with sed. It is also a Terraform output.
locals {
  orchestrator_card = replace(file("${path.module}/files/agent.card.template.json"), "__AGENT_URL__", local.orch_url)
}

resource "google_storage_bucket" "lab" {
  name                        = "${local.project}-lab"
  location                    = "US"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true
  depends_on                  = [google_project_service.apis]
}

resource "google_storage_bucket_object" "orchestrator_card" {
  bucket       = google_storage_bucket.lab.name
  name         = "orchestrator-card.json"
  content      = local.orchestrator_card
  content_type = "application/json"
}
