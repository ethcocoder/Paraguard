import unittest

import numpy as np

from paraguard.periodicity import benjamini_hochberg, empirical_cluster_test, rayleigh_scan


class PeriodicityTests(unittest.TestCase):
    def test_rayleigh_scan_finds_known_period(self):
        timestamps = np.arange(0.0, 120.0, 5.0)

        result = rayleigh_scan(timestamps, min_period=4.0, max_period=6.0, frequency_count=201)

        self.assertIsNotNone(result)
        self.assertAlmostEqual(result.period_seconds, 5.0, places=2)
        self.assertLess(result.scan_adjusted_p_value, 0.01)

    def test_empirical_cluster_test_detects_regular_events(self):
        timestamps = np.arange(0.0, 300.0, 5.0)

        result = empirical_cluster_test(
            timestamps,
            2.0,
            60.0,
            frequency_count=128,
            cluster_gap_seconds=1.5,
            surrogate_count=99,
            seed=23,
        )

        self.assertIsNotNone(result)
        self.assertLessEqual(result.p_value, 0.05)
        self.assertEqual(result.cluster_count, len(timestamps))

    def test_empirical_cluster_test_does_not_flag_one_burst(self):
        timestamps = np.array([10.0, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7])

        result = empirical_cluster_test(
            timestamps,
            2.0,
            60.0,
            frequency_count=128,
            cluster_gap_seconds=1.5,
            surrogate_count=99,
            seed=23,
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.cluster_count, 1)
        self.assertEqual(result.p_value, 1.0)

    def test_rayleigh_scan_skips_insufficient_or_zero_span_data(self):
        self.assertIsNone(rayleigh_scan([1.0, 1.0, 1.0, 1.0], 1.0, 2.0))
        self.assertIsNone(rayleigh_scan([1.0, 2.0, 3.0], 1.0, 2.0))

    def test_frequency_count_can_exceed_previous_limit(self):
        result = rayleigh_scan([0.0, 1.0, 2.0, 3.0], 1.0, 2.0, frequency_count=10_001)

        self.assertIsNotNone(result)
        self.assertEqual(result.tested_frequencies, 10_001)

    def test_frequency_count_remains_bounded(self):
        with self.assertRaisesRegex(ValueError, "100000"):
            rayleigh_scan([0.0, 1.0, 2.0, 3.0], 1.0, 2.0, frequency_count=100_001)

    def test_benjamini_hochberg_preserves_order_and_monotonicity(self):
        adjusted = benjamini_hochberg([0.04, 0.001, 0.02, 0.5])

        np.testing.assert_allclose(adjusted, [0.0533333333, 0.004, 0.04, 0.5])

    def test_invalid_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            rayleigh_scan([0.0, 1.0, float("nan"), 3.0], 1.0, 2.0)
        with self.assertRaises(ValueError):
            benjamini_hochberg([0.1, 1.1])


if __name__ == "__main__":
    unittest.main()