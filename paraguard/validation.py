import math
from collections import defaultdict

import numpy as np

from .models import Event
from .periodicity import (
    MAX_FREQUENCY_COUNT,
    benjamini_hochberg,
    empirical_cluster_test,
    rayleigh_scan,
)


MAX_VALIDATION_PHASE_EVALUATIONS = 100_000_000


def _wilson_interval(successes: int, trials: int) -> tuple[float, float]:
    z = 1.959963984540054
    proportion = successes / trials
    denominator = 1.0 + z * z / trials
    center = (proportion + z * z / (2.0 * trials)) / denominator
    margin = z * math.sqrt(
        proportion * (1.0 - proportion) / trials + z * z / (4.0 * trials * trials)
    ) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def validate_periodicity(
    *,
    trials: int = 500,
    event_count: int = 32,
    duration_seconds: float = 600.0,
    min_period: float = 2.0,
    max_period: float = 60.0,
    frequency_count: int = 256,
    alpha: float = 0.01,
    cluster_width_seconds: float = 0.5,
    calibration_method: str = "analytic",
    cluster_gap_seconds: float = 1.5,
    surrogate_count: int = 99,
    groups_per_host_day: float | None = None,
    seed: int = 42,
) -> dict:
    if type(trials) is not int or not 20 <= trials <= 100_000:
        raise ValueError("trials must be between 20 and 100000")
    if type(event_count) is not int or not 4 <= event_count <= 100_000:
        raise ValueError("event_count must be between 4 and 100000")
    if not math.isfinite(duration_seconds) or duration_seconds <= 0:
        raise ValueError("duration_seconds must be finite and positive")
    if not math.isfinite(min_period) or not math.isfinite(max_period):
        raise ValueError("period bounds must be finite")
    if min_period <= 0 or max_period <= min_period:
        raise ValueError("period bounds must satisfy 0 < min_period < max_period")
    if type(frequency_count) is not int or not 2 <= frequency_count <= MAX_FREQUENCY_COUNT:
        raise ValueError(f"frequency_count must be between 2 and {MAX_FREQUENCY_COUNT}")
    if not math.isfinite(alpha) or not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be between 0 and 1")
    if not math.isfinite(cluster_width_seconds) or cluster_width_seconds <= 0:
        raise ValueError("cluster_width_seconds must be finite and positive")
    if calibration_method not in {"analytic", "cluster_empirical"}:
        raise ValueError("calibration_method must be 'analytic' or 'cluster_empirical'")
    if not math.isfinite(cluster_gap_seconds) or cluster_gap_seconds <= 0:
        raise ValueError("cluster_gap_seconds must be finite and positive")
    if type(surrogate_count) is not int or not 20 <= surrogate_count <= 10_000:
        raise ValueError("surrogate_count must be between 20 and 10000")
    if groups_per_host_day is not None and (
        not math.isfinite(groups_per_host_day) or groups_per_host_day < 0
    ):
        raise ValueError("groups_per_host_day must be finite and nonnegative")
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    surrogate_multiplier = surrogate_count + 1 if calibration_method == "cluster_empirical" else 1
    estimated_work = trials * event_count * frequency_count * 3 * surrogate_multiplier
    if estimated_work > MAX_VALIDATION_PHASE_EVALUATIONS:
        raise ValueError(
            "validation exceeds the work limit; reduce trials, events, or frequency_count"
        )

    rng = np.random.default_rng(seed)
    uniform_false_positives = 0
    bursty_false_positives = 0
    periodic_detections = 0
    cluster_count = max(2, event_count // 4)

    def p_value_for(times, trial_index):
        if calibration_method == "cluster_empirical":
            result = empirical_cluster_test(
                times,
                min_period,
                max_period,
                frequency_count=frequency_count,
                cluster_gap_seconds=cluster_gap_seconds,
                surrogate_count=surrogate_count,
                seed=seed + trial_index,
            )
            return result.p_value if result is not None else 1.0
        result = rayleigh_scan(times, min_period, max_period, frequency_count)
        return result.scan_adjusted_p_value if result is not None else 1.0

    for trial_index in range(trials):
        uniform_times = rng.uniform(0.0, duration_seconds, event_count)
        if p_value_for(uniform_times, 3 * trial_index) <= alpha:
            uniform_false_positives += 1

        centers = rng.uniform(0.0, duration_seconds, cluster_count)
        bursty_times = (
            rng.choice(centers, event_count)
            + rng.normal(0.0, cluster_width_seconds, event_count)
        ) % duration_seconds
        if p_value_for(bursty_times, 3 * trial_index + 1) <= alpha:
            bursty_false_positives += 1

        period = rng.uniform(min_period, max_period)
        phase = rng.uniform(0.0, period)
        periodic_times = phase + period * np.arange(event_count, dtype=np.float64)
        if p_value_for(periodic_times, 3 * trial_index + 2) <= alpha:
            periodic_detections += 1

    mc_tolerance = 3.0 * math.sqrt(alpha * (1.0 - alpha) / trials)

    def null_summary(false_positives: int) -> dict:
        rate = false_positives / trials
        interval = _wilson_interval(false_positives, trials)
        return {
            "false_positives": false_positives,
            "false_positive_rate": rate,
            "wilson_95_interval": [interval[0], interval[1]],
            "within_monte_carlo_tolerance": interval[1] <= alpha + mc_tolerance,
            "estimated_false_alerts_per_host_day": (
                rate * groups_per_host_day if groups_per_host_day is not None else None
            ),
        }

    uniform = null_summary(uniform_false_positives)
    bursty = null_summary(bursty_false_positives)
    periodic_detection_rate = periodic_detections / trials
    passed = (
        uniform["within_monte_carlo_tolerance"]
        and bursty["within_monte_carlo_tolerance"]
        and periodic_detection_rate >= 0.9
    )
    return {
        "validation_version": 1,
        "status": "passed" if passed else "failed",
        "method": calibration_method,
        "synthetic_only": True,
        "configuration": {
            "trials": trials,
            "event_count_per_trial": event_count,
            "duration_seconds": duration_seconds,
            "min_period": min_period,
            "max_period": max_period,
            "frequency_count": frequency_count,
            "alpha": alpha,
            "cluster_count": cluster_count,
            "cluster_width_seconds": cluster_width_seconds,
            "cluster_gap_seconds": cluster_gap_seconds,
            "surrogate_count": surrogate_count if calibration_method == "cluster_empirical" else 0,
            "groups_per_host_day": groups_per_host_day,
            "seed": seed,
            "monte_carlo_tolerance": mc_tolerance,
        },
        "uniform_null": uniform,
        "bursty_null": bursty,
        "periodic_positive_control": {
            "detections": periodic_detections,
            "detection_rate": periodic_detection_rate,
            "passed": periodic_detection_rate >= 0.9,
        },
        "limitations": [
            "Synthetic calibration does not establish false-positive rates on real benign telemetry.",
            "The bursty null preserves local clusters but randomizes cluster centers; other dependence structures may differ.",
            "A false-alerts-per-host-day estimate is only provided when groups_per_host_day is explicitly supplied.",
        ],
        "recommendation": (
            "Do not interpret analytic Rayleigh p-values as calibrated for bursty event groups; validate against representative benign logs or use an empirically calibrated null."
            if not bursty["within_monte_carlo_tolerance"]
            else "Synthetic null checks passed; validate against representative benign logs before operational use."
        ),
    }


def validate_benign_events(
    events,
    *,
    candidate_gaps=(0.5, 1.0, 1.5, 2.0),
    train_fraction: float = 0.6,
    min_period: float = 2.0,
    max_period: float = 60.0,
    frequency_count: int = 256,
    surrogate_count: int = 199,
    fdr: float = 0.01,
    groups_per_host_day: float | None = None,
    seed: int = 42,
) -> dict:
    gaps = tuple(float(gap) for gap in candidate_gaps)
    if not gaps or any(not math.isfinite(gap) or gap <= 0 for gap in gaps):
        raise ValueError("candidate_gaps must contain finite positive values")
    if len(set(gaps)) != len(gaps):
        raise ValueError("candidate_gaps must be unique")
    if not math.isfinite(train_fraction) or not 0.5 <= train_fraction <= 0.9:
        raise ValueError("train_fraction must be between 0.5 and 0.9")
    if not math.isfinite(min_period) or not math.isfinite(max_period):
        raise ValueError("period bounds must be finite")
    if min_period <= 0 or max_period <= min_period:
        raise ValueError("period bounds must satisfy 0 < min_period < max_period")
    if type(frequency_count) is not int or not 2 <= frequency_count <= MAX_FREQUENCY_COUNT:
        raise ValueError(f"frequency_count must be between 2 and {MAX_FREQUENCY_COUNT}")
    if type(surrogate_count) is not int or not 20 <= surrogate_count <= 10_000:
        raise ValueError("surrogate_count must be between 20 and 10000")
    if not math.isfinite(fdr) or not 0.0 < fdr <= 1.0:
        raise ValueError("fdr must be between 0 and 1")
    if groups_per_host_day is not None and (
        not math.isfinite(groups_per_host_day) or groups_per_host_day < 0
    ):
        raise ValueError("groups_per_host_day must be finite and nonnegative")
    if type(seed) is not int:
        raise ValueError("seed must be an integer")

    grouped = defaultdict(list)
    for event in events:
        if not isinstance(event, Event):
            raise TypeError("events must contain Event objects")
        grouped[(event.process_id, event.channel)].append(event.timestamp)

    split_groups = []
    skipped_groups = 0
    for (process_id, channel), raw_times in sorted(grouped.items()):
        times = np.sort(np.asarray(raw_times, dtype=np.float64))
        split_at = int(len(times) * train_fraction)
        if split_at < 4 or len(times) - split_at < 4:
            skipped_groups += 1
            continue
        training_times = times[:split_at]
        heldout_times = times[split_at:]
        if training_times[-1] <= training_times[0] or heldout_times[-1] <= heldout_times[0]:
            skipped_groups += 1
            continue
        split_groups.append({
            "process_id": process_id,
            "channel": channel,
            "training_times": training_times,
            "heldout_times": heldout_times,
        })

    if not split_groups:
        raise ValueError("no process-channel groups have enough distinct events for both time splits")

    total_events = sum(
        len(group["training_times"]) + len(group["heldout_times"])
        for group in split_groups
    )
    estimated_work = total_events * len(gaps) * (surrogate_count + 1) * frequency_count
    if estimated_work > MAX_VALIDATION_PHASE_EVALUATIONS:
        raise ValueError("real-log validation exceeds the work limit; reduce gaps, surrogates, or frequency_count")

    def score_segment(segment_key: str, gap: float, gap_index: int) -> list[dict]:
        rows = []
        p_values = []
        for group_index, group in enumerate(split_groups):
            result = empirical_cluster_test(
                group[segment_key],
                min_period,
                max_period,
                frequency_count=frequency_count,
                cluster_gap_seconds=gap,
                surrogate_count=surrogate_count,
                seed=seed + gap_index * 1_000_003 + group_index,
            )
            p_value = result.p_value if result is not None else 1.0
            p_values.append(p_value)
            rows.append({
                "process_id": group["process_id"],
                "channel": group["channel"],
                "event_count": int(len(group[segment_key])),
                "p_value": p_value,
                "cluster_count": result.cluster_count if result is not None else 0,
            })
        q_values = benjamini_hochberg(p_values)
        for row, q_value in zip(rows, q_values):
            row["q_value"] = q_value
            row["alert"] = q_value <= fdr
        return rows

    training_candidates = []
    for gap_index, gap in enumerate(gaps):
        rows = score_segment("training_times", gap, gap_index)
        alert_rate = sum(row["alert"] for row in rows) / len(rows)
        training_candidates.append({
            "cluster_gap_seconds": gap,
            "training_alerts": int(sum(row["alert"] for row in rows)),
            "training_group_count": len(rows),
            "training_alert_rate": alert_rate,
        })
    selected_index = min(
        range(len(training_candidates)),
        key=lambda index: (
            abs(training_candidates[index]["training_alert_rate"] - fdr),
            training_candidates[index]["cluster_gap_seconds"],
        ),
    )
    selected_gap = training_candidates[selected_index]["cluster_gap_seconds"]
    heldout_rows = score_segment("heldout_times", selected_gap, selected_index + len(gaps))
    heldout_alerts = sum(row["alert"] for row in heldout_rows)
    heldout_count = len(heldout_rows)
    alert_rate = heldout_alerts / heldout_count
    interval = _wilson_interval(heldout_alerts, heldout_count)

    return {
        "validation_version": 1,
        "status": "evaluated",
        "data_source": "user-supplied benign event log",
        "split_method": "chronological within each process-channel group",
        "configuration": {
            "train_fraction": train_fraction,
            "candidate_gaps_seconds": list(gaps),
            "selected_cluster_gap_seconds": selected_gap,
            "min_period": min_period,
            "max_period": max_period,
            "frequency_count": frequency_count,
            "surrogate_count": surrogate_count,
            "fdr": fdr,
            "groups_per_host_day": groups_per_host_day,
            "seed": seed,
        },
        "group_counts": {
            "total_input_groups": len(grouped),
            "evaluated_groups": len(split_groups),
            "skipped_groups": skipped_groups,
        },
        "split_event_counts": {
            "training": int(sum(len(group["training_times"]) for group in split_groups)),
            "heldout": int(sum(len(group["heldout_times"]) for group in split_groups)),
        },
        "training_gap_selection": training_candidates,
        "heldout": {
            "alert_count": int(heldout_alerts),
            "group_count": heldout_count,
            "alert_rate": alert_rate,
            "wilson_95_interval": [interval[0], interval[1]],
            "estimated_false_alerts_per_host_day": (
                alert_rate * groups_per_host_day if groups_per_host_day is not None else None
            ),
            "groups": heldout_rows,
        },
        "limitations": [
            "The input is treated as benign; mislabeled or mixed telemetry invalidates the false-alert interpretation.",
            "The selected gap is tuned on the chronological training segment and evaluated once on the held-out segment.",
            "The estimate is per process-channel group; host identifiers and fleet-level dependencies are not modeled.",
            "One held-out interval does not establish stability across seasons, software changes, or hosts.",
        ],
    }