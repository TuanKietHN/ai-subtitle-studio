import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_release_manifest_schema_encodes_size_hash_and_stable_fields():
    schema = json.loads((ROOT / "packaging" / "release-manifest.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["schema_version"]["const"] == 1
    assert schema["properties"]["architecture"]["const"] == "x64"
    artifact = schema["properties"]["artifacts"]["items"]
    assert artifact["properties"]["size_bytes"]["exclusiveMaximum"] == 2 * 1024 * 1024 * 1024
    assert artifact["properties"]["sha256"]["pattern"] == "^[0-9a-f]{64}$"
    assert "signature_status" in artifact["required"]


def test_manifest_generator_uses_exact_tag_urls_hashes_and_installer_values():
    script = (ROOT / "scripts" / "generate-release-manifest.ps1").read_text(encoding="utf-8")
    for required in (
        "releases/download/$Tag",
        "Get-FileHash -Algorithm SHA256",
        "dependency_manifest_sha256",
        "SHA256SUMS-v$Version.txt",
        "generated-release-values.iss",
        "RuntimeVolumeCount",
    ):
        assert required in script
