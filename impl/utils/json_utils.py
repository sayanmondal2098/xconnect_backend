from __future__ import annotations

import json
from typing import Any, Dict


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def loads(s: str) -> Any:
    return json.loads(s or "{}")
