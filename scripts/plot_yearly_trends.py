#!/usr/bin/env python3
"""
Generate bar charts that show yearly triple counts for TemporalKG datasets.

Example:
    python scripts/plot_yearly_trends.py --output-dir figures/
    python scripts/plot_yearly_trends.py --datasets icews05-15 wikidata
"""

import argparse
import os
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List

try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError as exc:
    raise SystemExit(
        "matplotlib is required for this script. Install it with `pip install matplotlib`."
    ) from exc


def guess_dataset_type(dataset_name: str) -> str:
    name = dataset_name.lower()
    if "icews" in name:
        return "icews"
    if "wikidata" in name:
        return "wikidata"
    if "yago" in name:
        return "yago"
    return "generic"


def discover_datasets(base_dir: Path, include: Iterable[str]) -> List[str]:
    candidates = sorted(
        entry.name for entry in base_dir.iterdir() if entry.is_dir()
    )
    if include:
        include_lower = {name.lower() for name in include}
        candidates = [name for name in candidates if name.lower() in include_lower]
    return candidates


def year_counts_for_file(path: Path, dataset_type: str) -> Counter:
    counts: Counter = Counter()
    with path.open("r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line:
                continue
            tokens = line.split("\t")
            if dataset_type == "icews":
                if len(tokens) >= 4:
                    try:
                        year = datetime.strptime(tokens[3], "%Y-%m-%d").year
                    except ValueError:
                        continue
                    counts[year] += 1
            elif dataset_type == "wikidata":
                if len(tokens) >= 5:
                    try:
                        year = int(tokens[4].strip())
                    except ValueError:
                        continue
                    counts[year] += 1
            elif dataset_type == "yago":
                if len(tokens) >= 5:
                    digits = "".join(ch for ch in tokens[4] if ch.isdigit())
                    if len(digits) >= 4:
                        year = int(digits[:4])
                        counts[year] += 1
            else:
                if len(tokens) >= 4 and tokens[3].isdigit():
                    counts[int(tokens[3])] += 1
    return counts


def aggregate_year_counts(dataset_dir: Path, dataset_type: str) -> Counter:
    aggregate: Counter = Counter()
    for filename in sorted(dataset_dir.iterdir()):
        if filename.suffix != ".txt":
            continue
        aggregate.update(year_counts_for_file(filename, dataset_type))
    return aggregate


def plot_year_counts(dataset: str, counts: Counter, output_dir: Path) -> Path:
    years = sorted(counts)
    values = [counts[year] for year in years]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(years, values, width=0.8)
    ax.set_title(f"Yearly triple counts for {dataset}")
    ax.set_xlabel("Year")
    ax.set_ylabel("Triples")
    ax.set_xlim(min(years) - 1, max(years) + 1)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    output_path = output_dir / f"{dataset}_yearly_counts.png"
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot yearly triple counts for TemporalKG datasets."
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("TemporalKGs"),
        help="Folder containing dataset subdirectories (default: TemporalKGs).",
    )
    parser.add_argument(
        "--datasets",
        nargs="*",
        default=[],
        help="Optional list of dataset folders to plot (defaults to all).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("figures"),
        help="Directory where plots will be written (default: figures/).",
    )
    args = parser.parse_args()

    if not args.base_dir.exists():
        raise SystemExit(f"Base directory {args.base_dir} does not exist.")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    targets = discover_datasets(args.base_dir, args.datasets)
    if not targets:
        raise SystemExit("No matching dataset folders were found.")

    for dataset in targets:
        dataset_dir = args.base_dir / dataset
        dataset_type = guess_dataset_type(dataset)
        counts = aggregate_year_counts(dataset_dir, dataset_type)
        if not counts:
            print(f"[warn] Skipping {dataset}: no yearly information found.")
            continue
        output_path = plot_year_counts(dataset, counts, args.output_dir)
        print(f"[ok] Wrote {output_path}")


if __name__ == "__main__":
    main()
