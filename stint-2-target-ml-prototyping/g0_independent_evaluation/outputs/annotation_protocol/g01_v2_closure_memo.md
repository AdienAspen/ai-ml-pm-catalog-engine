# g01-v2 protocol closure

**Question.** Can two blind LLM annotators reproducibly separate performed Activity and physical Damage under operational tie-break rules, without forcing catalogue codes?

**Protocol.** Damage uses `g01-v2`, including a separate `ambiguous_multi_process` exit and group-first/code-second response. Activity was fully re-annotated under `g01-v2.1`, with A3 distinguishing performed work from plans and `no_applicable_code` from `none_applicable`. The frozen sample is 300 units per target with 75 shared, and no text/prototype/threshold revision was made for this closure.

**Agreement.** Activity v2.1: 71/75 raw agreement, Cohen kappa 0.893, AC1 0.943. Damage v2: 67/75 raw agreement; group kappa 0.604 and AC1 0.891; group+code kappa 0.609 and AC1 0.893. The per-class and confusion tables remain the primary reading alongside global scores.

**Status.** Protocol round closed for diagnostic registration as `evaluation_set_v2`; not a final held-out or human-SME set. Damage and Activity closure details are in the G2.0f and G2.0e memos.
