#!/usr/bin/env bash
set -euo pipefail

repository_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
verification_environment=$(mktemp -d /tmp/fsair-verification.XXXXXX)

cleanup() {
    if [[ $verification_environment == /tmp/fsair-verification.* && -d $verification_environment ]]; then
        rm -rf -- "$verification_environment"
    fi
}
trap cleanup EXIT

cd "$repository_root"

/usr/bin/python3 -c \
    'import sys; assert sys.version_info[:2] == (3, 12), "CPython 3.12 is required"'
/usr/bin/python3 -m venv "$verification_environment"

python="$verification_environment/bin/python"
"$python" -m pip install --upgrade "pip==26.2.1"
"$python" -m pip install -r requirements.txt -c constraints-py312.txt
"$python" -m pip check
"$python" --version
"$python" -m pip list --format=freeze
"$python" -m pytest -ra
