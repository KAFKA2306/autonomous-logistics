#!/usr/bin/env python3
"""Verify the reviewed FAA Part 135 package-delivery registry against the current FAA page."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

PAGE = "https://www.faa.gov/uas/advanced_operations/package_delivery_drone"
ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "faa-package-delivery-operators.json"


def fetch() -> bytes:
    request = Request(PAGE, headers={"User-Agent": "autonomous-logistics/1.0 github.com/KAFKA2306/autonomous-logistics"})
    with urlopen(request, timeout=60) as response:
        return response.read()


def visible_text(raw: bytes) -> str:
    html = raw.decode("utf-8", errors="replace")
    html = re.sub(r"<script\b[^>]*>.*?</script>", " ", html, flags=re.I | re.S)
    html = re.sub(r"<style\b[^>]*>.*?</style>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", html)
    return " ".join(text.split())


def verify(registry: dict[str, object], raw: bytes) -> dict[str, object]:
    text = visible_text(raw).lower()
    missing = []
    for row in registry.get("operators", []):
        name = str(row["operator"])
        candidates = {name.lower()}
        if " (dexa)" in name.lower():
            candidates.add(name.lower().replace(" (dexa)", ""))
        if not any(candidate in text for candidate in candidates):
            missing.append(name)
    if missing:
        raise ValueError(f"FAA source no longer contains reviewed operators: {missing}")
    return {
        "schema_version": 1,
        "source_url": PAGE,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "operator_count": len(registry.get("operators", [])),
        "operators": registry.get("operators", []),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--output", type=Path, default=Path("output/faa-package-delivery-operators.json"))
    args = parser.parse_args()
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    result = verify(registry, fetch())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"verified {result['operator_count']} FAA operators -> {args.output}")


if __name__ == "__main__":
    main()
