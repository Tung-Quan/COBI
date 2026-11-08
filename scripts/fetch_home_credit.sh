#!/usr/bin/env bash
set -euo pipefail
if [[ "$#" != 1 || "$1" != "--accepted-kaggle-rules" ]]; then
    echo "DOWNLOAD_NOT_AUTHORIZED: accept the Home Credit competition rules on Kaggle first." >&2
    exit 2
fi
cd "$(dirname "$0")/.."
kaggle competitions download -c home-credit-default-risk -p data/raw/home_credit
echo "Archive downloaded subject to Kaggle terms. Review provenance, labels and as-of joins before use."
