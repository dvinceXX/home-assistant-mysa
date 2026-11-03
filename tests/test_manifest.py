"""Tests for the Mysa integration manifest."""

import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "mysa"


def test_manifest_is_valid() -> None:
    """Ensure the integration manifest has required metadata."""
    manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["domain"] == "mysa"
    assert manifest["name"] == "Mysa"
    assert manifest["config_flow"] is True
    assert manifest["iot_class"] == "cloud_polling"
    assert "mysa-client==0.2.1" in manifest["requirements"]


def test_translations_are_valid_json() -> None:
    """Ensure both translation files parse as JSON."""
    for path in (INTEGRATION / "strings.json", INTEGRATION / "translations" / "en.json"):
        json.loads(path.read_text(encoding="utf-8"))


def test_only_read_only_platforms_are_registered() -> None:
    """Ensure the integration exposes monitoring platforms only."""
    const = (INTEGRATION / "const.py").read_text(encoding="utf-8")
    assert 'PLATFORMS: Final = ["sensor", "binary_sensor"]' in const
