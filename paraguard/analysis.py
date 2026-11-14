import math
from collections import defaultdict

import numpy as np

from .features import spectral_features
from .models import Event
from .periodicity import (
    MAX_FREQUENCY_COUNT,
    benjamini_hochberg,
    empirical_cluster_test,
    rayleigh_scan,
)


MAX_EMPIRICAL_SCAN_WORK = 100_000_000


def analyze_events(
    events,
    *,
    bin_seconds: float = 1.0,
    min_period: float = 2.0,
    max_period: float = 300.0,
    frequency_count: int = 256,
    fdr: float = 0.01,
    empirical_surrogates: int = 0,
    cluster_gap_seconds: float = 1.5,
    random_seed: int = 42,
) -> dict:
    if not math.isfinite(bin_seconds) or bin_seconds <= 0:
        raise ValueError("bin_seconds must be finite and positive")
    if not math.isfinite(fdr) or not 0.0 < fdr <= 1.0:
        raise ValueError("fdr must be between 0 and 1")
    if type(frequency_count) is not int or not 2 <= frequency_count <= MAX_FREQUENCY_COUNT:
        raise ValueError(f"frequency_count must be between 2 and {MAX_FREQUENCY_COUNT}")
    if type(empirical_surrogates) is not int or (
        empirical_surrogates != 0 and not 20 <= empirical_surrogates <= 10_000
    ):
        raise ValueError("empirical_surrogates must be 0 or between 20 and 10000")
    if not math.isfinite(cluster_gap_seconds) or cluster_gap_seconds <= 0:
        raise ValueError("cluster_gap_seconds must be finite and positive")
    if type(random_seed) is not int:
        raise ValueError("random_seed must be an integer")

    grouped = defaultdict(list)
    event_count = 0
    for event in events:
        if not isinstance(event, Event):
            raise TypeError("events must contain Event objects")
        grouped[(event.process_id, event.channel)].append(event.timestamp)
        event_count += 1

    empirical_work = sum(map(len, grouped.values())) * empirical_surrogates * frequency_count
    if empirical_work > MAX_EMPIRICAL_SCAN_WORK:
        raise ValueError("empirical scan exceeds the work limit; reduce groups, surrogates, or frequency_count")

    groups = []
    p_values = []
    for group_index, ((process_id, channel), raw_times) in enumerate(sorted(grouped.items())):
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
        empirical = None
        if periodicity is not None and empirical_surrogates:
            empirical = empirical_cluster_test(
                times,
                min_period=min_period,
                max_period=max_period,
                frequency_count=frequency_count,
                cluster_gap_seconds=cluster_gap_seconds,
                surrogate_count=empirical_surrogates,
                seed=random_seed + group_index,
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
            selected_p_value = (
                empirical.p_value if empirical is not None else periodicity.scan_adjusted_p_value
            )
            p_values.append(selected_p_value)
            result["periodicity"] = {
                "period_seconds": periodicity.period_seconds,
                "resultant_length": periodicity.resultant_length,
                "statistic": periodicity.statistic,
                "raw_p_value": periodicity.raw_p_value,
                "scan_adjusted_p_value": periodicity.scan_adjusted_p_value,
                "p_value": selected_p_value,
                "p_value_method": (
                    "cluster-preserving empirical" if empirical is not None else "analytic scan correction"
                ),
                "surrogate_count": empirical.surrogate_count if empirical is not None else 0,
                "minimum_resolvable_p_value": (
                    1.0 / (empirical.surrogate_count + 1) if empirical is not None else None
                ),
                "cluster_count": empirical.cluster_count if empirical is not None else None,
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
            "empirical_surrogates": empirical_surrogates,
            "cluster_gap_seconds": cluster_gap_seconds,
            "random_seed": random_seed,
        },
        "groups": groups,
        "alerts": alerts,
        "limitations": [
            "Analytic Rayleigh scan p-values use an asymptotic approximation and can be miscalibrated for bursty or dependent events.",
            "Cluster-preserving empirical p-values depend on the selected inter-event gap threshold and exchangeable cluster placement.",
            "Empirical p-value resolution is 1/(surrogates + 1); too few surrogates can prevent significance after Benjamini-Hochberg correction.",
            "No context baseline, benign-period allowlist, or validated benchmark is included.",
            "Results are research indicators and require analyst review.",
        ],
    }