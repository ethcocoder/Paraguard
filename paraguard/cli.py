import argparse
import json
from pathlib import Path
import sys

from .analysis import analyze_events
from .io import read_events
from .validation import validate_periodicity


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="paraguard", description="Offline analysis of exported security event records")
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan = subparsers.add_parser("scan", help="analyze a CSV or JSON Lines event file")
    scan.add_argument("input", type=Path, help="input .csv, .jsonl, or .ndjson file")
    scan.add_argument("--output", type=Path, help="write the JSON report to this path")
    scan.add_argument("--bin-seconds", type=float, default=1.0)
    scan.add_argument("--min-period", type=float, default=2.0)
    scan.add_argument("--max-period", type=float, default=300.0)
    scan.add_argument("--frequency-count", type=int, default=256)
    scan.add_argument("--fdr", type=float, default=0.01)
    validate = subparsers.add_parser("validate", help="measure periodicity false positives on synthetic nulls")
    validate.add_argument("--trials", type=int, default=500)
    validate.add_argument("--events", type=int, default=32)
    validate.add_argument("--duration-seconds", type=float, default=600.0)
    validate.add_argument("--min-period", type=float, default=2.0)
    validate.add_argument("--max-period", type=float, default=60.0)
    validate.add_argument("--frequency-count", type=int, default=256)
    validate.add_argument("--alpha", type=float, default=0.01)
    validate.add_argument("--cluster-width-seconds", type=float, default=0.5)
    validate.add_argument("--groups-per-host-day", type=float)
    validate.add_argument("--seed", type=int, default=42)
    validate.add_argument("--output", type=Path, help="write the JSON report to this path")
    return parser


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "scan":
            report = analyze_events(
                read_events(args.input),
                bin_seconds=args.bin_seconds,
                min_period=args.min_period,
                max_period=args.max_period,
                frequency_count=args.frequency_count,
                fdr=args.fdr,
            )
        else:
            report = validate_periodicity(
                trials=args.trials,
                event_count=args.events,
                duration_seconds=args.duration_seconds,
                min_period=args.min_period,
                max_period=args.max_period,
                frequency_count=args.frequency_count,
                alpha=args.alpha,
                cluster_width_seconds=args.cluster_width_seconds,
                groups_per_host_day=args.groups_per_host_day,
                seed=args.seed,
            )
        rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
        if args.command == "validate" and report["status"] != "passed":
            return 1
    except (OSError, ValueError, TypeError) as error:
        parser.error(str(error))
    return 0