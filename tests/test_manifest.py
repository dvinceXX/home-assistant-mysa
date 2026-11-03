"""Tests for the Mysa integration manifest."""

import json
from pathlib import Path


def test_manifest_is_valid() -> None:
    """Ensure the integration manifest has required metadata."""
    manifest_path = (
        Path(__file__).parents[1]
        / "custom_components"
        / "mysa"
        / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["domain"] == "mysa"
    assert manifest["name"] == "Mysa"
    assert manifest["config_flow"] is True
    assert manifest["iot_class"] == "cloud_polling"
