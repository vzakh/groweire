"""Write backend/openapi.json: half of the Backend -> Frontend contract (plan 20 task 27).

make openapi
"""

from __future__ import annotations

import json
import sys

from core.config import REPO_ROOT
from main import create_app

OUT = REPO_ROOT / "backend" / "openapi.json"


def main() -> int:
    schema = create_app().openapi()
    OUT.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO_ROOT)} ({len(schema['paths'])} paths)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
