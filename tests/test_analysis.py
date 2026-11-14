import unittest

from paraguard.analysis import analyze_events
from paraguard.models import Event


class AnalysisTests(unittest.TestCase):
    def test_analysis_reports_periodic_group_with_explanation(self):
        events = [Event(float(timestamp), "worker-1", "network") for timestamp in range(0, 100, 5)]

        report = analyze_events(
            events,
            min_period=4.0,
            max_period=6.0,
            frequency_count=201,
        )

        self.assertEqual(report["analysis_mode"], "offline")
        self.assertEqual(report["group_count"], 1)
        self.assertEqual(len(report["alerts"]), 1)
        self.assertIn("period", report["alerts"][0]["explanation"])
        self.assertIn("peak_frequency_hz", report["groups"][0]["spectral_features"])

    def test_empty_input_produces_empty_report(self):
        report = analyze_events([])

        self.assertEqual(report["event_count"], 0)
        self.assertEqual(report["groups"], [])
        self.assertEqual(report["alerts"], [])


if __name__ == "__main__":
    unittest.main()