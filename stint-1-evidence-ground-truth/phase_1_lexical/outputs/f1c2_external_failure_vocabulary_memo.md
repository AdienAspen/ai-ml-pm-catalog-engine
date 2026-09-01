# F1c2 - External Failure Vocabulary Materialization

## Purpose

This bounded pass materializes public/reference vocabulary needed before F1d domain grouping.

It closes the WMEP failure-effects gap and adds subsystem-specific damage/failure evidence sets without merging semantic levels.

## Result

- Vocabulary rows: 144
- Distinct concept IDs: 144
- WMEP failure effects: closed
- Damage beyond gearbox: available as published evidence sets
- Observed text to concept mapping: not performed in this pass
- Raw operational values emitted: false

## Tier Policy

- `silver-high`: WMEP causes/effects, gearbox NREL GRD, NREL main bearing, blade failure-mode literature, converter field-data literature.
- `silver-medium`: generator, yaw, transformer, and hydraulics sets until failure mode / damage / cause levels are separated.

## Required Cautions

- WMEP effects support Symptom-like anchoring but do not prove project-specific Symptom labels.
- NREL GRD remains gearbox-specific.
- The broader subsystem evidence sets are not equivalent vocabularies; F1d must not flatten them into one Damage list.
- Public source URLs were cleaned of `utm_source` parameters, and ResearchGate was not used as a primary source.
