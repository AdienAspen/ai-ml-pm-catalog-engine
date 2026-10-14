# G2.0f Damage closure

**Question.** Can the B1 text be assigned consistently to a physical Damage group and, when applicable, a code?

**Protocol and evidence.** Two blind LLM annotators answered 300 distinct units under `g01-v2`, with 75 shared. The later formatting-only pass left judgements unchanged. Final receipt hashes and `g20f_damage_agreement_sanitized.csv` anchor this closure; responses remain separate in `evaluation_set_v2`.

**Agreement and reading.** Group and group+code raw agreement are both 67/75. Group kappa is 0.604 (AC1 0.891); group+code kappa is 0.609 (AC1 0.893). Both annotators assigned a code to seven shared cases and agreed exactly on all seven. Eight overlap cases had a group/code from annotator 01 but none from annotator 02. Conditional seven-of-seven is narrow evidence, not a population precision estimate. Read per-class tables and confusion matrices alongside the aggregate scores.

**Status.** Closed as diagnostic, `eligible_for_final_heldout=false`; no denominator change or code-performance claim.
