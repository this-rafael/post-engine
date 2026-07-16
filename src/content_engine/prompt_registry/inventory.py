"""Inventario versionado das fontes de prompt encontradas na migracao."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INVENTORY_PATH = PROJECT_ROOT / "docs" / "prompt-registry-inventory.json"


def build_inventory(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_classification: dict[str, int] = {}
    for record in records:
        label = str(record.get("classification", "UNKNOWN"))
        by_classification[label] = by_classification.get(label, 0) + 1
    return {
        "schema_version": 1,
        "generated_by": "content_engine.prompt_registry.importer",
        "summary": {"total": len(records), "by_classification": by_classification},
        "items": records,
    }


def write_inventory(records: list[dict[str, Any]], path: str | Path | None = None) -> Path:
    target = Path(path) if path is not None else DEFAULT_INVENTORY_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(build_inventory(records), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


__all__ = ["DEFAULT_INVENTORY_PATH", "build_inventory", "write_inventory"]
