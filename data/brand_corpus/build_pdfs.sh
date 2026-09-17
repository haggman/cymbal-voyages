#!/usr/bin/env bash
# Render every brand_corpus/*.md to brand_corpus/pdf/*.pdf. Markdown stays the source of truth;
# the PDFs are what the Gemini Enterprise Cloud Storage data store indexes.
#
# Needs pandoc plus one PDF engine: wkhtmltopdf (preferred, used here) or a LaTeX install.
#   macOS:  brew install pandoc wkhtmltopdf      Debian/Ubuntu: apt-get install pandoc wkhtmltopdf
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p pdf
command -v pandoc >/dev/null || { echo "pandoc not found" >&2; exit 1; }
if command -v wkhtmltopdf >/dev/null; then
  ENGINE=(--pdf-engine=wkhtmltopdf --pdf-engine-opt=--enable-local-file-access -V margin-top=18mm -V margin-bottom=18mm -V margin-left=18mm -V margin-right=18mm)
else
  echo "wkhtmltopdf not found; falling back to pandoc's default PDF engine (needs LaTeX)" >&2
  ENGINE=(-V geometry:margin=18mm)
fi
for md in [0-9][0-9]-*.md; do
  out="pdf/${md%.md}.pdf"
  title=$(sed -n 's/^# //p' "$md" | head -1)
  pandoc "$md" -o "$out" --from gfm --css style.css --metadata pagetitle="$title" "${ENGINE[@]}" 2>/dev/null \
    || pandoc "$md" -o "$out" --from gfm --css style.css --metadata pagetitle="$title" "${ENGINE[@]}"
  echo "· $out"
done
echo "$(ls pdf/*.pdf | wc -l | tr -d ' ') PDFs in brand_corpus/pdf/"
