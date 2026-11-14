from dataclasses import dataclass
import math

import numpy as np


@dataclass(frozen=True)
class PeriodicityResult:
    event_count: int
    period_seconds: float
    resultant_length: float
    statistic: float
    raw_p_value: float
    scan_adjusted_p_value: float
    tested_frequencies: int


def rayleigh_scan(
    timestamps,
    min_period: float,
    max_period: float,
    frequency_count: int = 256,
) -> PeriodicityResult | None:
    if not math.isfinite(min_period) or not math.isfinite(max_period):
        raise ValueError("period bounds must be finite")
    if min_period <= 0 or max_period <= min_period:
        raise ValueError("period bounds must satisfy 0 < min_period < max_period")
    if type(frequency_count) is not int or not 2 <= frequency_count <= 10000:
        raise ValueError("frequency_count must be between 2 and 10000")

    times = np.asarray(timestamps, dtype=np.float64)
    if times.ndim != 1 or not np.all(np.isfinite(times)):
        raise ValueError("timestamps must be a one-dimensional finite sequence")
    if times.size < 4:
        return None
    times = np.sort(times)
    duration = float(times[-1] - times[0])
    if duration <= 0:
        return None
    times = times - times[0]

    frequencies = np.linspace(1.0 / max_period, 1.0 / min_period, frequency_count)
    best_resultant = -1.0
    best_frequency = float(frequencies[0])
    chunk_size = max(1, 1_000_000 // times.size)
    for start in range(0, frequencies.size, chunk_size):
        frequency_chunk = frequencies[start:start + chunk_size]
        phases = 2.0 * np.pi * frequency_chunk[:, None] * times[None, :]
        resultant = np.hypot(np.cos(phases).mean(axis=1), np.sin(phases).mean(axis=1))
        local_index = int(np.argmax(resultant))
        if resultant[local_index] > best_resultant:
            best_resultant = float(resultant[local_index])
            best_frequency = float(frequency_chunk[local_index])

    statistic = times.size * best_resultant**2
    raw_p_value = min(1.0, math.exp(-statistic))
    frequency_span = frequencies[-1] - frequencies[0]
    independent_frequencies = max(1.0, frequency_span * duration)
    adjusted_p_value = min(1.0, independent_frequencies * raw_p_value)
    return PeriodicityResult(
        event_count=int(times.size),
        period_seconds=1.0 / best_frequency,
        resultant_length=best_resultant,
        statistic=statistic,
        raw_p_value=raw_p_value,
        scan_adjusted_p_value=adjusted_p_value,
        tested_frequencies=int(frequencies.size),
    )


def benjamini_hochberg(p_values) -> list[float]:
    values = [float(value) for value in p_values]
    if any(not math.isfinite(value) or not 0.0 <= value <= 1.0 for value in values):
        raise ValueError("p-values must be finite values between 0 and 1")
    count = len(values)
    adjusted = [1.0] * count
    ranked = sorted(enumerate(values), key=lambda item: item[1])
    running_minimum = 1.0
    for rank in range(count, 0, -1):
        original_index, value = ranked[rank - 1]
        running_minimum = min(running_minimum, value * count / rank)
        adjusted[original_index] = min(1.0, running_minimum)
    return adjusted