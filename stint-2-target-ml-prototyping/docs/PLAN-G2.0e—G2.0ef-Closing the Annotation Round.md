# G2.0e/f — Closing the Annotation Round

**Two different actions. Do not mix them.**

```
Damage     format re-delivery only · do NOT re-annotate
Activity   full re-annotation · after rule A3 is rewritten
```

---

# Part 1 — Damage · Format Re-delivery

## Why

Both batches failed format validation. **Neither is a criterion problem.**

```
annotator_01   141 rows carry `none_applicable` in BOTH group and code
               The protocol states the label goes in `group`,
               and `code` stays EMPTY.

annotator_02   row G20EF-DAMAGE-0293 has two fields instead of three.
               Every row must carry three, even when the third
               is empty.
```

## Why not re-annotate

The criterion worked. In the visible overlap, **every case where both
annotators assigned a code matched exactly at group and code level** —
`EXT/EIBP`, `EXT/EICP`, `MEC/MFLC`, `MEC/MFLK`, `MEC/MFLO`.

Re-annotating would risk criterion drift between rounds and break
comparability, with nothing to gain.

## What to request

Same judgements, corrected shape:

```
annotation_id,group,code

damage assigned            MEC,MFLC
none_applicable            none_applicable,
ambiguous_multi_process    ambiguous_multi_process,
abstain                    abstain,
```

**The trailing comma is required. Three fields on every row.**

## Verify on receipt

```
row count matches package exactly
three fields on every row
code EMPTY wherever group is a special outcome
code non-empty and valid wherever group is one of the nine
no duplicate annotation_id
judgements unchanged from the original batch
```

The last check matters: if a judgement changed, the annotator
re-annotated instead of reformatting. Reject and request again.

---

# Part 2 — Activity · Re-annotation

## Why

```
raw agreement   56%
Cohen's κ       0.086
Gwet's AC1      0.538
```

The confusion matrix shows a one-directional shift, not random noise:

```
                    02: no_code    02: none
01: no_code              3            33
01: none                 0            39
```

**Zero in the lower-left cell.** Annotator 02 never marked
`no_applicable_code` where 01 marked `none_applicable`. One annotator
consistently required more evidence of executed work than the other.

Per-class agreement: **15.4%** on `no_applicable_code` against 70.3%
on `none_applicable`.

## Root cause — rule A3 as written

```
A3   annotate what was DONE
     intention stated without execution → none_applicable
```

**The rule does not define what counts as evidence of execution.** A
text such as `"6-month service"` describes work to one reader and
intention to the other, and both readings are defensible.

This is the same failure mode as `action_not_damage` in v1: a class
without an operational criterion.

⚠️ **Re-annotating under the current A3 would reproduce the same
disagreement.** The rule must be rewritten first.

## A3 — rewritten

```
A3 · performed vs described

Annotate `no_applicable_code` when the text names a maintenance act,
regardless of whether execution is narrated.

  "replaced filter"          → no_applicable_code
  "6-month service"          → no_applicable_code
  "annual inspection T14"    → no_applicable_code
  "blade repair scheduled"   → no_applicable_code

Annotate `none_applicable` only when NO maintenance act is named.

  "5088 WaterLevelTooLow"    → none_applicable · condition only
  "2 techs 4 hours"          → none_applicable · no act
  "Mountain View sub order"  → none_applicable · no act
  "T-14"                     → none_applicable · identifier only

The test is whether a maintenance act is NAMED, not whether its
execution is narrated. Do not infer execution, and do not require it.
```

**Rationale:** the earlier rule asked annotators to judge execution
from text that rarely states it. Naming an act is observable; having
executed it often is not.

## What to re-annotate

```
scope        the same 300 units · same packages
             do NOT resample
protocol     g01-v2 with A3 as rewritten above
version      record as g01-v2.1
```

**Keep the original batches.** They are not discarded — they document
that the earlier A3 did not discriminate, and that is itself a finding
about rule design.

## Register both rounds

```
g01-v2      original A3 · κ 0.086 · retained as evidence
g01-v2.1    rewritten A3 · the round that counts
```

---

## Deliverables

```
g20f_damage_responses_annotator_01_reformatted.csv
g20f_damage_responses_annotator_02_reformatted.csv
g20f_damage_agreement_sanitized.csv        κ · AC1 · confusion
                                            at group AND code level

g01-v2.1_protocol.md                       A3 rewritten
g20e_activity_responses_v21_annotator_01.csv
g20e_activity_responses_v21_annotator_02.csv
g20e_activity_agreement_v21_sanitized.csv
g20ef_round_comparison_memo.md             v2 vs v2.1 for Activity
```

---

## Closure criteria

```
Damage     both batches reformatted · judgements verified unchanged
           agreement reported at group and code level separately
           per-class agreement for the nine groups

Activity   A3 rewritten and frozen BEFORE re-annotation
           same 300 units · no resampling
           both rounds registered · v2 retained
           agreement reported with κ, AC1, raw, per-class, confusion
```

⚠️ **Activity remains diagnostic, not a final held-out set.** It was
drawn from 1,234 eligible units after G2.0c exclusions and does not
represent B1.