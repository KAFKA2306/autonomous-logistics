#!/usr/bin/env python3
"""Build autonomous-logistics evidence from FAA and operator primary sources."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
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
ALLOWED_STATUSES = {"regulatory_authorization", "testing", "supervised", "commercial", "commercial_driverless"}
USER_AGENT = "KAFKA2306 autonomous-logistics 137051370+KAFKA2306@users.noreply.github.com"
GATIK_LIVE_HEADER = "Truck Start Time End Time Driving Time Stops Status"
GATIK_LIVE_TIME_ZONE = "Pacific Standard Time (PST)"
GATIK_LIVE_STOPS_VALUES = ("Completed", "Unloading", "Driving", "Loading", "Parked")
GATIK_LIVE_STATUS_VALUES = ("On Time", "Completed", "Ready")
FAA_PART135_SOURCE_ID = "faa-part135-package-delivery"


def dump(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def normalized_text(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace")
    text = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return " ".join(html.unescape(text).split())


def parse_gatik_live_operations(text: str) -> dict[str, Any]:
    if GATIK_LIVE_TIME_ZONE not in text:
        raise ValueError("Gatik Live Operations time zone marker is missing")
    if GATIK_LIVE_HEADER not in text:
        raise ValueError("Gatik Live Operations columns are missing or reordered")
    if "Load more" not in text:
        raise ValueError("Gatik Live Operations completeness boundary is missing")

    body = text.split(GATIK_LIVE_HEADER, 1)[1].split("Load more", 1)[0].strip()
    row_pattern = re.compile(
        r"(G-\d{3}A)\s+"
        r"(\d{1,2}:\d{2}\s+[AP]M)\s+"
        r"(\d{1,2}:\d{2}\s+[AP]M)\s+"
        r"(\d+(?::\d{2})?\s+hrs)\s+"
        r"(.+?)(?=\s+G-\d{3}A\s+|$)"
    )
    matches = list(row_pattern.finditer(body))
    if not matches:
        raise ValueError("Gatik Live Operations has no parseable displayed rows")

    uncovered = []
    cursor = 0
    for match in matches:
        uncovered.append(body[cursor:match.start()].strip())
        cursor = match.end()
    uncovered.append(body[cursor:].strip())
    if any(uncovered):
        raise ValueError("Gatik Live Operations row structure changed or a truck ID is missing")

    records = []
    seen_truck_ids: set[str] = set()
    for match in matches:
        truck_id, start_time, end_time, driving_time, tail = match.groups()
        if truck_id in seen_truck_ids:
            raise ValueError(f"duplicate displayed Gatik truck label: {truck_id}")
        seen_truck_ids.add(truck_id)

        status = next(
            (value for value in GATIK_LIVE_STATUS_VALUES if tail == value or tail.endswith(f" {value}")),
            None,
        )
        if status is None:
            raise ValueError(f"unrecognized Gatik status value in displayed row: {truck_id}")
        stops = tail[: -len(status)].strip()
        if stops not in GATIK_LIVE_STOPS_VALUES:
            raise ValueError(f"unrecognized Gatik Stops value in displayed row: {truck_id}")
        records.append(
            {
                "truck_label": truck_id,
                "start_time": start_time,
                "end_time": end_time,
                "driving_time": driving_time,
                "stops": stops,
                "status": status,
            }
        )

    return {
        "time_zone_display": GATIK_LIVE_TIME_ZONE,
        "refresh_interval_hours": 3,
        "displayed_rows_complete": False,
        "displayed_row_count": len(records),
        "records": records,
    }


def fetch_source(source: dict[str, Any], data_root: Path) -> dict[str, Any]:
    source_id = str(source["source_id"])
    url = str(source["source_url"])
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
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
    evidence = {
        "source_id": source_id,
        "authority": source["authority"],
        "source_url": url,
        "sha256": digest,
        "size_bytes": len(raw),
        "content_type": content_type,
        "evidence_path": path.relative_to(data_root).as_posix(),
        "verified_markers": source.get("required_markers", []),
    }
    parser_name = source.get("parser")
    if parser_name == "gatik_live_operations":
        evidence["structured_data"] = parse_gatik_live_operations(text)
    elif parser_name is not None:
        raise ValueError(f"unsupported primary source parser: {parser_name}")
    return evidence


def event_period_key(value: object) -> tuple[int, int, int]:
    """Validate ISO 8601 calendar-day or reduced month precision without inventing a day."""
    text = str(value)
    if re.fullmatch(r"\d{4}-\d{2}", text):
        year, month = (int(part) for part in text.split("-"))
        if not 1 <= month <= 12:
            raise ValueError(f"invalid event month precision: {text}")
        return year, month, 0
    parsed = date.fromisoformat(text)
    return parsed.year, parsed.month, parsed.day


def validate_registry(registry: dict[str, Any]) -> None:
    sources = {str(row["source_id"]): row for row in registry.get("sources", [])}
    if len(sources) != len(registry.get("sources", [])) or len(sources) < 4:
        raise ValueError("source registry is incomplete or duplicated")
    parser_names = {row.get("parser") for row in sources.values() if row.get("parser") is not None}
    if not parser_names.issubset({"gatik_live_operations"}):
        raise ValueError(f"unsupported source parser in registry: {sorted(parser_names)}")
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
        exact_date = row.get("part135_certificate_date")
        month_period = row.get("part135_certificate_period")
        if bool(exact_date) == bool(month_period):
            raise ValueError(f"FAA authorization must carry exactly one date precision: {row.get('operator_id')}")
        if exact_date:
            date.fromisoformat(str(exact_date))
        elif not re.fullmatch(r"\d{4}-\d{2}", str(month_period)):
            raise ValueError(f"invalid FAA certificate month precision: {row.get('operator_id')}")
        if not row.get("permission"):
            raise ValueError(f"incomplete FAA authorization record: {row.get('operator_id')}")
        if row.get("operating_area") is None and row.get("operating_area_status") != "not_listed_as_current_operating_area_on_faa_page":
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
        if status == "commercial_driverless" and (row.get("commercial") is not True or row.get("human_driver_in_cab") is not False):
            raise ValueError(f"commercial driverless record is internally inconsistent: {row['operator_id']}")
        if not row.get("geography") or row.get("source_id") not in sources:
            raise ValueError(f"trucking record lacks geography/source: {row.get('operator_id')}")
    events = registry.get("operation_events") or []
    if not events:
        raise ValueError("operation event table is empty")
    if not any(event_period_key(row["effective_at"])[0] >= 2024 for row in events):
        raise ValueError("operation events must include 2024+ evidence")
    for row in events:
        event_period_key(row["effective_at"])
        if row.get("operation_status") not in ALLOWED_STATUSES:
            raise ValueError(f"event has unsupported operation status: {row}")
        if row.get("source_id") not in sources:
            raise ValueError("event refers to unknown source")


def validate_structured_evidence(registry: dict[str, Any], manifest: dict[str, Any]) -> None:
    source_map = {row["source_id"]: row for row in manifest["sources"]}
    live_sources = [source for source in registry["sources"] if source.get("parser") == "gatik_live_operations"]
    if len(live_sources) != 1:
        raise ValueError("registry must contain exactly one Gatik Live Operations source")
    live_source_id = str(live_sources[0]["source_id"])
    live_evidence = source_map.get(live_source_id)
    if not live_evidence or "structured_data" not in live_evidence:
        raise ValueError("Gatik Live Operations structured data is missing from verified evidence")


def verify_manifest(data_root: Path) -> dict[str, Any]:
    manifest = json.loads((data_root / "raw" / "latest-manifest.json").read_text())
    for row in manifest["sources"]:
        path = data_root / row["evidence_path"]
        raw = path.read_bytes()
        if sha256(raw) != row["sha256"]:
            raise ValueError(f"raw source hash mismatch: {row['source_id']}")
    return manifest


def enrich_records(records: list[dict[str, Any]], source_map: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            **source,
            "source_url": source_map[str(source["source_id"])]["source_url"],
            "source_sha256": source_map[str(source["source_id"])]["sha256"],
            "source_evidence_path": source_map[str(source["source_id"])]["evidence_path"],
        }
        for source in records
    ]


def build_part135_reconciliation(
    drones: list[dict[str, Any]],
    events: list[dict[str, Any]],
    source_map: dict[str, dict[str, Any]],
    retrieved_at: str,
) -> dict[str, Any]:
    faa_source = source_map.get(FAA_PART135_SOURCE_ID)
    if faa_source is None:
        raise ValueError("FAA Part 135 package-delivery source is missing")
    listed_operator_ids = {str(row["operator_id"]) for row in drones}
    records = []
    announcements = sorted(
        (
            row
            for row in events
            if row.get("mode") == "drone_package_delivery"
            and row.get("event_type") == "regulatory_authorization_announcement"
            and row.get("operation_status") == "regulatory_authorization"
        ),
        key=lambda row: (event_period_key(row["effective_at"]), str(row["operator_id"])),
    )
    for row in announcements:
        operator_id = str(row["operator_id"])
        if operator_id in listed_operator_ids:
            continue
        operator_source = source_map.get(str(row["source_id"]))
        if operator_source is None:
            raise ValueError(f"authorization announcement source is missing: {row['source_id']}")
        records.append(
            {
                "operator_id": operator_id,
                "operator_name": row.get("operator_name"),
                "announcement_effective_at": row["effective_at"],
                "authorization_type": row.get("authorization_type"),
                "operator_source_id": row["source_id"],
                "operator_source_url": operator_source["source_url"],
                "operator_source_sha256": operator_source["sha256"],
                "faa_registry_status": "not_listed_on_current_faa_package_delivery_page",
            }
        )
    return {
        "schema_version": 1,
        "retrieved_at": retrieved_at,
        "faa_registry": {
            "source_id": FAA_PART135_SOURCE_ID,
            "source_url": faa_source["source_url"],
            "source_sha256": faa_source["sha256"],
            "listed_operator_count": len(drones),
        },
        "records": records,
        "interpretation": (
            "An operator primary source may report FAA Part 135 authorization before the current FAA package-delivery page lists the operator. "
            "This view does not infer that the authorization is invalid, that commercial service has started, or that an unlisted operator belongs in the FAA-listed registry."
        ),
    }


def build_api(registry: dict[str, Any], manifest: dict[str, Any], api_dir: Path) -> dict[str, Any]:
    source_map = {row["source_id"]: row for row in manifest["sources"]}
    drones = enrich_records(registry["drone_part135"], source_map)
    trucking = enrich_records(registry["trucking_operators"], source_map)
    events = enrich_records(registry["operation_events"], source_map)
    part135_reconciliation = build_part135_reconciliation(
        drones, events, source_map, manifest["retrieved_at"]
    )
    api_dir.mkdir(parents=True, exist_ok=True)
    (api_dir / "drone-part135.json").write_bytes(dump({"schema_version": 1, "records": drones}))
    (api_dir / "trucking.json").write_bytes(dump({"schema_version": 1, "records": trucking}))
    (api_dir / "events.json").write_bytes(dump({"schema_version": 1, "records": events}))
    (api_dir / "part135-reconciliation.json").write_bytes(dump(part135_reconciliation))
    (api_dir / "provenance.json").write_bytes(dump(manifest))
    (api_dir / "registry.json").write_bytes(dump(registry))

    live_sources = [source for source in registry["sources"] if source.get("parser") == "gatik_live_operations"]
    live_source_id = str(live_sources[0]["source_id"]) if len(live_sources) == 1 else None
    live_evidence = source_map.get(live_source_id) if live_source_id else None
    gatik_live = None
    if live_evidence and "structured_data" in live_evidence:
        gatik_live = {
            "schema_version": 1,
            "source_id": live_source_id,
            "source_url": live_evidence["source_url"],
            "source_sha256": live_evidence["sha256"],
            "source_evidence_path": live_evidence["evidence_path"],
            "retrieved_at": manifest["retrieved_at"],
            **live_evidence["structured_data"],
        }
        (api_dir / "gatik-live-operations.json").write_bytes(dump(gatik_live))

    event_periods = [str(row["effective_at"]) for row in events]
    coverage = {
        "faa_part135_operator_count": len(drones),
        "part135_operator_announcements_not_listed_count": len(part135_reconciliation["records"]),
        "autonomous_trucking_operator_count": len(trucking),
        "commercial_driverless_trucking_operator_count": sum(row["operation_status"] == "commercial_driverless" for row in trucking),
        "operation_event_count": len(events),
        "operation_event_first_period": min(event_periods, key=event_period_key),
        "operation_event_last_period": max(event_periods, key=event_period_key),
        "events_2024_or_later": sum(event_period_key(value)[0] >= 2024 for value in event_periods),
        "primary_source_count": len(manifest["sources"]),
        "raw_evidence_count": len(manifest["sources"]),
    }
    views = {
        "drone_part135": "drone-part135.json",
        "part135_reconciliation": "part135-reconciliation.json",
        "trucking": "trucking.json",
        "events": "events.json",
        "registry": "registry.json",
        "provenance": "provenance.json",
    }
    if gatik_live is not None:
        coverage["gatik_live_displayed_row_count"] = gatik_live["displayed_row_count"]
        coverage["gatik_live_displayed_rows_complete"] = gatik_live["displayed_rows_complete"]
        views["gatik_live_operations"] = "gatik-live-operations.json"
    index = {
        "schema_version": 1,
        "dataset": "Autonomous logistics primary evidence",
        "retrieved_at": manifest["retrieved_at"],
        "coverage": coverage,
        "views": views,
        "rules": registry["rules"],
    }
    (api_dir / "index.json").write_bytes(dump(index))
    return index


def prune_raw_evidence(data_root: Path, source_evidence: list[dict[str, Any]]) -> None:
    raw_root = data_root / "raw"
    referenced = {data_root / row["evidence_path"] for row in source_evidence}
    objects = raw_root / "objects"
    if objects.exists():
        for path in objects.iterdir():
            if path.is_file() and path not in referenced:
                path.unlink()
    historical_manifests = raw_root / "manifests"
    if historical_manifests.exists():
        shutil.rmtree(historical_manifests)


def collect(registry: dict[str, Any], data_root: Path) -> dict[str, Any]:
    source_evidence = [fetch_source(row, data_root) for row in registry["sources"]]
    manifest = {
        "schema_version": 1,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "sources": source_evidence,
    }
    prune_raw_evidence(data_root, source_evidence)
    (data_root / "raw" / "latest-manifest.json").write_bytes(dump(manifest))
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
    validate_structured_evidence(registry, manifest)
    index = build_api(registry, manifest, args.api_dir)
    print(json.dumps(index["coverage"], sort_keys=True))


if __name__ == "__main__":
    main()
