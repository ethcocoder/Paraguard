import math

import numpy as np

from .periodicity import MAX_FREQUENCY_COUNT, empirical_cluster_test, rayleigh_scan


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