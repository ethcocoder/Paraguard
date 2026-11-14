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

    def test_validate_log_reads_jsonl_and_writes_heldout_report(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "benign.jsonl"
            output_path = Path(directory) / "heldout.json"
            records = [
                json.dumps({"timestamp": timestamp, "process_id": f"p{group}", "channel": "network"})
                for group in range(2)
                for timestamp in range(0, 200, 5)
            ]
            input_path.write_text("\n".join(records) + "\n", encoding="utf-8")

            exit_code = main([
                "validate-log", str(input_path),
                "--candidate-gaps", "0.5", "1.5",
                "--train-fraction", "0.6",
                "--min-period", "2", "--max-period", "60",
                "--frequency-count", "64", "--surrogates", "39",
                "--fdr", "0.05", "--output", str(output_path),
            ])
            report = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(report["split_method"], "chronological within each process-channel group")
        self.assertEqual(report["split_event_counts"], {"training": 48, "heldout": 32})


if __name__ == "__main__":
    unittest.main()