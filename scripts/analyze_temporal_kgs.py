#!/usr/bin/env python3
"""
Compute descriptive statistics for the datasets stored under TemporalKGs.

Examples:
    python scripts/analyze_temporal_kgs.py
    python scripts/analyze_temporal_kgs.py --base-dir TemporalKGs --json-output stats.json
    python scripts/analyze_temporal_kgs.py --per-file --top-n 3
"""

import argparse
import json
import os
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, List, Optional


@dataclass
class Stats:
    """Holds running statistics for a KG split."""

    triples: int = 0
    subjects: set = field(default_factory=set)
    objects: set = field(default_factory=set)
    relations: set = field(default_factory=set)
    subject_counter: Counter = field(default_factory=Counter)
    object_counter: Counter = field(default_factory=Counter)
    entity_counter: Counter = field(default_factory=Counter)
    relation_counter: Counter = field(default_factory=Counter)
    year_counter: Counter = field(default_factory=Counter)
    temporal_marker_counter: Counter = field(default_factory=Counter)
    temporal_records: int = 0
    min_date: Optional[datetime.date] = None
    max_date: Optional[datetime.date] = None
    min_year: Optional[int] = None
    max_year: Optional[int] = None


def guess_dataset_type(dataset_name: str) -> str:
    name = dataset_name.lower()
    if "icews" in name:
        return "icews"
    if "wikidata" in name:
        return "wikidata"
    if "yago" in name:
        return "yago"
    return "generic"


def init_stats() -> Stats:
    return Stats()


def merge_stats(acc: Stats, other: Stats) -> None:
    acc.triples += other.triples
    acc.subjects.update(other.subjects)
    acc.objects.update(other.objects)
    acc.relations.update(other.relations)
    acc.subject_counter.update(other.subject_counter)
    acc.object_counter.update(other.object_counter)
    acc.entity_counter.update(other.entity_counter)
    acc.relation_counter.update(other.relation_counter)
    acc.year_counter.update(other.year_counter)
    acc.temporal_marker_counter.update(other.temporal_marker_counter)
    acc.temporal_records += other.temporal_records

    if other.min_date is not None:
        if acc.min_date is None or other.min_date < acc.min_date:
            acc.min_date = other.min_date
        if acc.max_date is None or (
            other.max_date is not None and other.max_date > acc.max_date
        ):
            acc.max_date = other.max_date

    if other.min_year is not None:
        if acc.min_year is None or other.min_year < acc.min_year:
            acc.min_year = other.min_year
        if acc.max_year is None or (other.max_year is not None and other.max_year > acc.max_year):
            acc.max_year = other.max_year


def parse_temporal_tokens(tokens: List[str], dataset_type: str, stats: Stats) -> None:
    if dataset_type == "icews":
        if len(tokens) >= 4:
            date_str = tokens[3]
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                return
            stats.year_counter[dt.year] += 1
            date_value = dt.date()
            if stats.min_date is None or date_value < stats.min_date:
                stats.min_date = date_value
            if stats.max_date is None or date_value > stats.max_date:
                stats.max_date = date_value
    elif dataset_type == "wikidata":
        if len(tokens) >= 5:
            marker = tokens[3]
            year_token = tokens[4].strip()
            stats.temporal_marker_counter[marker] += 1
            stats.temporal_records += 1
            if year_token:
                try:
                    year = int(year_token)
                except ValueError:
                    return
                stats.year_counter[year] += 1
                if stats.min_year is None or year < stats.min_year:
                    stats.min_year = year
                if stats.max_year is None or year > stats.max_year:
                    stats.max_year = year
    elif dataset_type == "yago":
        if len(tokens) >= 5:
            marker = tokens[3].strip("<>\"")
            date_token = tokens[4].strip("\"")
            stats.temporal_marker_counter[marker] += 1
            stats.temporal_records += 1
            digits = "".join(ch for ch in date_token if ch.isdigit())
            if len(digits) >= 4:
                year = int(digits[:4])
                stats.year_counter[year] += 1
                if stats.min_year is None or year < stats.min_year:
                    stats.min_year = year
                if stats.max_year is None or year > stats.max_year:
                    stats.max_year = year


def process_file(path: str, dataset_type: str) -> Stats:
    stats = init_stats()
    with open(path, "r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line:
                continue
            tokens = line.split("\t")
            if len(tokens) < 3:
                continue
            subj, rel, obj = tokens[0], tokens[1], tokens[2]
            stats.triples += 1
            stats.subjects.add(subj)
            stats.objects.add(obj)
            stats.relations.add(rel)
            stats.subject_counter[subj] += 1
            stats.object_counter[obj] += 1
            stats.entity_counter[subj] += 1
            stats.entity_counter[obj] += 1
            stats.relation_counter[rel] += 1
            parse_temporal_tokens(tokens, dataset_type, stats)
    return stats


def summarize(stats: Stats, top_n: int) -> Dict[str, object]:
    return {
        "triples": stats.triples,
        "unique_subjects": len(stats.subjects),
        "unique_objects": len(stats.objects),
        "unique_relations": len(stats.relations),
        "top_entities": stats.entity_counter.most_common(top_n),
        "top_subjects": stats.subject_counter.most_common(top_n),
        "top_objects": stats.object_counter.most_common(top_n),
        "top_relations": stats.relation_counter.most_common(top_n),
        "top_years": stats.year_counter.most_common(top_n),
        "temporal_markers": stats.temporal_marker_counter.most_common(top_n),
        "temporal_records": stats.temporal_records,
        "min_date": stats.min_date.isoformat() if stats.min_date else None,
        "max_date": stats.max_date.isoformat() if stats.max_date else None,
        "min_year": stats.min_year,
        "max_year": stats.max_year,
    }


def humanize(dataset_name: str, summary: Dict[str, object], top_n: int) -> List[str]:
    lines: List[str] = []
    lines.append(f"=== {dataset_name} ===")
    lines.append(
        f"Total triples: {summary['triples']:,}"
        + f"; unique subjects: {summary['unique_subjects']:,}"
        + f"; unique objects: {summary['unique_objects']:,}"
        + f"; relations: {summary['unique_relations']:,}"
    )
    if summary["top_entities"]:
        lines.append(
            "Top entities: "
            + ", ".join(f"{ent} ({cnt:,})" for ent, cnt in summary["top_entities"])
        )
    if summary["top_relations"]:
        lines.append(
            "Top relations: "
            + ", ".join(f"{rel} ({cnt:,})" for rel, cnt in summary["top_relations"])
        )
    if summary["top_years"]:
        lines.append(
            "Most active years: "
            + ", ".join(f"{year} ({cnt:,})" for year, cnt in summary["top_years"])
        )
    if summary["temporal_markers"]:
        lines.append(
            "Temporal markers: "
            + ", ".join(
                f"{marker} ({cnt:,})" for marker, cnt in summary["temporal_markers"]
            )
            + f"; with explicit temporal info: {summary['temporal_records']:,}"
        )
    if summary["min_date"] or summary["max_date"]:
        lines.append(f"Date range: {summary['min_date']} to {summary['max_date']}")
    if summary["min_year"] is not None or summary["max_year"] is not None:
        lines.append(f"Year span: {summary['min_year']} to {summary['max_year']}")
    return lines


def discover_datasets(base_dir: str, include: Optional[Iterable[str]]) -> List[str]:
    entries = sorted(
        name
        for name in os.listdir(base_dir)
        if os.path.isdir(os.path.join(base_dir, name))
    )
    if include:
        include_lower = {item.lower() for item in include}
        entries = [name for name in entries if name.lower() in include_lower]
    return entries


def analyze(base_dir: str, top_n: int, include: Optional[List[str]], per_file: bool):
    results: Dict[str, Dict[str, object]] = {}
    datasets = discover_datasets(base_dir, include)
    if not datasets:
        raise SystemExit(f"No dataset folders found under {base_dir}.")

    for dataset in datasets:
        dataset_dir = os.path.join(base_dir, dataset)
        dataset_type = guess_dataset_type(dataset)
        aggregate = init_stats()
        file_summaries: Dict[str, Dict[str, object]] = {}
        for filename in sorted(os.listdir(dataset_dir)):
            if not filename.endswith(".txt"):
                continue
            path = os.path.join(dataset_dir, filename)
            stats = process_file(path, dataset_type)
            merge_stats(aggregate, stats)
            if per_file:
                file_summaries[filename] = summarize(stats, top_n)
        results[dataset] = {
            "aggregate": summarize(aggregate, top_n),
            "files": file_summaries,
        }
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute descriptive statistics for TemporalKG datasets."
    )
    parser.add_argument(
        "--base-dir",
        default="TemporalKGs",
        help="Folder containing dataset subdirectories (default: TemporalKGs)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=5,
        help="Number of top entities/relations to report (default: 5)",
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        help="Optional subset of dataset folders to analyse (match by name).",
    )
    parser.add_argument(
        "--json-output",
        help="Optional path to write the full statistics as JSON.",
    )
    parser.add_argument(
        "--per-file",
        action="store_true",
        help="Include per-split summaries in the JSON output and console log.",
    )
    args = parser.parse_args()

    results = analyze(args.base_dir, args.top_n, args.datasets, args.per_file)

    for dataset, payload in results.items():
        lines = humanize(dataset, payload["aggregate"], args.top_n)
        print("\n".join(lines))
        if args.per_file and payload["files"]:
            for filename, summary in payload["files"].items():
                lines = humanize(f"{dataset}/{filename}", summary, args.top_n)
                print("  " + lines[0])
                for item in lines[1:]:
                    print("    " + item)
        print()

    if args.json_output:
        with open(args.json_output, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=2)


if __name__ == "__main__":
    main()
