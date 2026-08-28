"""Software version capture for reproducibility.

Every analysis run should be able to answer, unambiguously, "which exact
software produced this result?". :func:`collect_versions` gathers versions
of the interpreter and key libraries actually installed, rather than trusting
requirement pins (which describe intent, not what actually ran).
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from importlib import metadata as importlib_metadata

from omicsfusion import __version__ as OMICSFUSION_VERSION

_TRACKED_PACKAGES = [
    "pandas",
    "numpy",
    "scipy",
    "scikit-learn",
    "statsmodels",
    "matplotlib",
    "plotly",
    "networkx",
    "pydantic",
]


def collect_versions() -> dict[str, str]:
    """Return a dict of component -> version string for the current environment."""
    versions: dict[str, str] = {
        "omicsfusion": OMICSFUSION_VERSION,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
    }

    for pkg in _TRACKED_PACKAGES:
        try:
            versions[pkg] = importlib_metadata.version(pkg)
        except importlib_metadata.PackageNotFoundError:
            versions[pkg] = "not installed"

    versions["R"] = _r_version()
    versions["Nextflow"] = _nextflow_version()
    return versions


def _r_version() -> str:
    rscript = shutil.which("Rscript")
    if rscript is None:
        return "not available"
    try:
        out = subprocess.run(
            [rscript, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        text = (out.stdout or out.stderr).strip().splitlines()
        return text[0] if text else "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _nextflow_version() -> str:
    nf = shutil.which("nextflow")
    if nf is None:
        return "not available"
    try:
        out = subprocess.run(
            [nf, "-version"], capture_output=True, text=True, timeout=10, check=False
        )
        for line in (out.stdout or "").splitlines():
            if "version" in line.lower():
                return line.strip()
        return "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def write_versions_file(path: str) -> None:
    versions = collect_versions()
    with open(path, "w", encoding="utf-8") as fh:
        fh.writelines(f"{key}: {value}\n" for key, value in versions.items())
