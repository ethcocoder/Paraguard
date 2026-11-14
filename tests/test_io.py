import json
from pathlib import Path
import tempfile
import unittest

from paraguard.io import read_events


class InputTests(unittest.TestCase):
    def test_reads_json_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            path.write_text(json.dumps({"timestamp": 1, "process_id": "p1", "channel": "file"}) + "\n", encoding="utf-8")

            events = read_events(path)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].timestamp, 1.0)
        self.assertEqual(events[0].channel, "file")

    def test_reads_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.csv"
            path.write_text("timestamp,process_id,channel\n2,p2,network\n", encoding="utf-8")

            events = read_events(path)

        self.assertEqual(events[0].process_id, "p2")

    def test_rejects_malformed_json_line(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            path.write_text("not-json\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "line 1"):
                read_events(path)


if __name__ == "__main__":
    unittest.main()