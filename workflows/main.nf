#!/usr/bin/env nextflow
/*
 * OmicsFusion — Nextflow entry point (spec section 4).
 *
 * Usage:
 *   nextflow run main.nf \
 *       --rna counts.csv --proteomics protein.csv --metabolomics metabolites.csv \
 *       --metadata metadata.csv \
 *       --differential-condition condition --differential-reference control \
 *       --outdir results [-profile docker]
 *
 * Any subset of --rna/--proteomics/--metabolomics may be supplied. A
 * project.yaml is generated from these flat parameters (see
 * modules/prepare_config.nf) so the rest of the pipeline runs from a single
 * resolved config file — exactly like `omicsfusion run --config project.yaml`
 * on the command line. That generated project.yaml is published to
 * `<outdir>/project.yaml`, so a run can be exactly reproduced later with
 * the plain CLI, without Nextflow.
 *
 * Note: this workflow builds its config from flat parameters rather than
 * accepting an arbitrary user-supplied project.yaml, because Nextflow
 * stages each input file independently per task; a hand-written config's
 * paths would need to already be valid inside every task's isolated work
 * directory (and, under -profile docker/singularity, inside the container's
 * mounted paths too). Generating the config here keeps that path-staging
 * correct automatically.
 */

nextflow.enable.dsl = 2

include { PREPARE_CONFIG }     from './modules/prepare_config.nf'
include { VALIDATE_INPUTS }    from './modules/validate.nf'
include { QC }                 from './modules/qc.nf'
include { ANALYZE_AND_REPORT } from './modules/analyze.nf'

def helpMessage() {
    log.info """
    OmicsFusion — modular multi-omics analysis and integration
    ============================================================
    Usage:
      nextflow run main.nf --rna counts.csv --proteomics protein.csv \\
          --metabolomics metabolites.csv --metadata metadata.csv \\
          --differential-condition condition --differential-reference control \\
          --outdir results [-profile docker|singularity|conda]

    Options:
      --rna / --proteomics / --metabolomics   Omics input files (any subset, at least one required)
      --metadata                  Sample metadata file (required)
      --differential-condition    Metadata column for the two-group comparison
      --differential-reference    Reference level of that column
      --differential-group        Comparison level (default: first non-reference level)
      --ml-target                 Metadata column to predict with machine learning
      --outdir                    Output directory (default: 'results')

    The resolved project.yaml is published to <outdir>/project.yaml and can
    be rerun directly with: omicsfusion run --config <outdir>/project.yaml

    Profiles: local (default), docker, singularity, conda
    """.stripIndent()
}

workflow {
    if (params.help) {
        helpMessage()
        exit 0
    }

    if (!params.metadata) {
        log.error "Missing required --metadata. See -help."
        exit 1
    }
    if (!params.rna && !params.proteomics && !params.metabolomics) {
        log.error "Provide at least one of --rna, --proteomics, --metabolomics. See -help."
        exit 1
    }

    rna_ch          = params.rna          ? file(params.rna, checkIfExists: true)         : file("${projectDir}/assets/NO_FILE_RNA")
    proteomics_ch   = params.proteomics   ? file(params.proteomics, checkIfExists: true)   : file("${projectDir}/assets/NO_FILE_PROTEOMICS")
    metabolomics_ch = params.metabolomics ? file(params.metabolomics, checkIfExists: true) : file("${projectDir}/assets/NO_FILE_METABOLOMICS")
    metadata_ch     = file(params.metadata, checkIfExists: true)

    PREPARE_CONFIG(rna_ch, proteomics_ch, metabolomics_ch, metadata_ch)
    VALIDATE_INPUTS(PREPARE_CONFIG.out.config, rna_ch, proteomics_ch, metabolomics_ch, metadata_ch)
    QC(VALIDATE_INPUTS.out.config, rna_ch, proteomics_ch, metabolomics_ch, metadata_ch)
    ANALYZE_AND_REPORT(VALIDATE_INPUTS.out.config, rna_ch, proteomics_ch, metabolomics_ch, metadata_ch)

    ANALYZE_AND_REPORT.out.report.view { "Report generated: $it" }
}
