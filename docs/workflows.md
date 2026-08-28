# Nextflow workflow

`workflows/main.nf` wraps the OmicsFusion CLI as a Nextflow pipeline.

## Usage

```bash
cd workflows
nextflow run main.nf \
    --rna counts.csv --proteomics protein.csv --metabolomics metabolites.csv \
    --metadata metadata.csv \
    --differential-condition condition --differential-reference control \
    --outdir results \
    -profile docker
```

Any subset of `--rna`/`--proteomics`/`--metabolomics` may be given (at
least one is required); `--metadata` is always required.

## Profiles

`local` (default), `docker`, `singularity`, `conda` — see
`workflows/nextflow.config`. Docker/Singularity use the image built from
the repository `Dockerfile`; conda uses `environment.yml`.

## Structure

```text
workflows/
├── main.nf                      entry point
├── nextflow.config               profiles, resource defaults, manifest
├── conf/base.config               default process resources
├── bin/make_project_config.py     flat params -> project.yaml (auto on PATH)
├── assets/NO_FILE_*                placeholders for un-supplied modalities
└── modules/
    ├── prepare_config.nf          builds project.yaml from --rna/--proteomics/...
    ├── validate.nf                fail-fast metadata/omics consistency gate
    ├── qc.nf                      per-modality QC (parallel, independent)
    └── analyze.nf                 full run_pipeline (normalize→...→report.html)
```

## Why the config is generated, not passed in directly

Nextflow stages each declared input file independently into every
process's isolated work directory (and, under `-profile docker`/
`singularity`, into the container's mounts). A hand-written `project.yaml`
with paths from your local filesystem would not resolve inside that
sandbox. `PREPARE_CONFIG` (`modules/prepare_config.nf`) builds a
`project.yaml` whose `inputs:` paths always match the basenames Nextflow
stages, so path resolution is correct regardless of profile. The resolved
`project.yaml` is published to `<outdir>/project.yaml` — reproduce the
exact same run without Nextflow via `omicsfusion run --config <outdir>/project.yaml`.

## Resume / caching

`nextflow run main.nf ... -resume` skips any process whose inputs
(the config + staged files) are unchanged, using Nextflow's standard
content-hash cache in `work/`.

## Current limitation (roadmap)

`ANALYZE_AND_REPORT` currently invokes `omicsfusion run`, which internally
re-runs normalization → differential → integration → ML → report as one
Python process, rather than as separate cacheable Nextflow processes with
file-based data contracts between them. This means `-resume` currently
grants coarse-grained caching (skip validation/QC/the whole analysis if
nothing changed) rather than fine-grained caching (skip only ML if you
changed a normalization setting). Splitting `core.pipeline.run_pipeline`
into stage functions with well-defined intermediate file formats, and
wiring each as its own Nextflow process/subworkflow, is the natural next
step — see the README roadmap.
