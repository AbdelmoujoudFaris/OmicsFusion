#!/usr/bin/env Rscript
# DIABLO (mixOmics) — supervised multi-omics integration that finds a
# molecular signature jointly discriminating a known outcome across views
# (spec section 14). Unlike MOFA2 (unsupervised), DIABLO requires an
# outcome label and is the right tool when the goal is a classifier-style
# joint signature rather than exploratory latent factors.
#
# Usage:
#   Rscript diablo_integration.R \
#       --views rna=rna_normalized.csv,protein=protein_normalized.csv \
#       --metadata metadata.csv --sample-id-column sample_id \
#       --outcome condition --n-features 10 --outdir diablo_results/

suppressPackageStartupMessages({
  library(optparse)
})

option_list <- list(
  make_option("--views", type = "character"),
  make_option("--metadata", type = "character"),
  make_option("--sample-id-column", type = "character", default = "sample_id"),
  make_option("--outcome", type = "character"),
  make_option("--n-features", type = "integer", default = 10),
  make_option("--outdir", type = "character", default = "diablo_results")
)
opt <- parse_args(OptionParser(option_list = option_list))
for (required in c("views", "metadata", "outcome")) {
  if (is.null(opt[[required]])) stop(sprintf("--%s is required", required))
}

suppressPackageStartupMessages({
  library(mixOmics)
})

dir.create(opt$outdir, showWarnings = FALSE, recursive = TRUE)

metadata <- read.csv(opt$metadata, check.names = FALSE)
sample_id_col <- opt[["sample-id-column"]]
rownames(metadata) <- metadata[[sample_id_col]]

view_specs <- strsplit(opt$views, ",")[[1]]
X <- list()
for (spec in view_specs) {
  kv <- strsplit(spec, "=")[[1]]
  name <- kv[1]
  path <- kv[2]
  mat <- read.csv(path, row.names = 1, check.names = FALSE)
  X[[name]] <- t(as.matrix(mat)) # DIABLO expects samples x features
}

common_samples <- Reduce(intersect, lapply(X, rownames))
common_samples <- intersect(common_samples, rownames(metadata))
if (length(common_samples) < 6) {
  stop(sprintf("Only %d samples shared across all views and metadata; need >= 6.", length(common_samples)))
}
X <- lapply(X, function(m) m[common_samples, , drop = FALSE])
Y <- factor(metadata[common_samples, opt$outcome])

design <- matrix(0.1, ncol = length(X), nrow = length(X), dimnames = list(names(X), names(X)))
diag(design) <- 0

keepX <- lapply(X, function(m) rep(opt[["n-features"]], 2))

model <- block.splsda(X = X, Y = Y, ncomp = 2, keepX = keepX, design = design)

for (view_name in names(X)) {
  loadings <- selectVar(model, block = view_name, comp = 1)$value
  write.csv(loadings, file.path(opt$outdir, sprintf("signature_%s.csv", view_name)))
}

perf_result <- perf(model, validation = "Mfold", folds = min(5, length(common_samples) %/% 2), nrepeat = 5)
sink(file.path(opt$outdir, "performance.txt"))
print(perf_result)
sink()

cat(sprintf(
  "DIABLO: joint signature (%d features/view/component) fit across %d views -> %s\n",
  opt[["n-features"]], length(X), opt$outdir
))
