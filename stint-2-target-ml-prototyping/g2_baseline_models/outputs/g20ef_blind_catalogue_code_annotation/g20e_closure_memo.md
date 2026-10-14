# G2.0e Activity closure

**Question.** Does B1 narrative describe performed work, and does the PMMUWW Catalog A profile offer a fitting code?

**Protocol and evidence.** Two blind LLM annotators re-annotated the same 300 Activity units under `g01-v2.1`; 75 units overlap. The final response receipts and `g20e_activity_agreement_v21_sanitized.csv` are authoritative. Their responses are kept separate in `evaluation_set_v2`.

**Agreement and reading.** Raw agreement is 71/75, kappa 0.893, AC1 0.943. Both marked 39/75 shared units as work described but no applicable code. Consult the per-class table and confusion matrix, not kappa alone. The result supports reproducible presence of work and a catalogue/profile coverage gap in this diagnostic sample; it is not a population rate or final code accuracy.

**Status.** Closed as diagnostic, `eligible_for_final_heldout=false`; no candidate promotion.
