#!/usr/bin/env bash
set -euo pipefail
REF="${1:-1.47_release}"
DIR="$(cd "$(dirname "$0")" && pwd)"
for f in dispatch.py convert_to_*.py edi_tweaks.py; do
    git show "$REF:$f" > "$DIR/$f"
done
echo "Refreshed $DIR from $REF"
