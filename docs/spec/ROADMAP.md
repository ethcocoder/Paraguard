# Paraguard Roadmap

## Phase 0: Baselines and data (weeks 1 to 2)
- Loaders, splits, baseline detectors, metric suite including the base-rate table
- Deliverable: baseline results

## Phase 1: Periodicity tester (weeks 3 to 4)
- Rayleigh scan, multiple-testing control, null calibration, jitter study
- Deliverable: Y1, Y2 results (a self-contained, publishable component)

## Phase 2: Spectral host features (weeks 5 to 6)
- STFT features, context baselines, allowlist
- Deliverable: Y3, Y5 results

## Phase 3: Coherence and families (weeks 7 to 8)
- Coherence features, optional family classifier, cross-dataset tests
- Deliverable: Y4, Y7 results

## Phase 4: Evasion and fleet (weeks 9 to 10)
- Signal-level evasion study, fleet correlation
- Deliverable: Y6, Y8 results

## Phase 5: Release (weeks 11 to 14)
- CLI analyzer for flow logs and host traces, report generator, documentation
- Honest benchmark write-up including failures
- Deliverable: open-source release

## Product directions (after results)
- Zeek-style package or script that outputs significant periodic connections with p-values
- SIEM/EDR plugin that adds spectral fields to alerts
- SOC dashboard with per-process spectrograms and explanations
- Privacy-preserving mode: share spectra and features across organizations instead of raw logs
- Shares the signal layer with Parascope (security telemetry as another signal source)

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Attackers adapt with jitter and padding | High | Evasion study from the start; combine with non-spectral features; randomize feature subsets |
| Benign periodic software floods alerts | High | Context baselines, allowlist, FDR control |
| Lab datasets overstate real performance | High | Multiple datasets, cross-dataset tests, time-based splits, report base-rate arithmetic |
| Label noise in public datasets | Medium | Manual inspection of samples; prefer well-documented sets |
| Null miscalibration on bursty traffic | Medium | Permutation-based null; validate on benign logs |
| Handling malware samples is risky | Medium | Isolated VMs only; prefer pre-recorded traces |
| Crowded market (EDR, NDR vendors) | High | Open-source, focus on explainability and rigorous statistics |

## Future ideas
1. **Learned spectral encoder** (small neural model on spectrograms) with the statistical tests as a safety net.
2. **Adversarial training** against signal-level evasion transformations.
3. **Cross-host resonance maps** for lateral movement patterns.
4. **Parascope link:** one signal layer for ops and security telemetry.
5. **Explainable alerts:** plain-language summaries generated from the structured report.

## Next idea in this series
Paravec (spectral compression for vector-search indexes).
