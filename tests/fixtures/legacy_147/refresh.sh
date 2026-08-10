#!/usr/bin/env bash
set -euo pipefail
REF="${1:-1.47_release}"
DIR="$(cd "$(dirname "$0")" && pwd)"
shopt -s nullglob
for f in dispatch.py convert_to_*.py edi_tweaks.py; do
    # Skip a stray literal filename like "convert_to_*.py" that may have
    # been created on disk and would otherwise match the glob above.
    case "$f" in
        dispatch.py|edi_tweaks.py) ;;
        *) case "$f" in \*|*\**) continue ;; esac ;;
    esac
    git show "$REF:$f" > "$DIR/$f"
done
echo "Refreshed $DIR from $REF"
