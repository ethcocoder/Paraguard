from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from paraguard.cli import main


class CliTests(unittest.TestCase):
    def test_validate_returns_failure_and_writes_calibration_report(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "validation.json"

            exit_code = main([
                "validate",
                "--trials", "40",
                "--events", "20",
                "--alpha", "0.05",
                "--frequency-count", "128",
                "--groups-per-host-day", "1000",
                "--output", str(output_path),
            ])
            report = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 1)
        self.assertEqual(report["status"], "failed")
        self.assertGreater(report["bursty_null"]["false_positive_rate"], 0.5)

    def test_scan_writes_a_json_report(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "events.jsonl"
            output_path = Path(directory) / "report.json"
            records = [
                json.dumps({"timestamp": timestamp, "process_id": "p1", "channel": "network"})
                for timestamp in range(0, 100, 5)
            ]
            input_path.write_text("\n".join(records) + "\n", encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main([
                    "scan",
                    str(input_path),
                    "--min-period",
                    "4",
                    "--max-period",
                    "6",
                    "--frequency-count",
                    "201",
                    "--empirical-surrogates",
                    "199",
                    "--output",
                    str(output_path),
                ])

            report = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(len(report["alerts"]), 1)
        self.assertEqual(
            report["groups"][0]["periodicity"]["p_value_method"],
            "cluster-preserving empirical",
        )
        self.assertEqual(report["groups"][0]["periodicity"]["minimum_resolvable_p_value"], 0.005)


if __name__ == "__main__":
    unittest.main()