#!/usr/bin/env Rscript
# Gene Set Enrichment Analysis (GSEA) via fgsea — the ranked-list
# alternative to the over-representation test in
# omicsfusion.pathways.ora.over_representation_analysis. Use GSEA (this
# script) when every tested feature has a continuous ranking statistic
# (e.g. log2FC or a t-statistic from differential analysis); use ORA when
# only a discrete "significant feature" list is available.
#
# Usage:
#   Rscript fgsea_enrichment.R \
#       --ranks differential_transcriptomics.csv --rank-column log2FC \
#       --gene-sets gene_sets.gmt --output fgsea_results.csv

suppressPackageStartupMessages({
  library(optparse)
})

option_list <- list(
  make_option("--ranks", type = "character", help = "CSV with a 'feature' column and a ranking column"),
  make_option("--rank-column", type = "character", default = "log2FC"),
  make_option("--gene-sets", type = "character", help = "Path to a .gmt gene-set file"),
  make_option("--min-size", type = "integer", default = 5),
  make_option("--max-size", type = "integer", default = 500),
  make_option("--output", type = "character", default = "fgsea_results.csv")
)
opt <- parse_args(OptionParser(option_list = option_list))
for (required in c("ranks", "gene-sets")) {
  if (is.null(opt[[required]])) stop(sprintf("--%s is required", required))
}

suppressPackageStartupMessages({
  library(fgsea)
  library(data.table)
})

ranks_df <- read.csv(opt$ranks, check.names = FALSE)
if (!"feature" %in% colnames(ranks_df)) stop("--ranks file must have a 'feature' column")
rank_col <- opt[["rank-column"]]
if (!rank_col %in% colnames(ranks_df)) stop(sprintf("Rank column '%s' not found", rank_col))

ranks <- setNames(ranks_df[[rank_col]], ranks_df$feature)
ranks <- sort(ranks, decreasing = TRUE)

pathways <- gmtPathways(opt[["gene-sets"]])

result <- fgsea(
  pathways = pathways, stats = ranks,
  minSize = opt[["min-size"]], maxSize = opt[["max-size"]]
)
result <- result[order(result$padj), ]
result$leadingEdge <- sapply(result$leadingEdge, function(x) paste(x, collapse = ","))

fwrite(result, opt$output)
cat(sprintf(
  "fgsea: %d pathways tested, %d significant (padj<0.05) -> %s\n",
  nrow(result), sum(result$padj < 0.05, na.rm = TRUE), opt$output
))
