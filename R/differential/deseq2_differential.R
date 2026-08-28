#!/usr/bin/env Rscript
# Rigorous count-based differential expression via DESeq2, invoked from
# Python by omicsfusion.core.r_bridge for the "R" path of section 10's
# differential-analysis framework. Requires raw (non-normalized) integer
# counts: DESeq2 fits its own size factors and dispersion model, so
# pre-normalizing the input (log/VST/etc.) here would violate its
# assumptions and invalidate the resulting p-values.
#
# Usage:
#   Rscript deseq2_differential.R \
#       --counts counts.csv --metadata metadata.csv \
#       --sample-id-column sample_id --condition condition \
#       --reference control --group treated --output results.csv

suppressPackageStartupMessages({
  library(optparse)
})

option_list <- list(
  make_option("--counts", type = "character"),
  make_option("--metadata", type = "character"),
  make_option("--sample-id-column", type = "character", default = "sample_id"),
  make_option("--condition", type = "character"),
  make_option("--reference", type = "character"),
  make_option("--group", type = "character"),
  make_option("--alpha", type = "double", default = 0.05),
  make_option("--output", type = "character", default = "differential_deseq2.csv")
)
opt <- parse_args(OptionParser(option_list = option_list))

for (required in c("counts", "metadata", "condition", "reference", "group")) {
  if (is.null(opt[[required]])) {
    stop(sprintf("--%s is required", required))
  }
}

suppressPackageStartupMessages({
  library(DESeq2)
})

counts <- read.csv(opt$counts, row.names = 1, check.names = FALSE)
metadata <- read.csv(opt$metadata, check.names = FALSE)
sample_id_col <- opt[["sample-id-column"]]
rownames(metadata) <- metadata[[sample_id_col]]

common_samples <- intersect(colnames(counts), rownames(metadata))
if (length(common_samples) < 4) {
  stop(sprintf(
    "Only %d samples shared between counts and metadata; need >= 4.",
    length(common_samples)
  ))
}
counts <- counts[, common_samples, drop = FALSE]
metadata <- metadata[common_samples, , drop = FALSE]

counts <- round(as.matrix(counts))
mode(counts) <- "integer"

metadata[[opt$condition]] <- relevel(factor(metadata[[opt$condition]]), ref = opt$reference)

dds <- DESeqDataSetFromMatrix(
  countData = counts,
  colData = metadata,
  design = as.formula(paste0("~", opt$condition))
)
dds <- DESeq(dds)
res <- results(dds, contrast = c(opt$condition, opt$group, opt$reference), alpha = opt$alpha)
res_df <- as.data.frame(res)
res_df$feature <- rownames(res_df)

out <- data.frame(
  feature = res_df$feature,
  log2FC = res_df$log2FoldChange,
  p_value = res_df$pvalue,
  adjusted_p_value = res_df$padj,
  effect_size = res_df$log2FoldChange / res_df$lfcSE,
  mean_group = NA,
  mean_reference = NA
)
out <- out[order(out$p_value), ]

write.csv(out, opt$output, row.names = FALSE)
cat(sprintf(
  "DESeq2: %d features tested, %d significant at alpha=%.3f -> %s\n",
  nrow(out), sum(out$adjusted_p_value < opt$alpha, na.rm = TRUE), opt$alpha, opt$output
))
