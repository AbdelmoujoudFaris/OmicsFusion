# Machine learning

`omicsfusion.machine_learning.models.run_ml` (spec section 15).

## Leakage prevention

Every model is wrapped in an `sklearn.Pipeline` (median imputation ->
scaling -> model). Cross-validation uses `cross_validate` over the
**training split only**, so scaling/imputation statistics are refit on
each fold's training data — never on the full dataset or the held-out
test set. The held-out test split (`test_size`, default 0.25) is used only
for the final reported metrics; it plays no role in model selection.

## Tasks and models

| Task | Models |
|---|---|
| `classification` | `random_forest`, `elastic_net` (logistic regression, elastic-net penalty), `logistic_regression`, `svm`, `xgboost` (if installed) |
| `regression` | `random_forest`, `elastic_net`, `svm`, `xgboost` (if installed) |

## Metrics

Classification: accuracy, F1, precision, recall, ROC-AUC (binary: single
positive-class AUC; multiclass: one-vs-rest weighted average).
Regression: R², RMSE, MAE.

## Feature importance

Tree-based models expose `feature_importances_`; linear models expose
`|coef_|`. Both are surfaced as a `pandas.Series` on each `ModelResult` and
plotted (`plot_feature_importance`) in the report/GUI. Treat this as
exploratory signal, not a validated biomarker list — see
`docs/reproducibility.md` on multiple-testing considerations that don't
automatically apply to ML feature-importance rankings.

## Inputs

`run_ml(X, y, ...)` expects `X` as **samples x features** — typically the
output of `early_integration(...).combined` for multi-omics ML, or a
single dataset's `.matrix.T` for one modality. `y` is a `pandas.Series`
aligned by sample ID; non-numeric classification targets are label-encoded
automatically.

## Minimum sample size

`run_ml` requires at least `2 * cv_folds` labelled samples and raises
otherwise — an underpowered CV split should fail loudly rather than return
a metric computed on 1-sample folds.

## Deep learning (optional)

`pip install -e ".[deep]"` installs PyTorch. A multi-omics
autoencoder/VAE module is on the roadmap (see README) — the core platform
is fully usable without it and without a GPU.
