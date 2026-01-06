# ICEWS Data Processing Summary

This repo uses ICEWS temporal KG data and a set of augmented + normalized variants.
The current experiment base is:

- `TemporalKGs/icews05-15_aug_inverse_time_year/icews_2005-2015_{train,valid,test}_normalized.txt`

Below is a concise explanation of what has been done so far, and how these files
compare to the base ICEWS splits.

## Base ICEWS Files

The original (non-augmented) splits live here:

- `TemporalKGs/icews05-15/icews_2005-2015_{train,valid,test}.txt`

Each line is a quadruple:

```
head<TAB>relation<TAB>tail<TAB>YYYY-MM-DD
```

Example:

```
Colombia	Investigate	Guerrilla (Colombia)	2008-07-25
```

## Augmentation Steps

The augmented dataset we are using is:

- `TemporalKGs/icews05-15_aug_inverse_time_year/icews_2005-2015_{train,valid,test}.txt`

It is created by *adding* new triples to the base data (the originals remain).
Two augmentations are applied:

1) Inverse relations
   - For each triple `(h, r, t, date)`, add `(t, r_INV, h, date)`.
   - This lets the model learn direction-specific patterns.

2) Time-bucketed relations (yearly)
   - For each triple `(h, r, t, date)`, add `(h, r_YEAR_YYYY, t, date)`.
   - This lets the model learn year-specific variants of each relation.

These augmentations *increase* relation vocabulary size and triple count while
preserving the original relations for dense, time-agnostic signal.

## Normalization Step

We then normalized the augmented files into the following outputs:

- `TemporalKGs/icews05-15_aug_inverse_time_year/icews_2005-2015_train_normalized.txt`
- `TemporalKGs/icews05-15_aug_inverse_time_year/icews_2005-2015_valid_normalized.txt`
- `TemporalKGs/icews05-15_aug_inverse_time_year/icews_2005-2015_test_normalized.txt`

Each normalized file is TSV with a header and parsed time + country fields:

```
head	relation	tail	date	year	month	day	time_index	head_country	tail_country	is_domestic
```

Where:
- `year`, `month`, `day` are integer fields parsed from the date string.
- `time_index` is the number of months since 2005-01:
  `time_index = (year - 2005) * 12 + (month - 1)`
- `head_country` and `tail_country` are extracted from parenthetical tags in the
  entity string when present (empty if missing).
- `is_domestic` is `1` when both countries are present and equal (case-insensitive),
  else `0`. This supports filtering to international-only events.

This normalization makes time comparable across events and simplifies downstream
aggregation (e.g., events per year) and model inputs.

## Summary of Differences vs. Base ICEWS

- Base files: raw quadruples only (`head`, `relation`, `tail`, `date`).
- Augmented files: base quadruples + inverse triples + yearly bucketed relations.
- Normalized files: augmented triples + parsed time fields + `time_index` for
  consistent temporal ordering.
