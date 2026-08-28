# References

Conceptual foundations for OmicsFusion's design. No code was copied from
these projects unless their licence explicitly permits it — OmicsFusion is
an independent implementation inspired by their design principles.

## Workflow architecture

- Di Tommaso, P. et al. "Nextflow enables reproducible computational workflows." *Nature Biotechnology* (2017).
- Ewels, P. A. et al. "The nf-core framework for community-curated bioinformatics pipelines." *Nature Biotechnology* (2020).
- Langer, B. E. et al. "Empowering bioinformatics communities with Nextflow and nf-core." (concept referenced for the modular, containerised, community-pipeline design this project follows.)
- [nf-core/rnaseq](https://github.com/nf-core/rnaseq) — modular RNA-seq pipeline structure.
- [nf-core/taxprofiler](https://github.com/nf-core/taxprofiler) — modular taxonomic profiling pipeline structure.
- [quantms](https://github.com/bigbio/quantms) — proteomics workflow design patterns.

## Statistical & analysis methods

- Love, M. I., Huber, W., Anders, S. "Moderated estimation of fold change and dispersion for RNA-seq data with DESeq2." *Genome Biology* (2014).
- Robinson, M. D., McCarthy, D. J., Smyth, G. K. "edgeR: a Bioconductor package for differential expression analysis of digital gene expression data." *Bioinformatics* (2010).
- Ritchie, M. E. et al. "limma powers differential expression analyses for RNA-sequencing and microarray studies." *Nucleic Acids Research* (2015).
- Argelaguet, R. et al. "Multi-Omics Factor Analysis — a framework for unsupervised integration of multi-omics data sets." *Molecular Systems Biology* (2018) (MOFA2).
- Singh, A. et al. "DIABLO: an integrative approach for identifying key molecular drivers from multi-omics assays." *Bioinformatics* (2019) (mixOmics/DIABLO).
- Korotkevich, G. et al. "Fast gene set enrichment analysis." *bioRxiv* (fgsea).
- Oksanen, J. et al. *vegan: Community Ecology Package* (R) — compositional/diversity methods referenced for the microbiome module.

## Software libraries

- [scikit-bio](http://scikit-bio.org/) — diversity metrics and compositional-data methods referenced for the microbiome module design.
- Pedregosa, F. et al. "Scikit-learn: Machine Learning in Python." *JMLR* (2011).
- McKinney, W. "Data Structures for Statistical Computing in Python" (pandas).
- Gu, Z. "Complex Heatmaps Reveal Patterns and Correlations in Multidimensional Genomic Data." *Bioinformatics* (2016) (ComplexHeatmap).

## Databases (referenced for annotation design, no content redistributed)

- Wishart, D. S. et al. "HMDB 5.0: the Human Metabolome Database." *Nucleic Acids Research* (2022).
- [MicroPhenoDB](http://www.liwzlab.cn/microphenodb/) — microbiome-phenotype association database, referenced conceptually for the annotation-layer design.
- National Microbiome Data Collaborative (NMDC) — data standards referenced conceptually for the metadata schema design.
- Multiomics Analytics Group educational resources — general multi-omics integration teaching materials referenced conceptually.

## Review

- A technical review of multi-omics data integration methods (early/intermediate/late integration taxonomy) informed the structure of `docs/integration.md` and `omicsfusion.integration`.
