#!/usr/bin/env python3
"""Build autonomous-logistics evidence from FAA and operator primary sources."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import time
import urllib.error
import urllib.request
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DEFAULT_REGISTRY = ROOT / "data" / "registry.json"
DEFAULT_DATA_ROOT = ROOT / "data" / "autonomous-logistics"
DEFAULT_API_DIR = ROOT / "api" / "v1" / "autonomous-logistics"
ALLOWED_STATUSES = {"regulatory_authorization", "testing", "supervised", "commercial_driverless"}
USER_AGENT = "KAFKA2306 autonomous-logistics 137051370+KAFKA2306@users.noreply.github.com"


def dump(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def normalized_text(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace")
    text = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return " ".join(html.unescape(text).split())


def fetch_source(source: dict[str, Any], data_root: Path) -> dict[str, Any]:
    source_id = str(source["source_id"])
    url = str(source["source_url"])
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"},
    )
    last_error: Exception | None = None
    raw = b""
    content_type = "application/octet-stream"
    for attempt in range(1, 4):
        try:
            print(f"fetch {source_id} attempt {attempt}/3: {url}", flush=True)
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
                content_type = response.headers.get_content_type()
            break
        except (TimeoutError, urllib.error.URLError) as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(attempt)
    else:
        raise RuntimeError(f"primary source unavailable after 3 attempts: {source_id} {url}") from last_error
    if len(raw) < 1000:
        raise ValueError(f"primary source unexpectedly small: {source_id} {url}")
    text = normalized_text(raw)
    missing = [marker for marker in source.get("required_markers", []) if marker.lower() not in text.lower()]
    if missing:
        raise ValueError(f"primary source markers missing for {source_id}: {missing}")
    digest = sha256(raw)
    objects = data_root / "raw" / "objects"
    objects.mkdir(parents=True, exist_ok=True)
    suffix = ".html" if content_type in {"text/html", "application/xhtml+xml"} else ".bin"
    path = objects / f"{digest}{suffix}"
    if not path.exists():
        path.write_bytes(raw)
    return {
        "source_id": source_id,
        "authority": source["authority"],
        "source_url": url,
        "sha256": digest,
        "size_bytes": len(raw),
        "content_type": content_type,
        "evidence_path": path.relative_to(data_root).as_posix(),
        "verified_markers": source.get("required_markers", []),
    }


def validate_registry(registry: dict[str, Any]) -> None:
    sources = {str(row["source_id"]): row for row in registry.get("sources", [])}
    if len(sources) != len(registry.get("sources", [])) or len(sources) < 4:
        raise ValueError("source registry is incomplete or duplicated")
    drones = registry.get("drone_part135") or []
    if len(drones) != 7:
        raise ValueError(f"FAA Part 135 operator registry must contain 7 current operators, got {len(drones)}")
    if len({row["operator_id"] for row in drones}) != len(drones):
        raise ValueError("duplicate drone operator_id")
    for row in drones:
        if row.get("operation_status") != "regulatory_authorization":
            raise ValueError("FAA Part 135 registry entries must not be promoted to commercial operation facts")
        if row.get("current_faa_registry_status") != "listed":
            raise ValueError("all canonical drone entries must be current FAA listed operators")
        if not row.get("part135_certificate_date") or not row.get("permission"):
            raise ValueError(f"incomplete FAA authorization record: {row.get('operator_id')}")
        if row.get("operating_area") is None and row.get("operating_area_status") != "not_listed_on_current_faa_page":
            raise ValueError("missing operating area must carry an explicit source limitation")
        if row.get("source_id") not in sources:
            raise ValueError("drone record refers to unknown source")
    trucking = registry.get("trucking_operators") or []
    if len(trucking) < 3:
        raise ValueError("at least three autonomous trucking operators are required")
    if len({row["operator_id"] for row in trucking}) != len(trucking):
        raise ValueError("duplicate trucking operator_id")
    for row in trucking:
        status = row.get("operation_status")
        if status not in ALLOWED_STATUSES:
            raise ValueError(f"unsupported trucking status: {status}")
        if status == "commercial_driverless":
            if row.get("commercial") is not True or row.get("human_driver_in_cab") is not False:
                raise ValueError(f"commercial driverless record is internally inconsistent: {row['operator_id']}")
        if not row.get("geography") or row.get("source_id") not in sources:
            raise ValueError(f"trucking record lacks geography/source: {row.get('operator_id')}")
    events = registry.get("operation_events") or []
    if not events:
        raise ValueError("operation event table is empty")
    if not any(date.fromisoformat(row["effective_at"]).year >= 2024 for row in events):
        raise ValueError("operation events must include 2024+ evidence")
    for row in events:
        if row.get("operation_status") not in ALLOWED_STATUSES:
            raise ValueError(f"event has unsupported operation status: {row}")
        if row.get("source_id") not in sources:
            raise ValueError("event refers to unknown source")


def verify_manifest(data_root: Path) -> dict[str, Any]:
    manifest = json.loads((data_root / "raw" / "latest-manifest.json").read_text())
    for row in manifest["sources"]:
        path = data_root / row["evidence_path"]
        raw = path.read_bytes()
        if sha256(raw) != row["sha256"]:
            raise ValueError(f"raw source hash mismatch: {row['source_id']}")
    return manifest


def enrich_records(records: list[dict[str, Any]], source_map: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for source in records:
        evidence = source_map[str(source["source_id"])]
        out.append({
            **source,
            "source_url": evidence["source_url"],
            "source_sha256": evidence["sha256"],
            "source_evidence_path": evidence["evidence_path"],
        })
    return out


def build_api(registry: dict[str, Any], manifest: dict[str, Any], api_dir: Path) -> dict[str, Any]:
    source_map = {row["source_id"]: row for row in manifest["sources"]}
    drones = enrich_records(registry["drone_part135"], source_map)
    trucking = enrich_records(registry["trucking_operators"], source_map)
    events = enrich_records(registry["operation_events"], source_map)
    api_dir.mkdir(parents=True, exist_ok=True)
    (api_dir / "drone-part135.json").write_bytes(dump({"schema_version": 1, "records": drones}))
    (api_dir / "trucking.json").write_bytes(dump({"schema_version": 1, "records": trucking}))
    (api_dir / "events.json").write_bytes(dump({"schema_version": 1, "records": events}))
    (api_dir / "provenance.json").write_bytes(dump(manifest))
    (api_dir / "registry.json").write_bytes(dump(registry))
    event_dates = [date.fromisoformat(row["effective_at"]) for row in events]
    coverage = {
        "faa_part135_operator_count": len(drones),
        "autonomous_trucking_operator_count": len(trucking),
        "commercial_driverless_trucking_operator_count": sum(row["operation_status"] == "commercial_driverless" for row in trucking),
        "operation_event_count": len(events),
        "operation_event_first_date": min(event_dates).isoformat(),
        "operation_event_last_date": max(event_dates).isoformat(),
        "events_2024_or_later": sum(row_date.year >= 2024 for row_date in event_dates),
        "primary_source_count": len(manifest["sources"]),
        "raw_evidence_count": len(manifest["sources"]),
    }
    index = {
        "schema_version": 1,
        "dataset": "Autonomous logistics primary evidence",
        "retrieved_at": manifest["retrieved_at"],
        "coverage": coverage,
        "views": {
            "drone_part135": "drone-part135.json",
            "trucking": "trucking.json",
            "events": "events.json",
            "registry": "registry.json",
            "provenance": "provenance.json",
        },
        "rules": registry["rules"],
    }
    (api_dir / "index.json").write_bytes(dump(index))
    return index


def collect(registry: dict[str, Any], data_root: Path) -> dict[str, Any]:
    retrieved_at = datetime.now(UTC).isoformat()
    source_evidence = [fetch_source(row, data_root) for row in registry["sources"]]
    manifest = {
        "schema_version": 1,
        "retrieved_at": retrieved_at,
        "sources": source_evidence,
    }
    raw = dump(manifest)
    manifests = data_root / "raw" / "manifests"
    manifests.mkdir(parents=True, exist_ok=True)
    digest = sha256(raw)
    (manifests / f"{digest}.json").write_bytes(raw)
    (data_root / "raw" / "latest-manifest.json").write_bytes(raw)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--api-dir", type=Path, default=DEFAULT_API_DIR)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    registry = json.loads(args.registry.read_text())
    validate_registry(registry)
    manifest = verify_manifest(args.data_root) if args.offline else collect(registry, args.data_root)
    index = build_api(registry, manifest, args.api_dir)
    print(json.dumps(index["coverage"], sort_keys=True))


if __name__ == "__main__":
    main()
