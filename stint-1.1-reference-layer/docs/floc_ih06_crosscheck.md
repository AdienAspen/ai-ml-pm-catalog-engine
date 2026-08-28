# FLOC IH06 Crosscheck

## Scope

T6b crosscheck over the IH06 reference/master-data workbook. This is a sanitized, aggregate-only pass.

No raw operational values, plant names, or functional-location identifiers are emitted.

## What Was Read

- IH06 workbook found: yes
- IH06 rows read: 88441
- Sanitized site groups: 9
- Observed logical-node rows emitted: 640
- ISO 14224 proxy rows emitted: 44

## Questions From Plan v2

### What IEC systems do not appear in IH06?

Status: blocked by upstream reference materialization. The IH06 observed-node inventory was produced, and a 21-row IEC logical-node intake file now exists at `reference_layer/source_designations/iec_logical_nodes_21_reference_v1.csv`. The actual authoritative node codes/labels are still pending, so no missing-node claim is made.

### Where is IH06 deeper than the standard?

Status: measured with a depth proxy and recorded as a design constraint. Depth by site was measured, and no rows at depth >= 6 were observed in this pass. Therefore, FLOC leaf derivation should be constrained to the observed IH06 hierarchy depth until deeper evidence is supplied. This remains a depth-based proxy, not a validated ISO mapping.

### Is the depth consistent between plants?

Status: measured by sanitized site key. Site-level min/median/mean/max depth and depth >= 6 share are reported in the by-site table.

## Outputs

- `stint-1.1-reference-layer/outputs/floc_ih06_crosscheck_by_site_v1.csv`
- `stint-1.1-reference-layer/outputs/floc_ih06_observed_nodes_v1.csv`
- `stint-1.1-reference-layer/outputs/floc_ih06_iso14224_proxy_v1.csv`
- `stint-1.1-reference-layer/docs/floc_ih06_crosscheck.md`

## Interpretation

This pass turns T6 from a support-source inventory into an actual IH06 structure crosscheck. The IEC 21-node contrast remains blocked because the authoritative node values are not yet populated in the materialized reference-layer input.

FLOC remains a separate namespace. KKS/RDS-PP can support and validate interpretation, but it does not resolve or construct hierarchy.

The observed IH06 depth profile is a FLOC leaf design constraint, not an incidental profiling statistic.

## Next Actions

- Populate the materialized 21-node IEC reference set with authoritative node codes/labels before claiming missing IEC systems.
- Review site-level depth outliers using internal-only raw lookup if needed.
- Keep all public/versioned outputs sanitized.
