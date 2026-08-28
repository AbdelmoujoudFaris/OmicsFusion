"""Generates the synthetic demo dataset committed alongside this script.

Re-run this script (``python generate_demo_data.py``) to regenerate the
CSVs deterministically (fixed random seed) — e.g. after changing the
number of samples or effect sizes. The demo simulates a case/control study
with a real (simulated) biological signal shared across three omics layers,
so the demo differential/integration/ML results are non-trivial rather than
pure noise.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
N_SAMPLES = 40
N_GENES = 300
N_PROTEINS = 150
N_METABOLITES = 80
N_SIGNAL_FEATURES = 20  # features per modality carrying the case/control signal

rng = np.random.default_rng(SEED)
OUT = Path(__file__).parent


def make_groups(n_samples: int) -> np.ndarray:
    return np.array(["treated"] * (n_samples // 2) + ["control"] * (n_samples - n_samples // 2))


def simulate_matrix(n_features: int, samples: list[str], groups: np.ndarray, base_mean: float,
                     dispersion: float, effect_size: float, n_signal: int) -> pd.DataFrame:
    is_treated = (groups == "treated").astype(float)
    data = np.zeros((n_features, len(samples)))
    for i in range(n_features):
        feature_mean = base_mean * rng.uniform(0.5, 2.0)
        shift = effect_size * feature_mean if i < n_signal else 0.0
        means = feature_mean + shift * is_treated
        data[i, :] = rng.negative_binomial(
            n=np.clip(feature_mean / dispersion, 1, None), p=0.5, size=len(samples)
        ) + np.clip(means - feature_mean, 0, None)
    ids = [f"feature_{i:04d}" for i in range(n_features)]
    return pd.DataFrame(data, index=ids, columns=samples)


def main() -> None:
    samples = [f"S{i:03d}" for i in range(1, N_SAMPLES + 1)]
    groups = make_groups(N_SAMPLES)
    rng.shuffle(groups)
    batch = np.where(np.arange(N_SAMPLES) % 2 == 0, "B1", "B2")
    sex = rng.choice(["F", "M"], size=N_SAMPLES)
    age = rng.normal(55, 12, size=N_SAMPLES).round(1)

    metadata = pd.DataFrame(
        {
            "sample_id": samples,
            "condition": groups,
            "batch": batch,
            "sex": sex,
            "age": age,
            "tissue": "liver",
            "timepoint": "T0",
        }
    )
    metadata.to_csv(OUT / "metadata.csv", index=False)

    rna = simulate_matrix(N_GENES, samples, groups, base_mean=200, dispersion=40,
                           effect_size=1.5, n_signal=N_SIGNAL_FEATURES)
    rna.index = [f"GENE_{i:04d}" for i in range(N_GENES)]
    rna.index.name = "gene_id"
    rna.to_csv(OUT / "transcriptomics.csv")

    proteomics = simulate_matrix(N_PROTEINS, samples, groups, base_mean=1000, dispersion=150,
                                  effect_size=1.0, n_signal=N_SIGNAL_FEATURES)
    proteomics.index = [f"PROT_{i:04d}" for i in range(N_PROTEINS)]
    proteomics.index.name = "protein_id"
    proteomics.to_csv(OUT / "proteomics.csv")

    metabolomics = simulate_matrix(N_METABOLITES, samples, groups, base_mean=500, dispersion=80,
                                    effect_size=1.2, n_signal=N_SIGNAL_FEATURES)
    metabolomics.index = [f"METAB_{i:04d}" for i in range(N_METABOLITES)]
    metabolomics.index.name = "metabolite_id"
    metabolomics.to_csv(OUT / "metabolomics.csv")

    print(f"Wrote demo dataset to {OUT} ({N_SAMPLES} samples).")


if __name__ == "__main__":
    main()
