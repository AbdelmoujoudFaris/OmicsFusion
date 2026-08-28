#!/usr/bin/env Rscript
# Multi-Omics Factor Analysis (MOFA2) — rigorous intermediate integration
# (spec sections 12-13). This is the R counterpart to
# omicsfusion.integration.methods.pca_consensus_integration: MOFA2 fits a
# single probabilistic latent-factor model jointly across views (rather
# than per-view PCA followed by concatenation), which is the correct tool
# when a real cross-view variance decomposition is needed.
#
# Each input matrix must be features (rows) x samples (columns), already
# normalized appropriately for its modality.
#
# Usage:
#   Rscript mofa2_integration.R \
#       --views rna=rna_normalized.csv,protein=protein_normalized.csv \
#       --n-factors 10 --outdir mofa_results/

suppressPackageStartupMessages({
  library(optparse)
})

option_list <- list(
  make_option("--views", type = "character", help = "comma-separated name=path.csv pairs"),
  make_option("--n-factors", type = "integer", default = 10),
  make_option("--outdir", type = "character", default = "mofa_results")
)
opt <- parse_args(OptionParser(option_list = option_list))
if (is.null(opt$views)) stop("--views is required, e.g. rna=rna.csv,protein=protein.csv")

suppressPackageStartupMessages({
  library(MOFA2)
})

dir.create(opt$outdir, showWarnings = FALSE, recursive = TRUE)

view_specs <- strsplit(opt$views, ",")[[1]]
data_list <- list()
for (spec in view_specs) {
  kv <- strsplit(spec, "=")[[1]]
  name <- kv[1]
  path <- kv[2]
  mat <- as.matrix(read.csv(path, row.names = 1, check.names = FALSE))
  data_list[[name]] <- mat
}

mofa_object <- create_mofa(data_list)
model_opts <- get_default_model_options(mofa_object)
model_opts$num_factors <- opt[["n-factors"]]
mofa_object <- prepare_mofa(mofa_object, model_options = model_opts)

mofa_object <- run_mofa(mofa_object, outfile = file.path(opt$outdir, "model.hdf5"), use_basilisk = TRUE)

factors <- get_factors(mofa_object, factors = "all")[[1]]
write.csv(factors, file.path(opt$outdir, "sample_factors.csv"))

weights <- get_weights(mofa_object, views = "all", factors = "all")
for (view_name in names(weights)) {
  write.csv(weights[[view_name]], file.path(opt$outdir, sprintf("weights_%s.csv", view_name)))
}

variance <- calculate_variance_explained(mofa_object)$r2_per_factor[[1]]
write.csv(variance, file.path(opt$outdir, "variance_explained.csv"))

cat(sprintf(
  "MOFA2: %d factors fit across %d views -> %s\n",
  opt[["n-factors"]], length(data_list), opt$outdir
))
