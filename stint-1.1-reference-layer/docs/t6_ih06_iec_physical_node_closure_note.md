# T6 Closure Note - IH06 vs IEC Physical Node Contrast

## Scope

This note closes T6b for the reference-layer sub-stint by comparing the materialized IEC wind logical-node reference against the sanitized IH06 node inventory.

No raw operational values are emitted. The comparison is a token-level proxy, not a final semantic crosswalk.

## Inputs

- IEC logical-node reference rows materialized: 21
- IEC physical turbine subsystem nodes selected for IH06 contrast: 8
- IH06 rows read: 88441
- Sanitized site count: 9
- Maximum observed IH06 depth by site: 4 to 5
- Raw values emitted: false

## Physical Node Contrast

| node_id | published_description | observed_in_ih06_token_inventory | observed_site_count | contrast_status |
| --- | --- | --- | --- | --- |
| WROT | Wind turbine rotor information | False | 0 | not_observed_in_ih06_token_inventory_crosswalk_required |
| WTRM | Wind turbine transmission information | False | 0 | not_observed_in_ih06_token_inventory_crosswalk_required |
| WGEN | Wind turbine generator information | False | 0 | not_observed_in_ih06_token_inventory_crosswalk_required |
| WCNV | Wind turbine converter information | False | 0 | not_observed_in_ih06_token_inventory_crosswalk_required |
| WTRF | Wind turbine transformer information | False | 0 | not_observed_in_ih06_token_inventory_crosswalk_required |
| WNAC | Wind turbine nacelle information | False | 0 | not_observed_in_ih06_token_inventory_crosswalk_required |
| WYAW | Wind turbine yawing information | False | 0 | not_observed_in_ih06_token_inventory_crosswalk_required |
| WTOW | Wind turbine tower information | False | 0 | not_observed_in_ih06_token_inventory_crosswalk_required |

## Result

- Physical subsystem nodes compared: 8
- Physical subsystem nodes observed by direct token match: 0
- Physical subsystem nodes not observed by direct token match: 8
- Non-physical IEC nodes excluded from missing-subsystem claims: 13

## Interpretation

The eight physical IEC subsystem node identifiers were not observed as direct tokens in the sanitized IH06 node inventory.

This should not be treated as proof that the IH06 lacks those physical subsystems. The current evidence supports a nomenclature/crosswalk gap: IH06 appears to encode hierarchy with project/SAP-specific structure rather than IEC logical-node identifiers.

Therefore, the absence is classified as not_observed_in_ih06_token_inventory_crosswalk_required, not as structural absence.

## Structural Depth Finding

The IH06 extract was successfully read and profiled. Observed hierarchy depth is shallower than the IEC logical-node reference would require for direct one-to-one node comparison, with site-level maximum depth ranging from 4 to 5 and no records at depth >= 6 in this pass.

This is a design constraint for the FLOC leaf segment target: future FLOC derivation should use IH06/KKS as supporting structure and validation context, while avoiding claims that KKS or IEC tokens directly resolve the final hierarchy.

## Closure Status

T6b is closed for STINT_1.1 as a reference-layer contrast. It produced a usable constraint and a required downstream action: build or obtain a semantic crosswalk between IH06/SAP functional-location naming and IEC physical subsystem concepts before making final missing-system or FLOC feasibility claims.

## Downstream Requirement

- Preserve the 21-node IEC reference as reference_evidence / silver-high with the preview-material caveat.
- Use only the eight physical subsystem nodes for IH06 missing-system contrast.
- Do not compare IH06 functional locations against informational/control/log nodes as if they were physical locations.
- Treat direct-token absence as crosswalk-required, not as absence of the underlying system.
