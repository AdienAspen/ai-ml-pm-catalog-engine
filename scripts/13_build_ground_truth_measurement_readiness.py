from __future__ import annotations

import json
from pathlib import Path
import sys


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root / "src"))

    from asset_ml_feasibility.reports.ground_truth_measurement_readiness import build_section

    summary = build_section(project_root)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
