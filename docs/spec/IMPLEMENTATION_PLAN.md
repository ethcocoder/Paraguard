# Paraguard Implementation Plan

Stack: Python 3.10+, NumPy, SciPy, pandas, scikit-learn (or LightGBM), matplotlib. Data loaders for flow logs (Zeek-style conn logs) and host traces (auditd/eBPF exports or public syscall datasets).

**Lab safety:** never execute real malware outside an isolated VM without network access to production. Prefer public pre-recorded traces and flow logs.

## Repo layout

```
paraguard/
  paraguard/
    __init__.py
    signalize.py      # events -> binned signals
    features.py       # spectral features
    periodic.py       # Rayleigh scan, FDR
    coherence.py      # cross-channel coherence
    baseline.py       # context baselines, allowlist
    score.py          # anomaly + beacon + family models
    report.py         # explanations and plots
  eval/
    datasets.py
    metrics.py        # TPR at fixed FPR, AUPRC, precision at low FPR, alerts/host/day
    evasion.py        # signal-level jitter/sleep/padding transformations (simulation only)
    run_eval.py
  tests/
```

## Step 0: Baselines and data (days 1 to 4)
1. Pick datasets (see `EXPERIMENTS.md`); write loaders and time-based splits.
2. Baselines: (a) interval-regularity beacon statistics (coefficient of variation, skew/dispersion style scores), (b) syscall n-gram or frequency features + random forest, (c) isolation forest on simple counts.
3. Record TPR at FPR 0.1% and 1%, AUPRC. This is the bar.

## Step 1: Periodicity tester (days 5 to 8)

```python
import numpy as np

def rayleigh_scan(ts, periods):
    t = np.asarray(ts, dtype=np.float64)
    t = t - t[0]
    w = 2 * np.pi / np.asarray(periods)
    z = np.exp(1j * np.outer(w, t)).mean(axis=1)    # (G,) complex mean resultant
    R = np.abs(z)
    Z = len(t) * R ** 2                              # ~ Exp(1) under the null
    return R, Z

def period_pvalue(Z, tobs, p_min, p_max):
    M = max(1.0, (1 / p_min - 1 / p_max) * tobs)     # approx independent frequencies
    p = np.exp(-Z)
    return np.minimum(1.0, M * p)                    # Bonferroni over frequencies
```

For many events and periods, chunk the outer product to bound memory.

**Tests (required):**
1. Null calibration: uniform random event times give an approximately uniform distribution of adjusted p-values (check the false-positive rate at 0.01 and 0.05).
2. Synthetic periodic events (known period, no jitter) are detected at the right period.
3. Power vs. jitter: detection rate as jitter goes from 0% to 50%.
4. Bursty benign-like synthetic events (clustered retries) do not inflate false positives beyond tolerance; if they do, switch to a permutation-based null.

## Step 2: Spectral features (days 9 to 12)
- STFT features per channel from `MATH_SPEC.md` §2.
- Feature cache (Parquet) keyed by process and window.
- Sanity checks: pure sine gives a high PAR and low SF; white noise gives a PAR near the expected value and SF near 1 (up to estimator bias).

## Step 3: Context baselines and allowlist (days 13 to 16)
- Context buckets from process class and host role (labels from dataset metadata where available).
- Mahalanobis scoring with shrinkage; quantile thresholds on benign validation.
- Allowlist of benign periodic lines learned from benign data.

## Step 4: Coherence feature (days 17 to 19)
- Residualize channels against baselines; compute coherence for pairs (read-write, write-rename, net-file).
- Ablate to see if it adds anything beyond per-channel features.

## Step 5: Evaluation (days 20 to 25)
- Time-based and family-held-out splits.
- Full metric suite, base-rate table.
- Ablations: remove periodicity, remove coherence, remove context.

## Step 6: Evasion robustness (days 26 to 29)
At the **signal level in simulation** only: add jitter to periodic event times, insert random sleeps, pad channels with benign-like activity, split activity across several processes. Report detection vs. strength of each transformation and what combination of features degrades least.

## Step 7: Packaging (days 30 to 33)
- CLI: `paraguard scan flows.csv --context-file ctx.json`
- Report with spectra and explanations.

## Definition of done for v0.1
- [ ] Null calibration test passes (false-positive rate near nominal)
- [ ] Baselines and Paraguard evaluated with time-based and family-held-out splits
- [ ] Ablation table (periodicity, coherence, context)
- [ ] Evasion degradation curves
- [ ] Base-rate / alerts-per-host-per-day table
- [ ] Honest README results

## Pitfalls
- Random train/test splits (they leak near-duplicate traces and inflate results).
- Evaluating only AUROC (hides the base-rate problem).
- Ignoring benign periodic software.
- Assuming lab datasets resemble real enterprise traffic.
- Reporting beacon detection at 0% jitter only.
