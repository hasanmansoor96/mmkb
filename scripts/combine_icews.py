#!/usr/bin/env python3
"""
Combine ICEWS datasets split-wise (train/valid/test) into a single folder.

Default behavior concatenates ICEWS05-15 and ICEWS14 splits, producing:

    TemporalKGs/icews05-15_2014_combined/icews_all_{train,valid,test}.txt

Each output file contains the union of the corresponding splits from the
source datasets (order preserved as: dataset_a lines first, then dataset_b).
"""

from __future__ import annotations

import argparse
import os
from typing import Tuple


def dataset_prefix(dataset_name: str) -> str:
    if dataset_name.startswith("icews05-15"):
        return "icews_2005-2015"
    if dataset_name.startswith("icews14"):
        return "icews_2014"
    raise ValueError(f"Unsupported dataset name: {dataset_name}")


def concat_files(src_a: str, src_b: str, dest: str) -> int:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    count = 0
    with open(dest, "w", encoding="utf-8") as out_f:
        for path in (src_a, src_b):
            with open(path, "r", encoding="utf-8") as in_f:
                for line in in_f:
                    out_f.write(line)
                    count += 1
    return count


def combine_split(
    dataset_a: str,
    dataset_b: str,
    split: str,
    output_dir: str,
    output_prefix: str,
) -> Tuple[str, int]:
    base_a = os.path.join("TemporalKGs", dataset_a)
    base_b = os.path.join("TemporalKGs", dataset_b)
    prefix_a = dataset_prefix(dataset_a)
    prefix_b = dataset_prefix(dataset_b)
    file_a = os.path.join(base_a, f"{prefix_a}_{split}.txt")
    file_b = os.path.join(base_b, f"{prefix_b}_{split}.txt")

    os.makedirs(output_dir, exist_ok=True)
    dest = os.path.join(output_dir, f"{output_prefix}_{split}.txt")
    total = concat_files(file_a, file_b, dest)
    return dest, total


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Combine ICEWS dataset splits into a single folder."
    )
    parser.add_argument(
        "--dataset-a",
        default="icews05-15",
        help="First dataset folder under TemporalKGs/ (default: icews05-15).",
    )
    parser.add_argument(
        "--dataset-b",
        default="icews14",
        help="Second dataset folder under TemporalKGs/ (default: icews14).",
    )
    parser.add_argument(
        "--output-name",
        default="icews05-15_2014_combined",
        help="Name of the output folder under TemporalKGs/ (default shown).",
    )
    parser.add_argument(
        "--output-prefix",
        default="icews_all",
        help="Prefix for combined split filenames (default: icews_all).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = os.path.join("TemporalKGs", args.output_name)
    os.makedirs(output_dir, exist_ok=True)

    for split in ("train", "valid", "test"):
        dest, total = combine_split(
            dataset_a=args.dataset_a,
            dataset_b=args.dataset_b,
            split=split,
            output_dir=output_dir,
            output_prefix=args.output_prefix,
        )
        print(f"Wrote {total:,} lines to {dest}")


if __name__ == "__main__":
    main()

