# G2.0c Step 1 Sanitization Rerun Reconciliation

The original neutral Step 1 run emitted 79,896 candidate terms. A later quality
gate found an operational contractor name inside a hyphenated compound. The
normalizer was corrected to split compounds and remove operational entity
sub-tokens before semantic hashing and n-gram emission.

The first corrected rerun emitted 79,369 terms, a reduction of 527:

- B1_RELATIONAL: 76,157 -> 75,633 (-524).
- B2_WORKBOOKS: 1,752 -> 1,752 (0).
- PATH_A: 1,987 -> 1,984 (-3).

Because semantic hashes changed, conservative duplicate-text exclusion also changed
the eligible construction universe from 9,278 to 9,263 B1 units and from 1,479 to
1,478 B2 units. Path A remained at 159. Step 2 consumed only the corrected 79,369-row
pool. No operational values were emitted.

Release correction: the final assertion above was incomplete. A broader local
restricted-term check found 39 additional path-term rows, including compound
tokens. A separate lexical safety filter now removes them before candidate
emission. The current pool is 79,330 (B1 75,615; B2 1,752; Path A 1,963),
566 below the original 79,896. Normalization and exclusion hashes are unchanged;
the construction universe remains B1 9,263; B2 1,478; Path A 159.
