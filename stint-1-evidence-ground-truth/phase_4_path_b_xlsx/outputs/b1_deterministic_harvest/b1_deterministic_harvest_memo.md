# B1.1 Deterministic Harvest

## Scope

This pass harvests deterministic structural evidence for `CONTRACTOR_PATH_001`. It does not run ML, infer text labels, or map source material codes to SAP catalogs.

## Summary

- Service-order records: `10749`
- Activity Type / MAT observed labels: `10749`
- Consumption records: `10749`
- Consumption item rows with usable source signal: `15358`
- Orders with structured consumption records: `10749`
- FLOC route context rows: `10749`
- Asset join match rate: `99.99%`
- Site join match rate: `100.00%`
- Contractual denominator rows supported now: `10749`

## Target Summary

| target | status | evidence_rows | physical_records | contractual_rows_now |
| --- | --- | ---: | ---: | ---: |
| Activity Type / MAT | resolved_observed_source_label | 10749 | 10749 | 10749 |
| FLOC leaf | internal_asset_site_join_resolved_external_floc_alignment_required | 10749 | 10749 | 0 |
| Object Part | structured_source_material_observed_mapping_required | 15358 | 4079 | 0 |

## Relationship Rates Used

| source_entity | source_field | target_entity | target_field | match_rate |
| --- | --- | --- | --- | ---: |
| api_common_v1_assets | siteId | api_common_v1_sites | id | 100.00% |
| api_common_v1_assets | customerId | api_common_v1_customers | id | 100.00% |
| api_common_v1_assets | serviceContractId | api_common_v1_contracts | id | 100.00% |
| api_service_v1_service-orders | assetId | api_common_v1_assets | id | 99.99% |
| api_service_v1_service-orders | siteId | api_common_v1_sites | id | 100.00% |
| api_service_v1_service-orders | customerId | api_common_v1_customers | id | 100.00% |
| api_service_v1_service-orders | contractId | api_common_v1_contracts | id | 100.00% |
| api_service_v1_service-orders | padId | api_common_v1_assets | padId | 99.99% |
| api_service_v1_service-visits | orderId | api_service_v1_service-orders | id | 93.59% |
| api_service_v1_service-visits | assetId | api_common_v1_assets | id | 99.99% |
| api_service_v1_service-visits | customerId | api_common_v1_customers | id | 100.00% |
| api_service_v1_service-visits | contractId | api_common_v1_contracts | id | 100.00% |
| api_service_v1_service-orders_consumption | orderId | api_service_v1_service-orders | id | 100.00% |
| api_service_v1_service-orders_consumption | _serviceOrderId | api_service_v1_service-orders | id | 100.00% |

## Interpretation

`activityType` is harvested as a direct observed source label for Activity Type / MAT and is outside the ML scope for this branch.

`consumption` provides structured Object Part signal, but this pass does not establish material-to-SAP Catalog B equivalence. Those rows remain mapping-required and do not support denominator promotion yet.

FLOC route context closes strongly inside the API graph, but SAP/IH06 FLOC leaf alignment remains required before promotion to a target label.

raw_operational_values_emitted: false
