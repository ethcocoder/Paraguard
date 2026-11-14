import unittest

import numpy as np

from paraguard.features import spectral_features


class FeatureTests(unittest.TestCase):
    def test_spectral_peak_tracks_a_sinusoid(self):
        sample_rate = 1.0
        samples = np.arange(256)
        signal = np.sin(2 * np.pi * samples / 16)

        features = spectral_features(signal, sample_rate)

        self.assertAlmostEqual(features["peak_frequency_hz"], 1 / 16, places=2)
        self.assertGreater(features["peak_to_average_ratio"], 10.0)

    def test_constant_signal_has_finite_zero_energy_features(self):
        features = spectral_features(np.ones(32), sample_rate=1.0)

        self.assertEqual(features["total_power"], 0.0)
        self.assertTrue(np.isfinite(features["spectral_entropy"]))


if __name__ == "__main__":
    unittest.main()