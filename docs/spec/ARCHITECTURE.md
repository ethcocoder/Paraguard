# Paraguard Architecture

## 1. Pipeline

```
 host events ──┐
 network logs ─┼─► Signalizer ─► Spectral Features ─► Context Baseline ─► Scorer ─► Alerts + explanations
 process tree ─┘        │                ▲                    ▲
                        │         Periodicity Tester          │
                        └── Context Encoder (geometry g) ─────┘
```

## 2. Components

### 2.1 Signalizer
Per process (or per flow group) and per channel, create evenly binned counts and byte-rates.

| Channel | Example signals |
|---|---|
| Network | connections per bin per destination, bytes out/in, inter-arrival times |
| File | reads, writes, creates, renames, distinct files touched per bin |
| Process | child spawns per bin, injection-related calls per bin |
| Memory/registry | allocation and key-write rates per bin |

Bin sizes: multiple scales (for example 100 ms, 1 s, 60 s). Event timestamps are also kept for the periodicity tester.

### 2.2 Spectral Features
Per signal window:
- Peak frequency, peak-to-average ratio (PAR)
- Spectral flatness and spectral entropy
- Log-spaced band energies (octave bands)
- Spectral centroid and rolloff
- Harmonic ratio (energy at integer multiples of the peak)

Cross-channel: coherence between channel pairs in each band.

### 2.3 Periodicity Tester (for events with timestamps)
- **Rayleigh scan** over a grid of candidate periods.
- Multiple-testing correction across periods, destinations and processes (Benjamini-Hochberg).
- Output: period, strength, adjusted p-value, jitter estimate (line width).

### 2.4 Context Encoder (geometry)
Builds `g` from: process image class (browser, updater, shell, unknown), parent process class, user role, host role (workstation, server, build machine), hour-of-week. v1 uses discrete buckets; v2 mixes baselines continuously.

### 2.5 Context Baseline
Per context bucket: distribution of the feature vector on benign data (mean and shrunk covariance; or an isolation-forest model). Known-periodic benign activity (software updaters, health checks, NTP) is learned as allowed lines, so they are not flagged.

### 2.6 Scorer
- **Anomaly score:** distance of the feature vector from the context baseline.
- **Beacon score:** significant periodicity not on the allowlist.
- **Family classifier (optional):** gradient-boosted trees on features when labels exist.
- Combined into a ranked alert with an explanation: channel, band, how far from baseline, and a spectrum plot.

### 2.7 Fleet correlation (v2)
Several hosts showing the same period toward the same destination is a stronger signal than one host; combine p-values across hosts.

## 3. Deployment modes

| Mode | Description |
|---|---|
| **Offline analyzer** | Reads exported logs (flow logs, auditd/eBPF traces) and writes reports; start here |
| **Sandbox scorer** | Scores behavior traces from an isolated analysis sandbox |
| **Streaming sidecar** | Rolling windows on a host or collector (later) |

## 4. Safeguards and ethics
1. Malware samples run only in isolated VMs with no production network access.
2. Spectra and features can be shared instead of raw logs (privacy).
3. Every alert carries an explanation and is reproducible from stored features.
4. Report false-positive volume per host per day, not only rates.

## 5. Design rules
1. Never rely on spectral features alone; keep non-spectral baselines in every comparison.
2. Evaluate evasion (jitter, sleeps, padding) from day one.
3. Split train and test by time and by malware family to avoid leakage.
