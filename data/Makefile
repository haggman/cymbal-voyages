# Cymbal Voyages data foundation (mkt016). `make` goes from nothing to out/, schemas/ and docs/.
PY ?= python3
PROJECT_ID ?= $(shell gcloud config get-value project 2>/dev/null)
BUCKET ?= class-demo
PREFIX ?= cymbal-voyages/v1

.PHONY: all setup generate verify docs pdfs embeddings stage load clean

all: generate verify docs

setup:
	$(PY) -m pip install -r requirements.txt

generate:            ## write out/<table>/part-*.parquet, schemas/*.json, out/_manifest.json
	$(PY) generate_warehouse.py

verify:              ## run the walkthrough queries locally (DuckDB) and print the tables
	$(PY) sql/verify_local.py

docs:                ## regenerate docs/anomaly-walkthrough.md and docs/data-dictionary.md from the data
	$(PY) sql/verify_local.py --write
	$(PY) sql/build_dictionary.py

pdfs:                ## render brand_corpus/*.md to brand_corpus/pdf/*.pdf
	./brand_corpus/build_pdfs.sh

embeddings:          ## needs PROJECT_ID and Vertex AI access; writes out/catalog_embeddings/
	PROJECT_ID=$(PROJECT_ID) $(PY) embeddings/build_embeddings.py

stage:               ## copy out/, schemas/ and the PDFs to gs://$(BUCKET)/$(PREFIX)/  (see docs/staging.md)
	gcloud storage rsync --recursive --delete-unmatched-destination-objects out gs://$(BUCKET)/$(PREFIX)/out
	gcloud storage rsync --recursive schemas gs://$(BUCKET)/$(PREFIX)/schemas
	gcloud storage rsync --recursive brand_corpus/pdf gs://$(BUCKET)/$(PREFIX)/brand_corpus

load:                ## bq load everything into $(PROJECT_ID):cymbal_voyages
	PROJECT_ID=$(PROJECT_ID) BUCKET=$(BUCKET) PREFIX=$(PREFIX) ./sql/load.sh

clean:
	rm -rf out schemas brand_corpus/pdf
