import csv
import json
from pathlib import Path
from typing import Iterator

from .models import Event


def read_events(path: str | Path) -> list[Event]:
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix == ".csv":
        records = _read_csv(source)
    elif suffix in {".jsonl", ".ndjson"}:
        records = _read_json_lines(source)
    else:
        raise ValueError("input must be a .csv, .jsonl, or .ndjson file")
    return [Event.from_mapping(record) for record in records]


def _read_csv(path: Path) -> Iterator[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        required = {"timestamp", "process_id", "channel"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError("CSV needs timestamp, process_id, and channel columns")
        for line_number, record in enumerate(reader, start=2):
            try:
                yield record
            except csv.Error as error:
                raise ValueError(f"invalid CSV record at line {line_number}") from error


def _read_json_lines(path: Path) -> Iterator[dict]:
    with path.open("r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid JSON at line {line_number}") from error
            if not isinstance(record, dict):
                raise ValueError(f"event at line {line_number} must be a JSON object")
            yield record