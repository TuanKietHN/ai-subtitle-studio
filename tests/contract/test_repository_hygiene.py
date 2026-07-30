from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]


def test_gitignore_excludes_private_and_generated_release_data():
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
    required = (
        "__pycache__/",
        ".ruff_cache/",
        ".venv/",
        "outputs/**",
        "!outputs/.gitkeep",
        "release/",
        "release-staging/",
        "*.exe",
        "*.7z.*",
        "*.mp4",
        "*.srt",
        "*.sqlite3-*",
        ".env.*",
        "*.pfx",
        "*.pem",
        "*.key",
        "packaging/vendor/",
    )
    for pattern in required:
        assert pattern in ignored


def test_version_has_one_literal_source():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    package_init = (ROOT / "src/ai_subtitle_studio/__init__.py").read_text(encoding="utf-8")
    assert re.search(
        r'^version = "\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?"$',
        pyproject,
        re.MULTILINE,
    )
    assert not re.search(r'APP_VERSION\s*=\s*"\d+\.\d+\.\d+"', package_init)
    assert "importlib.metadata.version" in package_init


def test_public_repository_requires_owner_license_decision():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "private" in readme.lower()
    assert "license" in readme.lower()
