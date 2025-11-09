#!/usr/bin/env python3
"""
Fetch English labels for Wikidata entity identifiers referenced in the TemporalKGs/wikidata splits.

The script collects every subject and object ID that looks like a Wikidata
entity (prefixed with `Q`) and uses the Wikidata API to download English labels
in batches. A TSV mapping file is written so downstream tooling (for example
join_entity_labels.py) can attach human-readable names.

Example:
    python scripts/build_wikidata_label_mapping.py \
        --dataset-dir TemporalKGs/wikidata \
        --output data/wikidata_labels.tsv
"""

import argparse
import itertools
import json
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, List, Set
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import ssl

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
MAX_IDS_PER_REQUEST = 50


def collect_entity_ids(dataset_dir: Path) -> Set[str]:
    entity_ids: Set[str] = set()
    for entry in sorted(dataset_dir.iterdir()):
        if entry.suffix != ".txt":
            continue
        with entry.open("r", encoding="utf-8") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) < 3:
                    continue
                for candidate in (parts[0], parts[2]):
                    if candidate.startswith("Q") and candidate[1:].isdigit():
                        entity_ids.add(candidate)
    return entity_ids


def batched(iterable: Iterable[str], size: int) -> Iterable[List[str]]:
    iterator = iter(iterable)
    while True:
        batch = list(itertools.islice(iterator, size))
        if not batch:
            break
        yield batch


def fetch_labels(ids: List[str], language: str = "en") -> Dict[str, str]:
    params = {
        "action": "wbgetentities",
        "format": "json",
        "ids": "|".join(ids),
        "props": "labels",
        "languages": language,
    }
    url = f"{WIKIDATA_API}?{urlencode(params)}"
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    request = Request(
        url,
        headers={
            "User-Agent": "TemporalKGLabelFetcher/1.0 (https://example.org/contact)",
        },
    )
    with urlopen(request, timeout=30, context=context) as response:
        payload = json.load(response)
    entities = payload.get("entities", {})
    results: Dict[str, str] = {}
    for entity_id, data in entities.items():
        labels = data.get("labels", {})
        label_entry = labels.get(language)
        if label_entry:
            results[entity_id] = label_entry.get("value", "")
        else:
            results[entity_id] = ""
    return results


def build_mapping(dataset_dir: Path, language: str = "en", delay: float = 0.1) -> Dict[str, str]:
    entity_ids = sorted(collect_entity_ids(dataset_dir))
    if not entity_ids:
        raise SystemExit(f"No Wikidata entity identifiers found under {dataset_dir}")

    mapping: Dict[str, str] = {}
    total = len(entity_ids)
    for index, batch in enumerate(batched(entity_ids, MAX_IDS_PER_REQUEST), start=1):
        labels = fetch_labels(batch, language)
        mapping.update(labels)
        if delay:
            time.sleep(delay)
        sys.stderr.write(
            f"\rFetched labels for {min(index * MAX_IDS_PER_REQUEST, total)} / {total} entities"
        )
        sys.stderr.flush()
    sys.stderr.write("\n")
    return mapping


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch English labels for Wikidata entities referenced in TemporalKG datasets."
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=Path("TemporalKGs/wikidata"),
        help="Directory containing Wikidata split files (default: TemporalKGs/wikidata).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/wikidata_labels.tsv"),
        help="TSV file to write the mapping (default: data/wikidata_labels.tsv).",
    )
    parser.add_argument(
        "--language",
        default="en",
        help="Label language to request from Wikidata (default: en).",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.1,
        help="Delay in seconds between requests to avoid hitting rate limits (default: 0.1).",
    )
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)

    mapping = build_mapping(args.dataset_dir, args.language, args.sleep)

    with args.output.open("w", encoding="utf-8") as fh:
        for entity_id, label in sorted(mapping.items()):
            fh.write(f"{entity_id}\t{label}\n")

    print(f"Wrote {len(mapping)} labels to {args.output}")


if __name__ == "__main__":
    main()
