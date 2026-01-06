#!/usr/bin/env python3
"""Prepare ICEWS data into a single clean CSV."""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path


def iter_icews_rows(paths):
    for path in paths:
        split = path.stem.split("_")[-1]
        with path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            for row in reader:
                if len(row) != 4:
                    continue
                head, rel, tail, date_str = row
                try:
                    dt = datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    continue
                yield {
                    "head": head,
                    "relation": rel,
                    "tail": tail,
                    "date": date_str,
                    "year": dt.year,
                    "month": dt.month,
                    "day": dt.day,
                    "split": split,
                }


def build_date_index(rows):
    dates = sorted({row["date"] for row in rows})
    return {date: idx for idx, date in enumerate(dates)}


def main():
    parser = argparse.ArgumentParser(
        description="Combine ICEWS train/valid/test into a clean CSV."
    )
    parser.add_argument(
        "--source-dir",
        default="TemporalKGs/icews05-15_2014_combined",
        help="Directory containing ICEWS .txt files.",
    )
    parser.add_argument(
        "--out",
        default="RCS/data/ICEWS_clean.csv",
        help="Output CSV path.",
    )
    parser.add_argument(
        "--summary-out",
        default="RCS/data/ICEWS_summary.json",
        help="Output JSON summary path.",
    )
    args = parser.parse_args()

    source_dir = Path(args.source_dir)
    paths = sorted(source_dir.glob("*.txt"))
    if not paths:
        raise SystemExit(f"No .txt files found in {source_dir}")

    rows = list(iter_icews_rows(paths))
    date_index = build_date_index(rows)

    entities = set()
    relations = set()
    events_per_year = {}
    split_counts = {}
    for row in rows:
        entities.add(row["head"])
        entities.add(row["tail"])
        relations.add(row["relation"])
        events_per_year[row["year"]] = events_per_year.get(row["year"], 0) + 1
        split_counts[row["split"]] = split_counts.get(row["split"], 0) + 1

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "head",
        "relation",
        "tail",
        "date",
        "year",
        "month",
        "day",
        "date_index",
        "split",
    ]
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            row["date_index"] = date_index[row["date"]]
            writer.writerow(row)

    print(f"Wrote {len(rows)} rows to {out_path}")
    print(f"Entities: {len(entities)}")
    print(f"Relations: {len(relations)}")
    for year in sorted(events_per_year):
        print(f"Events {year}: {events_per_year[year]}")
    for split in sorted(split_counts):
        print(f"Split {split}: {split_counts[split]}")

    summary_path = Path(args.summary_out)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "rows": len(rows),
        "entities": len(entities),
        "relations": len(relations),
        "events_per_year": {str(k): v for k, v in sorted(events_per_year.items())},
        "split_counts": dict(sorted(split_counts.items())),
        "source_dir": str(source_dir),
        "out_csv": str(out_path),
    }
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Wrote summary to {summary_path}")


if __name__ == "__main__":
    main()
