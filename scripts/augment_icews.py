#!/usr/bin/env python3
"""
Create augmented variants of ICEWS temporal KG splits.

Currently supports two augmentation variants for ICEWS05-15:

1. icews05-15_aug_inverse
   - Adds inverse triples with relation suffix "_INV".

2. icews05-15_aug_inverse_time
   - Adds inverse triples, plus time-bucketed relation variants per year
     (relation name gets suffix "_YEAR_<YYYY>").

Usage:
    python scripts/augment_icews.py --dataset icews05-15
"""

from __future__ import annotations

import argparse
import os
from collections import defaultdict
from datetime import datetime
from typing import Dict, Iterable, List, Sequence, Tuple


Triple = Tuple[str, str, str, str]


def read_split(path: str) -> List[Triple]:
    triples: List[Triple] = []
    with open(path, "r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 4:
                continue
            triples.append((parts[0], parts[1], parts[2], parts[3]))
    return triples


def write_split(triples: Iterable[Triple], path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for s, r, o, t in triples:
            fh.write(f"{s}\t{r}\t{o}\t{t}\n")


def add_inverse_triples(triples: Iterable[Triple]) -> List[Triple]:
    inverse: List[Triple] = []
    for s, r, o, t in triples:
        inv_rel = f"{r}_INV"
        inverse.append((o, inv_rel, s, t))
    return inverse


def add_timebucket_triples(triples: Iterable[Triple], bucket: str = "year") -> List[Triple]:
    augmented: List[Triple] = []
    for s, r, o, t in triples:
        try:
            dt = datetime.strptime(t, "%Y-%m-%d")
        except ValueError:
            # Skip malformed dates.
            continue
        if bucket == "year":
            tag = f"YEAR_{dt.year}"
        elif bucket == "quarter":
            quarter = (dt.month - 1) // 3 + 1
            tag = f"Q{quarter}_{dt.year}"
        elif bucket == "month":
            tag = f"MONTH_{dt.year}-{dt.month:02d}"
        else:
            raise ValueError(f"Unsupported time bucket: {bucket}")
        rel_with_time = f"{r}_{tag}"
        augmented.append((s, rel_with_time, o, t))
    return augmented


def apply_augmentations(base_triples: List[Triple], augmentations: Sequence[str]) -> List[Triple]:
    augmented = list(base_triples)
    for aug in augmentations:
        if aug == "inverse":
            augmented.extend(add_inverse_triples(base_triples))
        elif aug == "time_year":
            augmented.extend(add_timebucket_triples(base_triples, bucket="year"))
        elif aug == "time_quarter":
            augmented.extend(add_timebucket_triples(base_triples, bucket="quarter"))
        elif aug == "time_month":
            augmented.extend(add_timebucket_triples(base_triples, bucket="month"))
        else:
            raise ValueError(f"Unknown augmentation: {aug}")
    return augmented


def get_dataset_prefix(dataset: str) -> str:
    if dataset == "icews05-15":
        return "icews_2005-2015"
    if dataset == "icews14":
        return "icews_2014"
    raise ValueError(f"Unsupported dataset: {dataset}")


def summarize(triples: Sequence[Triple]) -> Dict[str, int]:
    stats = defaultdict(int)
    stats["triples"] = len(triples)
    return stats


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


DEFAULT_VARIANTS = {
    "aug_inverse": ["inverse"],
    "aug_time_year": ["time_year"],
    "aug_time_quarter": ["time_quarter"],
    "aug_time_month": ["time_month"],
    "aug_inverse_time_year": ["inverse", "time_year"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create augmented ICEWS datasets.")
    parser.add_argument(
        "--dataset",
        choices=["icews05-15", "icews14"],
        default="icews05-15",
        help="Dataset folder name under TemporalKGs (default: icews05-15).",
    )
    parser.add_argument(
        "--output-root",
        default="TemporalKGs",
        help="Root directory to place augmented datasets (default: TemporalKGs).",
    )
    parser.add_argument(
        "--variants",
        nargs="*",
        help=(
            "Optional subset of variants to generate. "
            "Choices: "
            + ", ".join(DEFAULT_VARIANTS.keys())
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    prefix = get_dataset_prefix(args.dataset)
    base_dir = os.path.join("TemporalKGs", args.dataset)
    splits = {
        "train": read_split(os.path.join(base_dir, f"{prefix}_train.txt")),
        "valid": read_split(os.path.join(base_dir, f"{prefix}_valid.txt")),
        "test": read_split(os.path.join(base_dir, f"{prefix}_test.txt")),
    }

    chosen_variants = DEFAULT_VARIANTS
    if args.variants:
        unknown = [name for name in args.variants if name not in DEFAULT_VARIANTS]
        if unknown:
            raise SystemExit(f"Unknown variants requested: {', '.join(unknown)}")
        chosen_variants = {k: DEFAULT_VARIANTS[k] for k in args.variants}

    for variant_name, augmentation_list in chosen_variants.items():
        variant_dir = os.path.join(args.output_root, f"{args.dataset}_{variant_name}")
        ensure_dir(variant_dir)
        print(f"Generating {variant_name} with augmentations: {augmentation_list}")
        for split_name, triples in splits.items():
            augmented_triples = apply_augmentations(triples, augmentation_list)
            output_file = os.path.join(variant_dir, f"{prefix}_{split_name}.txt")
            write_split(augmented_triples, output_file)
            stats = summarize(augmented_triples)
            print(
                f"  {split_name}: {stats['triples']:,} triples "
                f"(+{stats['triples'] - len(triples):,} from augmentation)"
            )


if __name__ == "__main__":
    main()
