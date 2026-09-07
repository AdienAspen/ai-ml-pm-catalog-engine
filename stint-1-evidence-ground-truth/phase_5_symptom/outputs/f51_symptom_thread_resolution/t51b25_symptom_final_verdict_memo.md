# T5.1b2.5 - Final Symptom Verdict

## Verdict

`Symptom` is no longer a zero-signal target. The corpus contains observed-condition proxy candidates, mainly in the relational `reason` field and secondarily in Path A/B2 text. However, this is not ground truth and does not support a contractual denominator.

## Path Verdicts

| Path | Rows evaluated | OEM pattern rows | Semantic observed_condition | Verdict |
| --- | ---: | ---: | ---: | --- |
| `RELATIONAL_REASON` | 10338 | 4057 | 1827 (17.67%) | `candidate_signal_present` |
| `PATH_A_NOTES` | 882 | 15 | 42 (4.76%) | `candidate_signal_present` |
| `PATH_A_CONCERN_TABLE` | 1581 | 0 | 68 (4.3%) | `candidate_signal_present` |
| `B2_WORKBOOKS` | 1963 | 3 | 62 (3.16%) | `candidate_signal_present` |

## OEM Dictionary Finding

The OEM dictionary contains `4057` observed occurrences, `679` distinct codes, and `1014` code-description pairs. `151` codes have multiple normalized descriptions, including `81` likely-polysemous codes. Therefore, downstream mapping must not assume `code -> description` is one-to-one.

## Denominator Guardrail

All Symptom signal in this memo remains `expert_inference`, maximum `silver-medium`, and `evaluation_independence = derived_from_rules`. It can seed a proxy candidate set for F6, but this pass promotes nothing to contractual or proxy denominator.

## Practical Conclusion

The strongest Symptom route is no longer a sentinel or placeholder. It is a conservative proxy route: normalized semantic classification over `reason`, supported by an observed OEM alarm dictionary and cross-checked against Path A/B2 text. The next decision belongs in F6: whether these candidates are admitted into a clearly labelled POC proxy denominator, never into the contractual denominator.
