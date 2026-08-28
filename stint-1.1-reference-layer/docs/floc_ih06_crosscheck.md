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
- IEC logical nodes materialized: 21
- IEC physical subsystem nodes used for IH06 contrast: 8
- IEC physical subsystem nodes observed by direct token match: 0
- IEC physical subsystem nodes not observed by direct token match: 8
- Non-physical IEC nodes excluded from missing-subsystem claims: 13

## Questions From Plan v2

### What IEC systems do not appear in IH06?

Status: completed as a token-level proxy. The 21-node IEC reference set is now materialized from accessible preview/table material. Only physical turbine subsystem nodes are used for IH06 missing-system contrast.

Direct token matching did not observe 8 of 8 physical subsystem nodes. This does not yet prove absence of those systems because IH06 may use site-specific FLOC segment codes rather than IEC logical-node identifiers. A crosswalk is required before final missing-system claims.

### Where is IH06 deeper than the standard?

Status: measured with a depth proxy. Depth by site was measured, and no rows at depth >= 6 were observed in this pass. Therefore, no deeper-than-proxy claim is made. This remains a depth-based proxy, not a validated ISO mapping.

### Is the depth consistent between plants?

Status: measured by sanitized site key. Site-level min/median/mean/max depth and depth >= 6 share are reported in the by-site table.

## Outputs

- `stint-1.1-reference-layer/outputs/floc_ih06_crosscheck_by_site_v1.csv`
- `stint-1.1-reference-layer/outputs/floc_ih06_observed_nodes_v1.csv`
- `stint-1.1-reference-layer/outputs/floc_ih06_iso14224_proxy_v1.csv`
- `stint-1.1-reference-layer/outputs/floc_ih06_iec_node_contrast_v1.csv`
- `stint-1.1-reference-layer/docs/floc_ih06_crosscheck.md`

## Interpretation

This pass turns T6 from a support-source inventory into an actual IH06 structure crosscheck. The IEC 21-node contrast is no longer blocked by missing reference materialization.

The contrast is still a token-level proxy: it can show direct matches or non-matches between IH06 FLOC tokens and IEC node identifiers, but it cannot by itself prove physical-system absence without a FLOC-to-IEC crosswalk.

FLOC remains a separate namespace. KKS/RDS-PP can support and validate interpretation, but it does not resolve or construct hierarchy.

## Next Actions

- Build or obtain a FLOC-to-IEC crosswalk before final missing-system claims.
- Review site-level depth outliers using internal-only raw lookup if needed.
- Keep all public/versioned outputs sanitized.
