"""Download the large ML model weights that are intentionally NOT stored in git.

The three .pkl model files are hundreds of MB, so they live in external storage
(S3 / GCS / Google Drive / etc.) instead of the repository. This script fetches
any that are missing into backend/app/ml/models/.

Usage (from the backend/ directory):
    # Point at the folder/bucket that hosts the .pkl files:
    MODELS_BASE_URL="https://your-storage.example.com/zonalyze-models" \
        python -m app.scripts.fetch_models

Each model is downloaded from  <MODELS_BASE_URL>/<filename> .
Files that already exist are skipped, so it is safe to re-run.
"""
from __future__ import annotations

import os
import sys
import urllib.request
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parents[1] / "ml" / "models"

# The small feature_columns.json / model_metadata.json are tracked in git; only
# the large weight files need downloading.
MODEL_FILES = [
    "risk_classifier.pkl",
    "revenue_regressor.pkl",
    "feasibility_regressor.pkl",
]


def main() -> int:
    base_url = os.getenv("MODELS_BASE_URL", "").strip().rstrip("/")
    if not base_url:
        print(
            "ERROR: MODELS_BASE_URL is not set.\n"
            "Set it to the storage location that hosts the model .pkl files, e.g.\n"
            '  MODELS_BASE_URL="https://your-storage/zonalyze-models" '
            "python -m app.scripts.fetch_models",
            file=sys.stderr,
        )
        return 1

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    for name in MODEL_FILES:
        target = MODELS_DIR / name
        if target.exists():
            print(f"skip  {name} (already present)")
            continue
        url = f"{base_url}/{name}"
        print(f"fetch {name} <- {url}")
        try:
            urllib.request.urlretrieve(url, target)  # noqa: S310 (trusted, operator-provided URL)
        except Exception as exc:  # pragma: no cover
            print(f"ERROR downloading {name}: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 2

    print(f"Done. Models are in {MODELS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
