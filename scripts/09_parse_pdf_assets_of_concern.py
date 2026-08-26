"""Parse PDF Assets of Concern tables with sanitized versioned outputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from asset_ml_feasibility.parsers.pdf_assets_of_concern import run


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    summary = run(limit=args.limit, verify_only=args.verify_only)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
