# Paraguard

> *para* + *guard*: malware and intrusion detection based on the spectrum of a program's behavior.

Paraguard turns security telemetry (syscalls, file activity, network events, process spawns) into time signals, extracts each process's **spectral fingerprint**, and flags behavior whose fingerprint is new for that context. Its sharpest tool is a statistically rigorous **periodicity test**, because command-and-control beaconing, scheduled exfiltration and some ransomware phases leave regular rhythms in time.

**Scope:** defensive detection only. Any malware analysis must happen in isolated lab environments, never on production systems.

## The problem

- Signature and rule-based detection is easy to evade (packing, polymorphism, renamed binaries).
- Sequence-based behavior models (API-call n-grams) are brittle: attackers can insert harmless calls.
- Security teams face a **base-rate problem**: even a 0.1% false-positive rate on millions of daily events produces more alerts than analysts can read.

## Core idea

1. **Signals, not sequences:** per process and channel (file, network, process, memory, registry), count events per time bin.
2. **Spectral features:** peak frequency, peak-to-average ratio, spectral flatness, spectral entropy, band energies, cross-channel coherence.
3. **Rigorous periodicity test** for event timestamps (Rayleigh test with multiple-testing control) to find beacons without binning artifacts.
4. **Context baselines (geometry):** what is normal depends on the application, user role, host role and time of day.

## String theory mapping

| String theory | Paraguard |
|---|---|
| Vibration modes identify particles | Spectral modes identify behaviors (a beacon is a line; bulk encryption is sustained broadband energy) |
| Compact dimensions set allowed vibrations | **Geometry** = context (app, user, host role, time) selects the baseline spectrum that counts as normal |
| Resonance | Coherence between channels (read, write, rename) reveals coupled activity |
| Duality | Time view for "when", spectrum view for "what kind" |

## What is claimed as new

1. A **single spectral feature layer** across host and network channels, with context-conditioned baselines.
2. **Cross-channel coherence** as a behavioral feature (for example read-write-rename coupling).
3. **Significance-controlled periodicity alerts** (false discovery rate control) instead of ad hoc thresholds.
4. **Evasion-aware evaluation** built in from the start (jitter, sleeps, benign padding).

## Honest status

Prior art is large: statistical and frequency-based **beacon detection** (for example in network-analysis tools), dynamic malware analysis in sandboxes, API-call and syscall sequence models, EDR behavioral engines. Attackers already add **jitter** and sleeps, which broaden or flatten spectral lines. Paraguard is most credible as a **complementary feature layer** that must show measurable gains over strong non-spectral baselines, and must report robustness honestly. See `EXPERIMENTS.md`.

## Documentation map

| File | Purpose |
|---|---|
| `README.md` | This overview |
| `ARCHITECTURE.md` | Pipeline and components |
| `MATH_SPEC.md` | Signals, features, periodicity tests, baselines |
| `IMPLEMENTATION_PLAN.md` | Build order and Python skeleton |
| `EXPERIMENTS.md` | Datasets, baselines, evasion tests, success criteria |
| `ROADMAP.md` | Phases, risks, product directions |
