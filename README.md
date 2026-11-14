# Paraguard

Paraguard is a research prototype for offline analysis of exported security event records. It groups timestamps by process and channel, computes spectral summaries, and scans event times for periodic patterns with multiple-testing correction.

It does not collect live telemetry, execute samples, connect to hosts, or take response actions. Treat alerts as analyst leads, not proof of malicious activity.

## Install

```powershell
python -m pip install -e .
```

## Input format

CSV and JSON Lines files need `timestamp`, `process_id`, and `channel` fields. `timestamp` is seconds on a consistent clock. `event_type` is optional.

```json
{"timestamp": 0.0, "process_id": "worker-1", "channel": "network", "event_type": "connect"}
```

## Analyze an exported file

```powershell
paraguard scan events.jsonl --min-period 2 --max-period 300 --fdr 0.01 --output report.json
```

Use `python -m paraguard scan events.csv` when running from a source checkout. The report includes per-process/channel features, periodicity statistics, adjusted q-values, and plain-language explanations.

For a cluster-preserving empirical null, use `--empirical-surrogates 199 --cluster-gap-seconds 1.5`. This relocates detected event clusters while preserving within-cluster timing, then compares the observed scan maximum with the surrogate maxima. The method is conditional on the gap threshold and exchangeable cluster-placement assumption; it is opt-in and does not replace review against representative benign telemetry.

`--frequency-count` controls the period-grid resolution (default `256`, maximum `100000`). Larger scans can take substantially longer as event volume grows.

Empirical p-value resolution is `1 / (surrogates + 1)`. Because Benjamini-Hochberg correction spans all tested process-channel groups, many groups may require more surrogates to reach the configured FDR. A work guard rejects oversized empirical scans.

## Limitations

The Rayleigh p-value is an asymptotic approximation and may be miscalibrated for bursty or dependent event times. This prototype has no context-conditioned benign baseline, allowlist, cross-channel coherence, family classifier, or public-dataset evaluation. No detection-performance claims are made. Consult `docs/spec` for the source design notes and planned validation work.

Run tests with:

```powershell
python -m unittest discover -s tests -v
```

## Calibrate the periodicity test

Run a deterministic Monte Carlo check of uniform and clustered null events plus a periodic positive control. The default analytic method is expected to fail on bursty patterns; compare with the cluster-preserving empirical method using a reduced, explicit test budget:

```powershell
paraguard validate --calibration-method cluster_empirical --trials 40 --events 20 --frequency-count 128 --surrogates 49 --alpha 0.05 --groups-per-host-day 1000 --output calibration.json
```

The report includes false-positive rates with Wilson 95% intervals and, when `--groups-per-host-day` is supplied, an estimated false-alert count per host-day. That estimate treats the value as the number of process-channel groups tested per host per day; it is an extrapolation, not an observed host metric. This is synthetic validation, not a substitute for benign host telemetry. The command exits nonzero when its null checks fail.

## Validate a benign event log

Use a representative log that is known to be benign. Paraguard splits each process-channel series chronologically, selects the gap whose training alert rate is closest to the target FDR, then evaluates that fixed gap on the held-out segment:

```powershell
paraguard validate-log benign_events.jsonl --train-fraction 0.6 --folds 3 --candidate-gaps 0.5 1 1.5 2 --surrogates 199 --fdr 0.01 --output heldout.json
```

With `--folds 3`, each fold expands its training prefix and tests the next non-overlapping time window; the gap is selected independently using only that fold's training data. The report includes per-fold and pooled held-out rates and Wilson intervals, selected gaps, and exact train/held-out event counts. Groups with fewer than four timestamps on either side or no timestamp spread are skipped; validation fails if no groups remain. This is an offline per-process/channel estimate: the input is assumed benign, host IDs and cross-host dependence are unavailable in the current schema, and walk-forward folds from one process-channel group are dependent, so pooled intervals are descriptive rather than independent-sample guarantees.