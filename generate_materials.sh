#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ -n "${CHEMDB_PYTHON:-}" ]]; then
  interpreter="$CHEMDB_PYTHON"
elif [[ -x /home/mytu/Software/miniforge3/envs/drug_info/bin/python ]]; then
  interpreter=/home/mytu/Software/miniforge3/envs/drug_info/bin/python
else
  interpreter=python3
fi
exec "$interpreter" tools/generate_materials.py "$@"
