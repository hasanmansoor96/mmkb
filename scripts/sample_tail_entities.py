#!/usr/bin/env python3
"""
Sample triples that involve low-frequency entities to inspect tail coverage.

Example:
    python scripts/sample_tail_entities.py --dataset TemporalKGs/yago15k/yago15k_train.txt
    python scripts/sample_tail_entities.py --dataset TemporalKGs/icews05-15/icews_2005-2015_train.txt \\
        --max-frequency 3 --sample-size 20 --seed 42
"""

import argparse
import random
from collections import Counter
from pathlib import Path
from typing import List, Tuple


def load_triples(path: Path) -> List[Tuple[str, str, str]]:
    triples: List[Tuple[str, str, str]] = []
    with path.open("r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line:
                continue
            tokens = line.split("\t")
            if len(tokens) < 3:
                continue
            triples.append((tokens[0], tokens[1], tokens[2]))
    return triples


def find_tail_entities(triples: List[Tuple[str, str, str]], max_frequency: int) -> List[str]:
    counter = Counter()
    for subj, _, obj in triples:
        counter[subj] += 1
        counter[obj] += 1
    return [entity for entity, count in counter.items() if count <= max_frequency]


def sample_tail_triples(
    triples: List[Tuple[str, str, str]],
    tail_entities: List[str],
    sample_size: int,
) -> List[Tuple[str, str, str]]:
    tail_set = set(tail_entities)
    tail_triples = [triple for triple in triples if triple[0] in tail_set or triple[2] in tail_set]
    if len(tail_triples) <= sample_size:
        return tail_triples
    return random.sample(tail_triples, sample_size)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sample triples that involve entities with low frequency."
    )
    parser.add_argument(
        "--dataset",
        required=True,
        type=Path,
        help="Path to the dataset split (tab-separated).",
    )
    parser.add_argument(
        "--max-frequency",
        type=int,
        default=5,
        help="Maximum frequency for entities considered part of the tail (default: 5).",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=10,
        help="Number of tail triples to sample (default: 10).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Optional random seed for reproducibility.",
    )
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    triples = load_triples(args.dataset)
    if not triples:
        raise SystemExit(f"No triples found in {args.dataset}.")

    tail_entities = find_tail_entities(triples, args.max_frequency)
    if not tail_entities:
        print("No entities fall below the specified frequency threshold.")
        return

    samples = sample_tail_triples(triples, tail_entities, args.sample_size)
    print(f"Found {len(tail_entities)} tail entities.")
    print(f"Showing {len(samples)} sampled triples:")
    for subj, rel, obj in samples:
        print(f"{subj}\t{rel}\t{obj}")


if __name__ == "__main__":
    main()
