# G2.0b leakage extraction review - C3

All 13 previously flagged B1 rows were rechecked against the current source narrative. The review tested whether the **entire persisted `leaked_value` string** occurs literally in that source. None does, so all 13 extracted spans are `rejected` and `pending_sample_validation` is closed for those spans. The internal audit holds the original values and checks at mode 600; the sanitised CSV contains only safe source keys and terminal status.

This does **not** mean the source has no target leakage. All 13 narratives contain the target heading. Four `Object Part` rows also contain a clear `Object Part: ... - code - ...` pattern with the parsed code. Nine `Cause` rows use a `Cause:` heading with free-text operational fields; apparent parsed codes in some of them come from later fields, not a verified SAP cause assignment. The old extractor overran field boundaries, so its full captured values are not trustworthy as catalogue labels.

The G2.0b masking remains in force for all 13 rows as a conservative input safeguard. No row is unmasked, no prior G2.0 evidence is retroactively promoted, and no denominator changes here. A future catalogue-leakage count must use a bounded parser and a separate review; this terminal validation concerns only the 13 stored extracted spans.
