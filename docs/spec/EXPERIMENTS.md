# Paraguard Experiments

Goal: find out whether spectral and coherence features add real, robust detection value beyond strong non-spectral baselines. Record negative results.

## Hypotheses

| ID | Hypothesis | Falsified if |
|---|---|---|
| G1 | The Rayleigh periodicity test detects beacons at lower false-positive rates than interval-regularity heuristics | Not better at equal FPR, for jitter ≤ 20% |
| G2 | Spectral features improve host-behavior malware detection over syscall n-gram/frequency baselines | Ablation shows no gain |
| G3 | Cross-channel coherence adds signal for ransomware-like behavior | Ablation shows no gain |
| G4 | Context-conditioned baselines cut false positives | No reduction in alerts per host per day at equal recall |
| G5 | Detection degrades gracefully under jitter, sleeps and padding | Detection collapses at mild evasion strength |
| G6 | Models trained on one dataset generalize to another | Large cross-dataset drop with no recovery |
| G7 | Fleet correlation improves detection of shared C2 | No gain over per-host tests |

## Datasets (public; check availability, licenses and known issues)
- **Network / beaconing / botnets:** CTU-13 botnet captures, Stratosphere IPS datasets (including malware and normal captures), UNSW-NB15, CIC-IDS2017/2018 (labeling issues documented in follow-up studies; treat with care)
- **Host syscall traces:** ADFA-LD (Linux IDS), DongTing (Linux syscall dataset), public dynamic-analysis reports for malware families (sandbox-generated)
- **Benign periodic traffic:** enterprise or campus flow logs where available; otherwise lab-generated benign traffic with updaters, NTP, health checks, cloud sync
- **Synthetic:** timestamp generators for periodic events with controlled jitter, plus benign background (events only; no malicious code)

## Baselines
1. Interval-regularity beacon heuristics (coefficient of variation, dispersion scores)
2. Binned FFT peak detector (no rigorous null)
3. Syscall n-gram / frequency features + random forest or gradient boosting
4. Isolation forest on simple counts
5. Per-host static rules (no context)

## Metrics
- **TPR at FPR ∈ {0.1%, 1%}**, AUPRC, AUROC (secondary)
- **Precision at low FPR** and the **base-rate table** (alerts per host per day for realistic volumes)
- Time to detect from first malicious behavior
- Family-held-out accuracy
- Cross-dataset performance drop
- CPU and memory overhead per host
- All splits: time-based; family-held-out where labels allow; repeated with ≥ 5 seeds

## Experiments

**Y1: Null calibration.** Benign and synthetic uniform events: measured vs. nominal false-positive rate for the periodicity test (including bursty benign data). Gate for G1.

**Y2: Beacon detection vs. jitter.** Synthetic and real beacon captures; sweep jitter 0–50% and event counts 20–1,000. Compare to baselines 1 and 2. Tests G1.

**Y3: Host behavior classification.** Spectral features vs. n-gram baseline vs. both combined; family-held-out split. Tests G2.

**Y4: Coherence ablation.** Ransomware-like traces vs. benign bulk file operations (backups, compression, indexing). Tests G3; benign bulk I/O is the hard negative.

**Y5: Context ablation.** With and without context baselines and the allowlist. Tests G4.

**Y6: Evasion study.** Signal-level transformations: jitter, random sleeps, padding with benign-like events, splitting across processes. Plot detection vs. strength for each model variant. Tests G5.

**Y7: Cross-dataset.** Train on dataset A, test on B (and the reverse). Tests G6.

**Y8: Fleet correlation.** Simulated fleets with a shared beacon at low per-host strength; combine p-values. Include benign fleets with shared schedulers to check the dependence problem. Tests G7.

**Y9: Overhead.** Throughput (events/s per core), memory per tracked process, effect of bin sizes and scales.

## Success criteria for v0.1

| Level | Criterion |
|---|---|
| Minimum | Y1 calibrated; Y2 matches the best heuristic at 0% jitter with equal or lower FPR |
| Good | Y2 beats heuristics for jitter ≤ 20%; Y3 spectral+baseline features improve AUPRC by ≥ 3 points on family-held-out |
| Great | Y6 shows graceful degradation (retains ≥ 50% of TPR at moderate evasion); Y4 shows coherence separates ransomware-like from benign bulk I/O |

## Stop / pivot conditions
- If Y3 ablation shows spectral features add nothing over n-gram features, drop the host-classifier claim and keep only the periodicity tester for network beaconing.
- If Y6 shows detection collapses under mild jitter or padding, reposition Paraguard as a **complementary feature** and publish the evasion curves honestly.
- If Y1 shows the null is badly miscalibrated on benign bursty data, switch to permutation or empirical-null testing before any other claim.
- If benign periodic software dominates alerts (Y5), prioritize the allowlist and context work over new features.

## Report template

```
Run ID:
Dataset / split (time, family-held-out):
Features / model / context:
Baselines:
TPR@0.1% FPR / TPR@1% FPR / AUPRC:
Alerts per host per day (assumed volume):
Evasion strength and retained TPR:
Overhead:
Notes:
```
