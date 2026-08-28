// Builds project.yaml from flat CLI-style parameters using
// workflows/bin/make_project_config.py (auto-added to PATH by Nextflow).
// Skipped entirely when params.config already points at a project.yaml.

process PREPARE_CONFIG {
    tag "prepare_config"
    label 'process_single'
    publishDir "${params.outdir}", mode: 'copy'

    input:
    path rna
    path proteomics
    path metabolomics
    path metadata

    output:
    path 'project.yaml', emit: config

    script:
    def rna_opt          = (rna.name          != 'NO_FILE_RNA')          ? "--rna ${rna.name}"                   : ''
    def proteomics_opt   = (proteomics.name   != 'NO_FILE_PROTEOMICS')   ? "--proteomics ${proteomics.name}"     : ''
    def metabolomics_opt = (metabolomics.name != 'NO_FILE_METABOLOMICS') ? "--metabolomics ${metabolomics.name}" : ''
    def diff_opts        = params.differential_condition ?
        "--differential-condition '${params.differential_condition}' --differential-reference '${params.differential_reference}'" +
        (params.differential_group ? " --differential-group '${params.differential_group}'" : '') : ''
    def ml_opts          = params.ml_target ? "--ml-target '${params.ml_target}'" : ''
    """
    make_project_config.py \\
        --name '${params.name ?: "omicsfusion_run"}' \\
        ${rna_opt} ${proteomics_opt} ${metabolomics_opt} \\
        --metadata ${metadata.name} \\
        ${diff_opts} ${ml_opts} \\
        --outdir . \\
        --output project.yaml
    """
}
