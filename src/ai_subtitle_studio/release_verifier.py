"""Offline verification for generated release manifests and assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

GITHUB_ASSET_LIMIT_BYTES = 2 * 1024 * 1024 * 1024
RUNTIME_VOLUME_LIMIT_BYTES = 19 * 1024 * 1024 * 100


class ReleaseVerificationError(RuntimeError):
    """Raised when release assets do not satisfy the published contract."""


def compute_runtime_bundle_id(manifest: dict[str, Any]) -> str:
    release = manifest.get("release")
    if not isinstance(release, dict):
        raise ReleaseVerificationError("Manifest release identity is missing")
    fields = (
        "app_version",
        "git_commit",
        "python_version",
        "platform",
        "whisperx_version",
        "torch_version",
        "cuda_runtime_version",
        "pyinstaller_version",
        "dependency_manifest_sha256",
    )
    lines = [f"{field}={release.get(field, '')}" for field in fields]
    volumes = sorted(
        (item for item in manifest.get("artifacts", []) if item.get("kind") == "runtime_volume"),
        key=lambda item: int(item.get("volume_index", 0)),
    )
    for volume in volumes:
        lines.append(
            "volume={}|{}|{}|{}".format(
                int(volume.get("volume_index", 0)),
                volume.get("name", ""),
                int(volume.get("size_bytes", 0)),
                str(volume.get("sha256", "")).lower(),
            )
        )
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8-sig") as stream:
        return json.load(stream)


def verify_release_directory(
    release_dir: str | Path,
    manifest_path: str | Path,
    *,
    github_asset_limit_bytes: int = GITHUB_ASSET_LIMIT_BYTES,
    runtime_volume_limit_bytes: int = RUNTIME_VOLUME_LIMIT_BYTES,
) -> list[Path]:
    root = Path(release_dir)
    manifest = load_manifest(manifest_path)
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ReleaseVerificationError("Manifest does not contain any artifacts")
    runtime_bundle_id = str(manifest.get("runtime_bundle_id") or "")
    if not re.fullmatch(r"[0-9a-f]{64}", runtime_bundle_id):
        raise ReleaseVerificationError("Manifest runtime_bundle_id is missing or invalid")

    verified: list[Path] = []
    volume_indexes: list[int] = []
    seen_names: set[str] = set()
    for artifact in artifacts:
        name = str(artifact.get("name") or "")
        if not name or Path(name).name != name or name in seen_names:
            raise ReleaseVerificationError(f"Invalid or duplicate artifact name: {name!r}")
        seen_names.add(name)
        path = root / name
        if not path.is_file():
            raise ReleaseVerificationError(f"Missing release asset: {name}")
        size = path.stat().st_size
        if size != int(artifact.get("size_bytes", -1)):
            raise ReleaseVerificationError(f"Size mismatch for {name}")
        if size >= github_asset_limit_bytes:
            raise ReleaseVerificationError(f"GitHub asset limit exceeded by {name}")
        if artifact.get("kind") == "runtime_volume":
            if size >= runtime_volume_limit_bytes:
                raise ReleaseVerificationError(f"Runtime volume limit exceeded by {name}")
            volume_indexes.append(int(artifact.get("volume_index", 0)))
        actual_hash = sha256_file(path)
        if actual_hash.lower() != str(artifact.get("sha256") or "").lower():
            raise ReleaseVerificationError(f"SHA-256 mismatch for {name}")
        verified.append(path)

    if volume_indexes:
        expected = list(range(1, len(volume_indexes) + 1))
        if sorted(volume_indexes) != expected:
            raise ReleaseVerificationError(
                f"Runtime volume indexes must be contiguous: expected {expected}, got {sorted(volume_indexes)}"
            )
    expected_bundle_id = compute_runtime_bundle_id(manifest)
    if runtime_bundle_id != expected_bundle_id:
        raise ReleaseVerificationError("runtime_bundle_id does not match release identity and ordered volumes")
    return verified


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-dir", required=True)
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args(argv)
    try:
        verified = verify_release_directory(args.release_dir, args.manifest)
    except ReleaseVerificationError as exc:
        print(f"release verification failed: {exc}")
        return 1
    print(f"verified {len(verified)} release assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
