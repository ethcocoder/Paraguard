# Paraguard Math Specification

## 1. Signals

For process `p` and channel `c`, bin size Δ:
```
x_{p,c}[n] = number of events of channel c by process p in [nΔ, (n+1)Δ)
```
Detrend by subtracting the window mean. Also keep raw event times `t_1 < t_2 < ... < t_N`.

## 2. Spectral features

Short-time spectrum `S[n, f] = |STFT(x)|²`. For each window with normalized spectrum `π_f = S_f / Σ_f S_f`:

- **Peak-to-average ratio:** `PAR = max_f S_f / mean_f S_f`
- **Spectral flatness:** `SF = exp(mean_f log S_f) / mean_f S_f`  (near 1: noise-like; near 0: a few strong lines)
- **Spectral entropy:** `H = -Σ_f π_f log π_f`
- **Band energy:** `E_b = Σ_{f ∈ band b} S_f` on octave bands
- **Centroid:** `Σ_f f π_f`
- **Harmonic ratio:** energy at `m·f*` (m = 2..4) divided by energy at `f*`, where `f* = argmax S_f`

Feature vector `φ` concatenates these across channels and scales.

## 3. Periodicity test for event timestamps (Rayleigh)

For a candidate frequency `ω = 2π/P`:
```
R(ω) = | (1/N) Σ_k e^{i ω t_k} |            (mean resultant length, in [0, 1])
Z(ω) = N · R(ω)²
```
Under no periodicity (event phases uniform on the circle) and moderate `N`, `Z` is approximately `Exp(1)`, so
```
p(ω) ≈ exp(-Z)
```
(more accurate small-sample form, a standard approximation: `p ≈ exp( √(1 + 4N + 4N²(1 − R²)) − (1 + 2N) )`; for very small `N` use simulation or a permutation null).

**Scan over periods** in `[P_min, P_max]` with total observation time `Tobs`. The number of roughly independent frequencies is
```
M ≈ (1/P_min − 1/P_max) · Tobs
p_adj = min(1, M · min_ω p(ω))            (Bonferroni over frequencies)
```
Across many processes/destinations use **Benjamini-Hochberg** FDR control at level `q` (default 0.01).

**Why Rayleigh and not binning + FFT:** it uses exact timestamps, avoids bin-alignment artifacts, and has a clean null distribution.

**Jitter:** if the interval is `P(1 + u)` with `u` uniform in `[-j, j]`, phase coherence decays with `k` periods as roughly `|sinc(π j k)|`-like terms, so `R(ω)` drops and the line broadens as jitter grows. Detection power falls with `j`; this is measured in E1 rather than assumed.

**Fallback for jittered beacons:** interval-based statistics on `d_k = t_{k+1} − t_k`: coefficient of variation, histogram peakedness, and the fraction of intervals within `±j` of a dominant value.

## 4. Cross-channel coherence

For channels `a, b` of the same process:
```
C_{ab}[f] = |S_{ab}[f]|² / (S_{aa}[f] · S_{bb}[f])
```
Behavior of interest: high coherence between read, write and rename counts in a shared band (a repeating per-file pipeline). Use coherence on residuals after removing the baseline-explained part, so shared daily cycles do not inflate it.

## 5. Context baseline and anomaly score

Context bucket `c`; benign feature vectors `{φ_i}` give mean `μ_c` and shrunk covariance `Σ_c = (1 − λ) Ŝ + λ diag(Ŝ)`.
```
d²(φ) = (φ − μ_c)ᵀ Σ_c⁻¹ (φ − μ_c)
```
Alert threshold `τ_c` = the `(1 − α)` quantile of `d²` on benign validation data, so the false-positive rate per context is controlled by construction. Alternative: isolation forest in the same feature space.

**Continuous geometry:** `μ(g) = Σ_m π_m(g) μ_m`, `π(g) = softmax(W g)`, fitted on benign data (as in Parascope).

**Allowed periodic lines:** per context, store a list of `(period, tolerance, destination class)` seen in benign data (updaters, health checks). A significant period matching an allowed line is not alerted.

## 6. Supervised family model (optional)

Gradient-boosted trees on `φ` with labels from public datasets. Evaluation uses **time-based splits** and **family-held-out splits** to measure generalization to unseen families, which is the real task.

## 7. Base-rate arithmetic (required in every report)

With `E` evaluated entities per day, false-positive rate `α`, and true prevalence `π_m`:
```
false alerts/day = α · E · (1 − π_m)
precision = TPR · π_m / ( TPR · π_m + α · (1 − π_m) )
```
Example: `E = 10⁶`, `α = 10⁻³` gives about 1,000 false alerts a day even with perfect recall. Report **precision at low FPR** and **alerts per host per day**.

## 8. Fleet correlation

For `H` hosts each with p-value `p_h` for the same (period, destination), combine with Fisher's method: `X = −2 Σ_h ln p_h ~ χ²_{2H}` under the null (valid for independent hosts; hosts sharing a clock or scheduler can be dependent, so validate on benign fleets).

## 9. Costs
- STFT per process-channel window: O(W log W)
- Rayleigh scan: O(N · G) for `G` candidate periods (use a vectorized grid or the FFT of a finely binned train for speed, then re-test the top peaks exactly)
- Baseline fit: O(samples · dim²)

## 10. Known risks in the math
- Attackers can add jitter, long random sleeps or benign-looking padding to flatten lines.
- Benign software is also periodic (updaters, telemetry), so the allowlist and context matter more than the test.
- Rayleigh p-values assume independent events; bursts of retries create dependence. Validate the null on benign logs.
