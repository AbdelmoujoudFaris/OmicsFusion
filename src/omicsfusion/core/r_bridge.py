"""Python -> R bridge (spec section 3).

Where the R/Bioconductor ecosystem is materially stronger than any Python
equivalent (DESeq2/edgeR/limma for count-based differential expression,
MOFA2/mixOmics for latent-factor integration, fgsea for gene-set
enrichment), OmicsFusion shells out to a dedicated ``Rscript`` under
``R/`` rather than reimplementing those methods in Python. This module is
the one place that knows how to invoke them and how to fail clearly when R
or a required package is missing, rather than letting every caller
duplicate that subprocess/error-handling logic.

Data crosses the bridge via CSV/TSV files rather than an in-process bridge
(e.g. rpy2), keeping the Python side usable with no R installed at all,
per the "core platform must remain usable without ..." principle applied
project-wide (spec section 16).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from omicsfusion.core.logging_config import get_logger

logger = get_logger("core.r_bridge")

R_ROOT = Path(__file__).resolve().parents[3] / "R"


class RNotAvailableError(RuntimeError):
    pass


class RScriptError(RuntimeError):
    def __init__(self, script: str, returncode: int, stderr: str):
        self.script = script
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"R script '{script}' failed (exit {returncode}):\n{stderr}")


def rscript_available() -> bool:
    return shutil.which("Rscript") is not None


def run_r_script(
    script: str, args: list[str], timeout: int = 3600
) -> subprocess.CompletedProcess:
    """Run an R script under ``R/`` with the given CLI arguments.

    ``script`` is relative to the repository's ``R/`` directory, e.g.
    ``"differential/deseq2_differential.R"``.
    """
    rscript = shutil.which("Rscript")
    if rscript is None:
        raise RNotAvailableError(
            "Rscript was not found on PATH. Install R (see environment.yml) to use "
            f"R-backed methods, or use the pure-Python equivalent for '{script}'."
        )

    script_path = R_ROOT / script
    if not script_path.exists():
        raise FileNotFoundError(f"R script not found: {script_path}")

    cmd = [rscript, str(script_path), *args]
    logger.info("Running R script: %s", " ".join(cmd))
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, check=False
    )

    if result.returncode != 0:
        raise RScriptError(script, result.returncode, result.stderr)

    logger.info("R script '%s' completed successfully", script)
    return result
