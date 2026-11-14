import unittest

from paraguard.validation import validate_periodicity
from paraguard.models import Event
from paraguard.validation import validate_benign_events


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

    def test_benign_log_validation_uses_chronological_holdout(self):
        events = [
            Event(float(timestamp), f"process-{group}", "network")
            for group in range(3)
            for timestamp in range(0, 200, 5)
        ]
        arguments = {
            "candidate_gaps": (0.5, 1.5),
            "train_fraction": 0.6,
            "min_period": 2.0,
            "max_period": 60.0,
            "frequency_count": 64,
            "surrogate_count": 39,
            "fdr": 0.05,
            "seed": 13,
        }

        first = validate_benign_events(events, **arguments)
        second = validate_benign_events(events, **arguments)

        self.assertEqual(first["group_counts"]["evaluated_groups"], 3)
        self.assertEqual(first["split_event_counts"], {"training": 72, "heldout": 48})
        self.assertEqual(first["configuration"]["selected_cluster_gap_seconds"],
                         second["configuration"]["selected_cluster_gap_seconds"])
        self.assertEqual(first["heldout"]["group_count"], 3)

    def test_walk_forward_folds_expand_training_and_hold_out_disjoint_windows(self):
        events = [
            Event(float(timestamp), f"process-{group}", "network")
            for group in range(2)
            for timestamp in range(0, 300, 5)
        ]

        report = validate_benign_events(
            events,
            candidate_gaps=(0.5, 1.5),
            train_fraction=0.6,
            folds=3,
            min_period=2.0,
            max_period=60.0,
            frequency_count=64,
            surrogate_count=39,
            fdr=0.05,
            seed=21,
        )

        self.assertEqual(report["configuration"]["folds_evaluated"], 3)
        training_counts = [fold["training_event_count"] for fold in report["fold_results"]]
        heldout_counts = [fold["heldout_event_count"] for fold in report["fold_results"]]
        self.assertEqual(training_counts, sorted(training_counts))
        self.assertTrue(all(count > 0 for count in heldout_counts))
        self.assertEqual(sum(heldout_counts), 48)
        self.assertEqual(report["heldout"]["group_fold_count"], 6)

    def test_validation_rejects_excessive_work(self):
        with self.assertRaisesRegex(ValueError, "work limit"):
            validate_periodicity(trials=1000, event_count=1000, frequency_count=1000)

    def test_cluster_empirical_calibration_controls_bursty_null(self):
        report = validate_periodicity(
            trials=40,
            event_count=20,
            duration_seconds=600.0,
            min_period=2.0,
            max_period=60.0,
            frequency_count=128,
            alpha=0.05,
            cluster_width_seconds=0.5,
            calibration_method="cluster_empirical",
            cluster_gap_seconds=1.5,
            surrogate_count=49,
            seed=42,
        )

        self.assertEqual(report["status"], "passed")
        self.assertLessEqual(report["bursty_null"]["false_positive_rate"], 0.15)
        self.assertGreaterEqual(report["periodic_positive_control"]["detection_rate"], 0.9)


if __name__ == "__main__":
    unittest.main()