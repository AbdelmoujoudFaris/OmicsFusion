#!/usr/bin/env Rscript
# limma-based differential analysis for continuous (proteomics/microarray-
# like) intensity data. Unlike DESeq2, limma expects already-normalized,
# roughly log-scale values — do not feed it raw counts.
#
# Usage:
#   Rscript limma_differential.R \
#       --matrix normalized_proteomics.csv --metadata metadata.csv \
#       --sample-id-column sample_id --condition condition \
#       --reference control --group treated --output results.csv

suppressPackageStartupMessages({
  library(optparse)
})

option_list <- list(
  make_option("--matrix", type = "character"),
  make_option("--metadata", type = "character"),
  make_option("--sample-id-column", type = "character", default = "sample_id"),
  make_option("--condition", type = "character"),
  make_option("--reference", type = "character"),
  make_option("--group", type = "character"),
  make_option("--output", type = "character", default = "differential_limma.csv")
)
opt <- parse_args(OptionParser(option_list = option_list))

for (required in c("matrix", "metadata", "condition", "reference", "group")) {
  if (is.null(opt[[required]])) {
    stop(sprintf("--%s is required", required))
  }
}

suppressPackageStartupMessages({
  library(limma)
})

expr <- read.csv(opt$matrix, row.names = 1, check.names = FALSE)
metadata <- read.csv(opt$metadata, check.names = FALSE)
sample_id_col <- opt[["sample-id-column"]]
rownames(metadata) <- metadata[[sample_id_col]]

common_samples <- intersect(colnames(expr), rownames(metadata))
if (length(common_samples) < 4) {
  stop(sprintf(
    "Only %d samples shared between matrix and metadata; need >= 4.",
    length(common_samples)
  ))
}
expr <- as.matrix(expr[, common_samples, drop = FALSE])
metadata <- metadata[common_samples, , drop = FALSE]

group_factor <- relevel(factor(metadata[[opt$condition]]), ref = opt$reference)
design <- model.matrix(~group_factor)

fit <- lmFit(expr, design)
fit <- eBayes(fit)

coef_name <- paste0("group_factor", opt$group)
top <- topTable(fit, coef = coef_name, number = Inf, sort.by = "P")
top$feature <- rownames(top)

out <- data.frame(
  feature = top$feature,
  log2FC = top$logFC,
  p_value = top$P.Value,
  adjusted_p_value = top$adj.P.Val,
  effect_size = top$t,
  mean_group = NA,
  mean_reference = NA
)

write.csv(out, opt$output, row.names = FALSE)
cat(sprintf("limma: %d features tested -> %s\n", nrow(out), opt$output))
