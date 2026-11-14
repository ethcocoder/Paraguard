import math

import numpy as np


def spectral_features(signal, sample_rate: float) -> dict:
    values = np.asarray(signal, dtype=np.float64)
    if values.ndim != 1 or not np.all(np.isfinite(values)):
        raise ValueError("signal must be a one-dimensional finite sequence")
    if not math.isfinite(sample_rate) or sample_rate <= 0:
        raise ValueError("sample_rate must be finite and positive")

    empty = {
        "peak_frequency_hz": 0.0,
        "peak_to_average_ratio": 0.0,
        "spectral_flatness": 0.0,
        "spectral_entropy": 0.0,
        "spectral_centroid_hz": 0.0,
        "rolloff_85_hz": 0.0,
        "harmonic_ratio": 0.0,
        "total_power": 0.0,
        "octave_band_energy": {},
    }
    if values.size < 3:
        return empty

    centered = values - values.mean()
    window = np.hanning(values.size)
    power = np.abs(np.fft.rfft(centered * window)) ** 2
    frequencies = np.fft.rfftfreq(values.size, d=1.0 / sample_rate)
    power = power[1:]
    frequencies = frequencies[1:]
    total_power = float(power.sum())
    if total_power <= np.finfo(np.float64).tiny:
        return empty

    peak_index = int(np.argmax(power))
    peak_power = float(power[peak_index])
    peak_frequency = float(frequencies[peak_index])
    mean_power = float(power.mean())
    probabilities = power / total_power
    nonzero = probabilities > 0
    entropy = -float(np.sum(probabilities[nonzero] * np.log(probabilities[nonzero])))
    if probabilities.size > 1:
        entropy /= math.log(probabilities.size)

    octave_indices = np.floor(np.log2(frequencies / frequencies[0])).astype(int)
    band_energy = {
        f"octave_{band}": float(power[octave_indices == band].sum())
        for band in range(int(octave_indices.max()) + 1)
    }
    harmonic_power = 0.0
    for multiple in range(2, 5):
        target = peak_frequency * multiple
        if target <= frequencies[-1]:
            harmonic_index = int(np.argmin(np.abs(frequencies - target)))
            harmonic_power += float(power[harmonic_index])

    rolloff_index = int(np.searchsorted(np.cumsum(power), 0.85 * total_power))
    return {
        "peak_frequency_hz": peak_frequency,
        "peak_to_average_ratio": peak_power / mean_power,
        "spectral_flatness": float(np.exp(np.mean(np.log(np.maximum(power, np.finfo(float).tiny)))) / mean_power),
        "spectral_entropy": entropy,
        "spectral_centroid_hz": float(np.sum(frequencies * probabilities)),
        "rolloff_85_hz": float(frequencies[min(rolloff_index, frequencies.size - 1)]),
        "harmonic_ratio": harmonic_power / peak_power,
        "total_power": total_power,
        "octave_band_energy": band_energy,
    }