// Fail-fast metadata/omics consistency gate before any analysis runs.

process VALIDATE_INPUTS {
    tag "validate"
    label 'process_single'

    input:
    path config
    path rna
    path proteomics
    path metabolomics
    path metadata

    output:
    path config, emit: config

    script:
    """
    omicsfusion validate --config ${config}
    """
}
