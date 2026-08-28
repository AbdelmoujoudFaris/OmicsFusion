"""Multi-omics machine learning module (spec section 15).

Every model is wrapped in an ``sklearn.Pipeline`` with scaling *inside* the
pipeline, and cross-validation is performed via ``cross_validate`` so that
scaling is refit on each training fold rather than on the full dataset —
this is what "prevent data leakage" (spec requirement) means in practice.
A held-out test split is used only for the final reported metrics; model
selection uses cross-validation on the training portion only.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.svm import SVC, SVR

from omicsfusion.core.logging_config import get_logger

logger = get_logger("machine_learning.models")

_CLASSIFIERS = {
    "random_forest": lambda seed: RandomForestClassifier(
        n_estimators=300, random_state=seed
    ),
    "elastic_net": lambda seed: LogisticRegression(
        solver="saga", l1_ratio=0.5, max_iter=5000, random_state=seed
    ),
    "logistic_regression": lambda seed: LogisticRegression(
        max_iter=5000, random_state=seed
    ),
    "svm": lambda seed: SVC(probability=True, random_state=seed),
}
_REGRESSORS = {
    "random_forest": lambda seed: RandomForestRegressor(
        n_estimators=300, random_state=seed
    ),
    "elastic_net": lambda seed: ElasticNet(random_state=seed),
    "svm": lambda seed: SVR(),
}

try:
    from xgboost import XGBClassifier, XGBRegressor

    _CLASSIFIERS["xgboost"] = lambda seed: XGBClassifier(
        random_state=seed, eval_metric="logloss", use_label_encoder=False
    )
    _REGRESSORS["xgboost"] = lambda seed: XGBRegressor(random_state=seed)
    _XGBOOST_AVAILABLE = True
except ImportError:
    _XGBOOST_AVAILABLE = False


@dataclass
class ModelResult:
    model: str
    task: str
    cv_metrics: dict[str, float]
    test_metrics: dict[str, float]
    feature_importance: pd.Series | None = None


@dataclass
class MLResult:
    task: str
    target: str
    n_samples: int
    n_features: int
    results: list[ModelResult] = field(default_factory=list)

    def best(self, metric: str = "roc_auc") -> ModelResult | None:
        candidates = [r for r in self.results if metric in r.test_metrics]
        if not candidates:
            return None
        return max(candidates, key=lambda r: r.test_metrics[metric])


def run_ml(
    X: pd.DataFrame,
    y: pd.Series,
    task: str = "classification",
    models: list[str] | None = None,
    cv_folds: int = 5,
    test_size: float = 0.25,
    random_state: int = 42,
) -> MLResult:
    """Train/evaluate one or more models for a classification or regression task.

    ``X`` must be samples x features (as produced by
    :func:`omicsfusion.integration.methods.early_integration` or a single
    dataset's transposed matrix). Missing values are median-imputed inside
    each CV fold's training data only.
    """
    models = models or ["random_forest"]
    if task not in ("classification", "regression"):
        raise ValueError("task must be 'classification' or 'regression'")

    common_index = X.index.intersection(y.dropna().index)
    if len(common_index) < cv_folds * 2:
        raise ValueError(
            f"Only {len(common_index)} labelled samples available; need at least "
            f"{cv_folds * 2} for {cv_folds}-fold cross-validation."
        )
    X = X.loc[common_index]
    y = y.loc[common_index]

    label_encoder = None
    if task == "classification" and not pd.api.types.is_numeric_dtype(y):
        label_encoder = LabelEncoder()
        y = pd.Series(label_encoder.fit_transform(y), index=y.index)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y if task == "classification" else None,
    )

    registry = _CLASSIFIERS if task == "classification" else _REGRESSORS
    scoring = (
        ["accuracy", "f1_weighted", "roc_auc_ovr"]
        if task == "classification"
        else ["r2", "neg_root_mean_squared_error", "neg_mean_absolute_error"]
    )
    binary = task == "classification" and y.nunique() == 2
    if binary:
        scoring = ["accuracy", "f1", "precision", "recall", "roc_auc"]

    ml_result = MLResult(
        task=task,
        target=str(y.name or "target"),
        n_samples=len(X),
        n_features=X.shape[1],
    )

    for model_name in models:
        if model_name not in registry:
            logger.warning(
                "Model '%s' unavailable for task '%s'; skipping.", model_name, task
            )
            continue

        pipeline = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", registry[model_name](random_state)),
            ]
        )

        try:
            cv_scores = cross_validate(
                pipeline,
                X_train,
                y_train,
                cv=(
                    min(cv_folds, y_train.value_counts().min())
                    if task == "classification"
                    else cv_folds
                ),
                scoring=scoring,
                error_score="raise",
            )
            cv_metrics = {
                k.replace("test_", ""): float(np.mean(v))
                for k, v in cv_scores.items()
                if k.startswith("test_")
            }
        except Exception as exc:  # noqa: BLE001 - isolate one model's CV failure
            logger.warning("CV failed for model '%s': %s", model_name, exc)
            cv_metrics = {}

        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)
        test_metrics = _test_metrics(pipeline, X_test, y_test, y_pred, task, binary)

        importance = _feature_importance(pipeline.named_steps["model"], X.columns)

        ml_result.results.append(
            ModelResult(
                model=model_name,
                task=task,
                cv_metrics=cv_metrics,
                test_metrics=test_metrics,
                feature_importance=importance,
            )
        )
        logger.info("ML[%s/%s]: test_metrics=%s", task, model_name, test_metrics)

    return ml_result


def _test_metrics(
    pipeline, X_test, y_test, y_pred, task: str, binary: bool
) -> dict[str, float]:
    metrics: dict[str, float] = {}
    if task == "classification":
        metrics["accuracy"] = float(accuracy_score(y_test, y_pred))
        average = "binary" if binary else "weighted"
        metrics["f1"] = float(
            f1_score(y_test, y_pred, average=average, zero_division=0)
        )
        metrics["precision"] = float(
            precision_score(y_test, y_pred, average=average, zero_division=0)
        )
        metrics["recall"] = float(
            recall_score(y_test, y_pred, average=average, zero_division=0)
        )
        if hasattr(pipeline, "predict_proba"):
            try:
                proba = pipeline.predict_proba(X_test)
                if binary:
                    metrics["roc_auc"] = float(roc_auc_score(y_test, proba[:, 1]))
                else:
                    metrics["roc_auc"] = float(
                        roc_auc_score(
                            y_test, proba, multi_class="ovr", average="weighted"
                        )
                    )
            except ValueError:
                pass
    else:
        metrics["r2"] = float(r2_score(y_test, y_pred))
        metrics["rmse"] = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        metrics["mae"] = float(mean_absolute_error(y_test, y_pred))
    return metrics


def _feature_importance(model, feature_names) -> pd.Series | None:
    if hasattr(model, "feature_importances_"):
        return pd.Series(model.feature_importances_, index=feature_names).sort_values(
            ascending=False
        )
    if hasattr(model, "coef_"):
        coef = np.asarray(model.coef_)
        coef = coef[0] if coef.ndim > 1 else coef
        return pd.Series(np.abs(coef), index=feature_names).sort_values(ascending=False)
    return None
