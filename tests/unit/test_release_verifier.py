import hashlib
import json

import pytest

from ai_subtitle_studio.release_verifier import ReleaseVerificationError, verify_release_directory


def _manifest_for(path, *, size=None, digest=None, index=1):
    data = path.read_bytes() if path.exists() else b""
    return {
        "artifacts": [
            {
                "name": path.name,
                "kind": "runtime_volume",
                "size_bytes": len(data) if size is None else size,
                "sha256": hashlib.sha256(data).hexdigest() if digest is None else digest,
                "volume_index": index,
            }
        ]
    }


def _write_manifest(tmp_path, manifest):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_release_verifier_accepts_matching_asset(tmp_path):
    asset = tmp_path / "runtime.7z.001"
    asset.write_bytes(b"valid")
    manifest = _write_manifest(tmp_path, _manifest_for(asset))
    assert verify_release_directory(tmp_path, manifest) == [asset]


def test_release_verifier_rejects_missing_asset(tmp_path):
    asset = tmp_path / "missing.7z.001"
    manifest = _write_manifest(tmp_path, _manifest_for(asset, size=1, digest="0" * 64))
    with pytest.raises(ReleaseVerificationError, match="Missing"):
        verify_release_directory(tmp_path, manifest)


def test_release_verifier_rejects_oversized_asset(tmp_path):
    asset = tmp_path / "runtime.7z.001"
    asset.write_bytes(b"x")
    manifest = _write_manifest(tmp_path, _manifest_for(asset))
    with pytest.raises(ReleaseVerificationError, match="limit"):
        verify_release_directory(
            tmp_path,
            manifest,
            github_asset_limit_bytes=2,
            runtime_volume_limit_bytes=1,
        )


def test_release_verifier_rejects_corrupt_asset(tmp_path):
    asset = tmp_path / "runtime.7z.001"
    asset.write_bytes(b"valid")
    manifest = _write_manifest(tmp_path, _manifest_for(asset, digest="0" * 64))
    with pytest.raises(ReleaseVerificationError, match="SHA-256"):
        verify_release_directory(tmp_path, manifest)


def test_release_verifier_rejects_non_contiguous_volume_indexes(tmp_path):
    asset = tmp_path / "runtime.7z.002"
    asset.write_bytes(b"valid")
    manifest = _write_manifest(tmp_path, _manifest_for(asset, index=2))
    with pytest.raises(ReleaseVerificationError, match="contiguous"):
        verify_release_directory(tmp_path, manifest)
