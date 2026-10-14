# G2.0i - component-node diagnostic resolution

B1_RELATIONAL only. Frozen MiniLM cosine >= 0.60, node margin >= 0.05, semantic_normalisation_v2.
40 final Object Part concepts; the 3 unassigned concepts in the historical 7,668-unit count were excluded, leaving 7,393 units with an assigned concept.

- Orders: 10,749; resolved candidates: 2,400; ambiguous: 3,772; abstained: 4,577.
- Resolved candidates that are terminal IH06 leaves: 1,342; non-leaf candidates: 1,058.
- Reasons: {'below_frozen_threshold': 1213, 'semantic_candidate_only': 2400, 'no_assigned_object_part_concept': 3308, 'top_two_node_margin_below_frozen_minimum': 3772, 'no_structural_turbine_match': 50, 'no_profiled_component_candidate': 6}.
- Site breakdown: {'SITE-001': {'abstained': 288, 'ambiguous': 332, 'resolved': 159}, 'SITE-003': {'resolved': 561, 'ambiguous': 382, 'abstained': 638}, 'SITE-007': {'resolved': 426, 'abstained': 1131, 'ambiguous': 742}, 'SITE-008': {'abstained': 1752, 'resolved': 901, 'ambiguous': 1539}, 'SITE-009': {'abstained': 768, 'resolved': 353, 'ambiguous': 777}}.
- Structural references: {}. Site/turbine containment is a scope check, not independent child-node ground truth.

The component node, RBNR, and all five target code spaces are text-derived candidates. No code assignment accuracy or FLOC accuracy is measured where an independent structural child reference is absent.
Object Part concept evidence used for node selection is ineligible as independent evaluation of the catalog code space restricted by that same node's profile.
Presence of an information type and classification into a catalog code remain separate claims; the latter is not measured here.
No promotion, training, F6 update, or denominator change.
