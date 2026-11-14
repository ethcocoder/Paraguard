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

`--frequency-count` controls the period-grid resolution (default `256`, maximum `100000`). Larger scans can take substantially longer as event volume grows.

## Limitations

The Rayleigh p-value is an asymptotic approximation and may be miscalibrated for bursty or dependent event times. This prototype has no context-conditioned benign baseline, allowlist, cross-channel coherence, family classifier, or public-dataset evaluation. No detection-performance claims are made. Consult `docs/spec` for the source design notes and planned validation work.

Run tests with:

```powershell
python -m unittest discover -s tests -v
```