import unittest

from paraguard.validation import validate_periodicity


class ValidationTests(unittest.TestCase):
    def test_seeded_validation_reveals_bursty_null_failure(self):
        report = validate_periodicity(
            trials=60,
            event_count=20,
            duration_seconds=600.0,
            min_period=2.0,
            max_period=60.0,
            frequency_count=128,
            alpha=0.05,
            groups_per_host_day=1000,
            seed=42,
        )

        self.assertEqual(report["status"], "failed")
        self.assertLess(report["uniform_null"]["false_positive_rate"], 0.15)
        self.assertGreater(report["bursty_null"]["false_positive_rate"], 0.5)
        self.assertIsNotNone(report["bursty_null"]["estimated_false_alerts_per_host_day"])
        self.assertGreaterEqual(report["periodic_positive_control"]["detection_rate"], 0.9)

    def test_validation_rejects_small_trial_count(self):
        with self.assertRaisesRegex(ValueError, "between 20 and 100000"):
            validate_periodicity(trials=19)

    def test_validation_rejects_excessive_work(self):
        with self.assertRaisesRegex(ValueError, "work limit"):
            validate_periodicity(trials=1000, event_count=1000, frequency_count=1000)


if __name__ == "__main__":
    unittest.main()