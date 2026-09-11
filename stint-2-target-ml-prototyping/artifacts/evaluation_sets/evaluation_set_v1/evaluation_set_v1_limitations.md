# Evaluation Set v1 Limitations

This registration freezes the usable G0.3 result for evaluation only. It is never a training source.

- Annotators are LLMs, not human SMEs. They judge information type, not domain correctness of SAP code assignment.
- No temperature control was available in either interface. Exact reproducibility is not guaranteed.
- B2 overlap is thin, between 7 and 41 records depending on target. Agreement in that branch carries wide confidence intervals.
- 141 admitted units had no recoverable text and are absent from the sample.
- Object Part carries annotator asymmetry. Annotator 02 applies a more restrictive criterion; v1 keeps annotator files separate and does not resolve the difference.
- Damage is not admitted to v1 because boundary definitions were insufficient, especially around damage vs symptom vs action.
- Activity is not admitted to v1 because the sample is prevalence-dominated and the question is mis-specified for useful discrimination.
- Versioned artefacts contain hashes, counts, responses, and metadata only. Raw text, site names, asset identifiers, and PII remain internal.
