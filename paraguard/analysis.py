import math
from collections import defaultdict

import numpy as np

from .features import spectral_features
from .models import Event
from .periodicity import benjamini_hochberg, rayleigh_scan


def analyze_events(
    events,
    *,
    bin_seconds: float = 1.0,
    min_period: float = 2.0,
    max_period: float = 300.0,
    frequency_count: int = 256,
    fdr: float = 0.01,
) -> dict:
    if not math.isfinite(bin_seconds) or bin_seconds <= 0:
        raise ValueError("bin_seconds must be finite and positive")
    if not math.isfinite(fdr) or not 0.0 < fdr <= 1.0:
        raise ValueError("fdr must be between 0 and 1")

    grouped = defaultdict(list)
    event_count = 0
    for event in events:
        if not isinstance(event, Event):
            raise TypeError("events must contain Event objects")
        grouped[(event.process_id, event.channel)].append(event.timestamp)
        event_count += 1

    groups = []
    p_values = []
    for (process_id, channel), raw_times in sorted(grouped.items()):
        times = np.sort(np.asarray(raw_times, dtype=np.float64))
        start = math.floor(float(times[0]) / bin_seconds) * bin_seconds
        bin_indexes = np.floor((times - start) / bin_seconds).astype(np.int64)
        counts = np.bincount(bin_indexes)
        periodicity = rayleigh_scan(
            times,
            min_period=min_period,
            max_period=max_period,
            frequency_count=frequency_count,
        )
        result = {
            "process_id": process_id,
            "channel": channel,
            "event_count": int(times.size),
            "start_timestamp": float(times[0]),
            "end_timestamp": float(times[-1]),
            "spectral_features": spectral_features(counts, 1.0 / bin_seconds),
            "periodicity": None,
        }
        if periodicity is not None:
            p_values.append(periodicity.scan_adjusted_p_value)
            result["periodicity"] = {
                "period_seconds": periodicity.period_seconds,
                "resultant_length": periodicity.resultant_length,
                "statistic": periodicity.statistic,
                "raw_p_value": periodicity.raw_p_value,
                "scan_adjusted_p_value": periodicity.scan_adjusted_p_value,
                "tested_frequencies": periodicity.tested_frequencies,
                "q_value": None,
                "significant": False,
            }
        groups.append(result)

    eligible = [group for group in groups if group["periodicity"] is not None]
    q_values = benjamini_hochberg(p_values)
    alerts = []
    for group, q_value in zip(eligible, q_values):
        group["periodicity"]["q_value"] = q_value
        group["periodicity"]["significant"] = q_value <= fdr
        if q_value <= fdr:
            alerts.append({
                "process_id": group["process_id"],
                "channel": group["channel"],
                "period_seconds": group["periodicity"]["period_seconds"],
                "q_value": q_value,
                "explanation": (
                    f"Recurring {group['channel']} events were detected at an estimated "
                    f"period of {group['periodicity']['period_seconds']:.3g} seconds."
                ),
            })

    return {
        "schema_version": 1,
        "analysis_mode": "offline",
        "event_count": event_count,
        "group_count": len(groups),
        "configuration": {
            "bin_seconds": bin_seconds,
            "min_period": min_period,
            "max_period": max_period,
            "frequency_count": frequency_count,
            "fdr": fdr,
        },
        "groups": groups,
        "alerts": alerts,
        "limitations": [
            "Rayleigh p-values use an asymptotic approximation and are not calibrated for bursty events.",
            "No context baseline, benign-period allowlist, or validated benchmark is included.",
            "Results are research indicators and require analyst review.",
        ],
    }