#!/usr/bin/env python3
"""
Augment a TemporalKG split by attaching human-readable labels to entity columns.

The mapping file is expected to contain two columns: entity identifier and label.
By default both input files are assumed to be tab-separated.

Example:
    python scripts/join_entity_labels.py \\
        --dataset TemporalKGs/wikidata/wiki_train.txt \\
        --mapping data/qid_labels.tsv \\
        --output wiki_train_with_labels.tsv
"""

import argparse
import csv
from pathlib import Path
from typing import Dict, Optional


def resolve_delimiter(delimiter: str) -> str:
    if len(delimiter) == 1:
        return delimiter
    try:
        decoded = delimiter.encode("utf-8").decode("unicode_escape")
    except UnicodeDecodeError:
        decoded = delimiter
    if len(decoded) != 1:
        raise SystemExit(
            f'Delimiter must resolve to a single character, got "{delimiter}". '
            "Use --delimiter '\\t' for tabs."
        )
    return decoded


def load_mapping(mapping_path: Path, delimiter: str) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    with mapping_path.open("r", encoding="utf-8") as fh:
        reader = csv.reader(fh, delimiter=delimiter)
        for row in reader:
            if not row:
                continue
            key = row[0].strip()
            if not key:
                continue
            label = row[1].strip() if len(row) > 1 else ""
            mapping[key] = label
    return mapping


def attach_labels(
    dataset_path: Path,
    mapping: Dict[str, str],
    delimiter: str,
    output_path: Optional[Path],
    missing_value: str,
) -> None:
    if output_path is None:
        output_path = dataset_path.with_suffix(dataset_path.suffix + ".labeled")

    with dataset_path.open("r", encoding="utf-8") as source, output_path.open(
        "w", encoding="utf-8", newline=""
    ) as target:
        reader = csv.reader(source, delimiter=delimiter)
        writer = csv.writer(target, delimiter=delimiter)
        for row in reader:
            if len(row) < 3:
                writer.writerow(row)
                continue
            subj, rel, obj, *rest = row
            subj_label = mapping.get(subj, missing_value)
            obj_label = mapping.get(obj, missing_value)
            writer.writerow([subj, rel, obj, subj_label, obj_label, *rest])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Attach labels to the subject/object columns of a dataset split."
    )
    parser.add_argument(
        "--dataset",
        required=True,
        type=Path,
        help="Path to the dataset split (tab-separated).",
    )
    parser.add_argument(
        "--mapping",
        required=True,
        type=Path,
        help="Two-column mapping file (entity ID, label).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional output path. Defaults to <dataset>.labeled next to the source file.",
    )
    parser.add_argument(
        "--delimiter", default="\\t", help="Column delimiter (default: TAB)."
    )
    parser.add_argument(
        "--missing-value",
        default="",
        help="Placeholder when an entity is not found in the mapping (default: empty string).",
    )
    args = parser.parse_args()

    delimiter = resolve_delimiter(args.delimiter)

    mapping = load_mapping(args.mapping, delimiter)
    if not mapping:
        raise SystemExit(f"No entries found in mapping file {args.mapping}.")

    attach_labels(args.dataset, mapping, delimiter, args.output, args.missing_value)


if __name__ == "__main__":
    main()
