#!/usr/bin/env python3
"""Build a project.yaml from flat Nextflow-style CLI parameters.

Kept dependency-free (stdlib only, no PyYAML) since Nextflow processes may
run this before the omicsfusion conda/pip environment is fully staged.
Placed under ``workflows/bin/`` so Nextflow automatically adds it to PATH
for every process (standard nf-core convention).
"""

from __future__ import annotations

import argparse


def _yaml_scalar(value: str) -> str:
    return f'"{value}"' if value else '""'


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="omicsfusion_run")
    parser.add_argument("--rna")
    parser.add_argument("--proteomics")
    parser.add_argument("--metabolomics")
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--differential-condition")
    parser.add_argument("--differential-reference")
    parser.add_argument("--differential-group")
    parser.add_argument("--ml-target")
    parser.add_argument("--outdir", default=".")
    parser.add_argument("--output", default="project.yaml")
    args = parser.parse_args()

    lines = [
        "project:",
        f"  name: {_yaml_scalar(args.name)}",
        "inputs:",
    ]
    if args.rna:
        lines.append(f"  transcriptomics: {_yaml_scalar(args.rna)}")
    if args.proteomics:
        lines.append(f"  proteomics: {_yaml_scalar(args.proteomics)}")
    if args.metabolomics:
        lines.append(f"  metabolomics: {_yaml_scalar(args.metabolomics)}")
    lines.append(f"  metadata: {_yaml_scalar(args.metadata)}")

    lines.append("analysis:")
    if args.differential_condition and args.differential_reference:
        lines.append("  differential:")
        lines.append(f"    condition: {_yaml_scalar(args.differential_condition)}")
        lines.append(f"    reference: {_yaml_scalar(args.differential_reference)}")
        if args.differential_group:
            lines.append(f"    group: {_yaml_scalar(args.differential_group)}")
    if args.ml_target:
        lines.append("  machine_learning:")
        lines.append("    enabled: true")
        lines.append(f"    target: {_yaml_scalar(args.ml_target)}")

    lines.append(f"outdir: {_yaml_scalar(args.outdir)}")

    with open(args.output, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
