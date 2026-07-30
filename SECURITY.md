# Security Policy

## Supported versions

Until `v0.1.0` is published, only the latest release candidate is supported.
After the first stable release, the latest stable version receives security
fixes.

## Reporting a vulnerability

Do not open a public issue containing credentials, private subtitle data, or
exploit details. Report vulnerabilities privately to the repository owner
through GitHub's private vulnerability reporting/security advisory feature.

Include:

- Affected version and Windows version.
- Reproduction steps with sanitized data.
- Expected and observed behavior.
- Relevant logs after removing paths, credentials, and subtitle contents.

## Sensitive data

API keys belong only in Windows Credential Manager through the application's
keyring adapter. Never place credentials in source, `.env` files committed to
Git, SQLite, logs, screenshots, subtitles, GitHub Actions variables, or release
artifacts.

Stable release assets must be SHA-256 verified and Authenticode signed.
Unsigned builds may only be published as pre-releases.
