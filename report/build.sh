#!/usr/bin/env bash
# Build the report with XeLaTeX (Traditional Chinese via Noto CJK TC).
# TinyTeX is user-local; this script puts it on PATH and runs latexmk.
set -e
cd "$(dirname "$0")"
export PATH="$HOME/.TinyTeX/bin/x86_64-linux:$PATH"
latexmk -xelatex -interaction=nonstopmode main.tex
echo "---- built: $(pwd)/main.pdf ($(pdfinfo main.pdf 2>/dev/null | awk '/Pages/{print $2" pages"}')) ----"
