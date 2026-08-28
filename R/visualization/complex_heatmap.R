#!/usr/bin/env Rscript
# Publication-quality clustered heatmap via ComplexHeatmap — used for the
# figure types where R's ComplexHeatmap ecosystem (annotation tracks,
# dendrograms, split heatmaps) exceeds what the Python/Plotly heatmap in
# omicsfusion.visualization.plots offers.
#
# Usage:
#   Rscript complex_heatmap.R \
#       --matrix normalized_transcriptomics.csv --metadata metadata.csv \
#       --annotation condition,batch --output heatmap.pdf

suppressPackageStartupMessages({
  library(optparse)
})

option_list <- list(
  make_option("--matrix", type = "character"),
  make_option("--metadata", type = "character", default = NULL),
  make_option("--sample-id-column", type = "character", default = "sample_id"),
  make_option("--annotation", type = "character", default = NULL, help = "comma-separated metadata columns"),
  make_option("--top-n-variable", type = "integer", default = 50),
  make_option("--output", type = "character", default = "heatmap.pdf")
)
opt <- parse_args(OptionParser(option_list = option_list))
if (is.null(opt$matrix)) stop("--matrix is required")

suppressPackageStartupMessages({
  library(ComplexHeatmap)
  library(circlize)
})

mat <- as.matrix(read.csv(opt$matrix, row.names = 1, check.names = FALSE))
variances <- apply(mat, 1, var, na.rm = TRUE)
top_features <- names(sort(variances, decreasing = TRUE))[seq_len(min(opt[["top-n-variable"]], nrow(mat)))]
mat <- mat[top_features, , drop = FALSE]

annotation <- NULL
if (!is.null(opt$metadata) && !is.null(opt$annotation)) {
  metadata <- read.csv(opt$metadata, check.names = FALSE)
  rownames(metadata) <- metadata[[opt[["sample-id-column"]]]]
  metadata <- metadata[colnames(mat), , drop = FALSE]
  annotation_cols <- strsplit(opt$annotation, ",")[[1]]
  annotation <- HeatmapAnnotation(df = metadata[, annotation_cols, drop = FALSE])
}

pdf(opt$output, width = 10, height = 8)
draw(Heatmap(
  mat,
  name = "value",
  top_annotation = annotation,
  show_row_names = nrow(mat) <= 60,
  col = colorRamp2(c(min(mat, na.rm = TRUE), 0, max(mat, na.rm = TRUE)), c("blue", "white", "red"))
))
dev.off()

cat(sprintf("ComplexHeatmap: %d features x %d samples -> %s\n", nrow(mat), ncol(mat), opt$output))
