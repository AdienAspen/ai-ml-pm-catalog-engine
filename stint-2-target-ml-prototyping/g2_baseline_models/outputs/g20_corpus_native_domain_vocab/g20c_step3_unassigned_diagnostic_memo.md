# G2.0c Step 3 - Unassigned Concept Diagnostic

## Purpose

Distinguish whether the 191 unassigned concepts primarily reflect insufficient
target support, mixed semantic clusters, or correctly rejected noise. This is a
diagnostic review only. It does not change target assignments, anchors,
denominators, or the Step 3 vocabulary.

## Sample design

The sample contains the five largest unassigned concepts plus five deterministic
positions from the remaining size distribution (10%, 30%, 50%, 70%, and 90%).
It is intentionally diagnostic and is not a probability sample; its proportions
must not be extrapolated to all 191 concepts.

## Findings

```
correctly conservative / remain unassigned       5
recoverable Activity support gap                 3
recoverable Object Part component-head gap       1
mixed cluster requiring split before assignment 1
```

The largest unassigned concepts are mostly encoded fragments, abbreviations, or
system-level context. Their rejection is appropriate and explains a meaningful
part of the unassigned volume. The review also found four coherent concepts that
the current target support misses: `acknowledged`, `setting`, `assessment`, and
`lock`. These are anchor or lexical-support gaps rather than grouping failures.

One concept (`rto`) mixes operational abbreviations with transformer-related
forms. Expanding anchors would not safely recover it; it requires a cluster split
or a later member-level review.

## Decision

Do not lower target thresholds globally. A global relaxation would promote the
large noise clusters. Before Step 4, consider one bounded target-support revision
using generic action families (`acknowledge/verify/ensure`,
`configure/set/setting`, `assess/analyze/review`) and generic physical hardware
heads (`lock/cylinder/pin/nut/hatch/door/shackle`). Any revision must remain
analyst-authored, must not use evaluation text or G2.0 prototypes, and must rerun
the target-by-path concentration gates.


## Release sanitization correction

The original six-token guard was incomplete. The broader local restricted-term policy removes 39 path-term candidates and 16 clustered variants. Current counts are 79,330 candidates, 24,825 filtered rows and 24,405 members. All 256 concept IDs and canonical labels remain stable. Member statistics and concentration are recomputed; original fitted centers, silhouette and target scores are historical, not a claim of a fresh clean fit. No restricted variant remains usable as an anchor. Step 3b, mapping and unit coverage are rerun separately. See the release reconciliation report for current results.
