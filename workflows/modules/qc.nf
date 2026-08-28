// Independent QC diagnostics, published alongside (but not blocking) the
// main analysis — a researcher can inspect QC while ANALYZE_AND_REPORT runs.

process QC {
    tag "qc"
    label 'process_single'
    publishDir "${params.outdir}/qc", mode: 'copy', pattern: 'qc_*.json'

    input:
    path config
    path rna
    path proteomics
    path metabolomics
    path metadata

    output:
    path 'qc_*.json', emit: reports

    script:
    """
    omicsfusion qc --config ${config}
    """
}
