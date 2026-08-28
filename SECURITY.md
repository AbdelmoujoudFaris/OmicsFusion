# Security Policy

## Supported versions

OmicsFusion is pre-1.0; only the latest release on the `main` branch
receives security fixes.

## Reporting a vulnerability

Please do not open a public GitHub issue for security vulnerabilities.
Instead, report it privately to the maintainers (see the repository's
GitHub "Security" tab to open a private security advisory).

Include:

- A description of the vulnerability and its potential impact
- Steps to reproduce
- Affected version(s)

We will acknowledge receipt within 5 business days and aim to provide a
fix or mitigation plan within 30 days, depending on severity.

## Scope notes

- OmicsFusion's CLI and pipeline execute local files and, optionally,
  local `Rscript`/`nextflow` binaries you already have installed; it does
  not fetch or execute remote code by default.
- The Streamlit GUI (`app/streamlit/`) is intended for local/trusted-network
  use (a researcher's own machine or lab server); it is not hardened for
  exposure on the public internet (no authentication is implemented).
- The annotation module (`omicsfusion.annotation`) reads only local,
  user-supplied mapping files by default and makes no network calls.
