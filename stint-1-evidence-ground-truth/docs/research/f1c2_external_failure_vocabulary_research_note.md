# F1c2 External Failure Vocabulary Research Note

## Scope

This note records the bounded research handoff used to materialize `F1c2` vocabulary inputs for STINT_1 Phase 1.

It closes two gaps needed before domain grouping:

- WMEP failure effects for Symptom-like anchoring.
- Public subsystem-specific failure and damage vocabulary beyond gearbox.

This note is a research support artifact. It does not create project-specific labels, validated mappings, denominators, model metrics, or production feasibility claims.

## WMEP Failure Effects

Source: Ozturk, Fthenakis, and Faulstich, *Energies* 11(9):2317, 2018, section 2.3.3 and Table 4. The article states that the WMEP database categories are used for the failure causes and effects in the study.

DOI: `10.3390/en11092317`

Failure effects materialized for F1c2:

| effect_term | target | semantic_level | evidence_type | tier | status |
|---|---|---|---|---|---|
| Overspeed | Symptom | failure_effect | reference_evidence | silver-high | active |
| Overload | Symptom | failure_effect | reference_evidence | silver-high | active |
| Noise | Symptom | failure_effect | reference_evidence | silver-high | active |
| Vibration | Symptom | failure_effect | reference_evidence | silver-high | active |
| Reduced power | Symptom | failure_effect | reference_evidence | silver-high | active |
| Causing follow-up damage | Symptom | failure_effect | reference_evidence | silver-high | active |
| Plant stoppage | Symptom | failure_effect | reference_evidence | silver-high | active |
| Other consequences | Symptom | failure_effect | reference_evidence | silver-high | residual_category |

Governance note: WMEP effects can anchor Symptom-like evidence, but they do not prove project-specific Symptom labels. `Causing follow-up damage` is propagation-like and must not be forced into Symptom or Damage without later rule justification. `Other consequences` is residual and should remain low-specificity unless constrained by additional evidence.

## WMEP Failure Causes

Source: same as above, section 2.3.2 and Table 4.

Failure causes materialized for F1c2:

| cause_term | target | semantic_level | evidence_type | tier | status |
|---|---|---|---|---|---|
| high wind | Cause | failure_cause | reference_evidence | silver-high | active |
| grid failure | Cause | failure_cause | reference_evidence | silver-high | active |
| lightning | Cause | failure_cause | reference_evidence | silver-high | active |
| icing | Cause | failure_cause | reference_evidence | silver-high | active |
| malfunction of control systems | Cause | failure_cause | reference_evidence | silver-high | active |
| component wear or failure | Cause | failure_cause | reference_evidence | silver-high | active |
| loosening of parts | Cause | failure_cause | reference_evidence | silver-high | active |
| other causes | Cause | failure_cause | reference_evidence | silver-high | active |
| unknown causes | Cause | failure_cause | reference_evidence | silver-high | active |

Governance note: these are reference causes reproduced through a peer-reviewed open-access secondary source, not the original WMEP database. They are valid reference vocabulary, not observed project labels.

## Subsystem Failure And Damage Vocabulary

The research did not find one single authoritative controlled vocabulary covering all major wind-turbine subsystems. Instead, it found multiple published evidence sets with different semantic levels.

This distinction matters: F1d must not flatten failure mode, event, component, damage mechanism, and cause into one homogeneous Damage list.

## Evidence Sets Materialized As `silver-high`

| owner | target | semantic_level | coverage_scope | rationale |
|---|---|---|---|---|
| `NREL_GRD` | Damage / Cause | damage_mechanism / failure_cause | gearbox | Official/public NREL gearbox failure evidence; gearbox-specific only. |
| `NREL_MAIN_BEARING` | Damage | field_reported_damage | main bearing | Field data study over 167 wind power plants / 15.3 GW; strong for main-bearing damage. |
| `BLADE_FAILURE_MODE_LITERATURE` | Damage | failure_mode_taxonomy | rotor blade | Published blade failure-mode taxonomy; subsystem-specific. |
| `CONVERTER_FIELD_DAMAGE_LITERATURE` | Damage | component_or_damage_mechanism | converter / power electronics | Field-data and damage analysis; strong, but mixes component and mechanism vocabulary. |

## Evidence Sets Materialized As `silver-medium`

| owner | target | semantic_level | coverage_scope | reason for caution |
|---|---|---|---|---|
| `GENERATOR_FAILURE_LITERATURE` | Damage | fault_or_failure_event | generator | Published vocabulary exists, but event/failure/damage levels need separation. |
| `YAW_FAILURE_LITERATURE` | Damage | fault_or_damage_vocabulary | yaw system | Published vocabulary exists, but fault and damage terms are mixed. |
| `TRANSFORMER_FAILURE_LITERATURE` | Damage | fault_tree_event | transformer | Published vocabulary exists, but fault-tree event terms are not direct Damage labels. |
| `HYDRAULIC_PITCH_FAILURE_LITERATURE` | Damage | component_failure_mode_or_cause | hydraulic pitch system | Published vocabulary exists, but component, failure mode, and cause terms are mixed; source verification remains weaker than the other sets. |

## Operational Interpretation

F1c2 produces real external reference vocabulary, not merely architecture. It is sufficient to proceed toward F1d domain grouping, with these constraints:

- WMEP effects can support the Symptom route, but only as reference vocabulary.
- Cause is better covered after WMEP causes, but still lacks observed project labels.
- Damage is no longer gearbox-only, but the new evidence sets are heterogeneous.
- Main bearing, converter, blades, and gearbox are stronger than generator, transformer, hydraulics, and yaw for immediate anchoring.
- Observed text to concept links remain `expert_inference` unless later corroborated independently.

## Source Hygiene

All formal source URLs used in F1c2 outputs must be free of `utm_source` parameters.

ResearchGate links from the handoff were not used as primary sources in the versioned F1c2 artifact. Where source verification is weaker, the materialized rows remain `silver-medium` and `requires_semantic_classification`.

## Downstream Rule

F1d must group observed terms against this vocabulary by target, owner, subsystem, and semantic level. It must not merge all Damage-adjacent evidence into a single flat concept space.
