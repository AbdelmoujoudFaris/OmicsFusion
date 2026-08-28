// Runs the full OmicsFusion pipeline (normalization -> differential ->
// integration -> ML -> HTML report) via the same `omicsfusion run` entry
// point used outside Nextflow, so a Nextflow run and a bare CLI run of the
// same config produce identical results.

process ANALYZE_AND_REPORT {
    tag "analyze"
    label 'process_high'
    publishDir "${params.outdir}", mode: 'copy'

    input:
    path config
    path rna
    path proteomics
    path metabolomics
    path metadata

    output:
    path 'report.html',            emit: report
    path 'run_summary.json',       emit: summary
    path 'analysis_config.yaml',   emit: resolved_config
    path 'software_versions.txt',  emit: versions
    path 'omicsfusion.log',        emit: log
    path '*.csv',                  emit: tables, optional: true

    script:
    """
    omicsfusion run --config ${config}
    """
}
