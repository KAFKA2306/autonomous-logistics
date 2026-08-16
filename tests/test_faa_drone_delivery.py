import pytest

from src.collect_faa_drone_delivery import verify


def test_verify_requires_every_reviewed_operator_on_source_page():
    registry = {"operators": [{"operator": "Wing Aviation, LLC"}, {"operator": "Zipline International Inc."}]}
    raw = b"<html><body>Wing Aviation, LLC is listed here.</body></html>"
    with pytest.raises(ValueError, match="Zipline International"):
        verify(registry, raw)


def test_verify_accepts_reviewed_names_and_records_hash():
    registry = {"operators": [{"operator": "Wing Aviation, LLC"}]}
    result = verify(registry, b"<p>Wing Aviation, LLC</p>")
    assert result["operator_count"] == 1
    assert len(result["source_sha256"]) == 64
