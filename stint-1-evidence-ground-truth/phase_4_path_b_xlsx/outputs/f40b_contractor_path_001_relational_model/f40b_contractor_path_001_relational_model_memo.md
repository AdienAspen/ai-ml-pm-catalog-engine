# F4.0b CONTRACTOR_PATH_001 Relational-Model Characterization Memo

## What CONTRACTOR_PATH_001 Is

The CONTRACTOR_PATH_001 family is an API-dump style relational model, not a daily workbook family. The entity names follow endpoint-like namespace/version/resource structure, split between common master data and service transaction data. JSON is the recommended canonical format because it preserves typing and nested structure while avoiding spreadsheet parsing overhead.

## Entity Inventory

| Entity | Records | Formats | Role | Canonical | Redundancy check |
|---|---:|---|---|---|---|
| `api_common_v1_assets` | 286 | `json;xlsx;xml` | master_data | `json` | json_xml_row_count_consistent;json_xlsx_row_count_consistent |
| `api_common_v1_contracts` | 5 | `json;xlsx;xml` | master_data | `json` | json_xml_row_count_consistent;json_xlsx_row_count_consistent |
| `api_common_v1_customers` | 4 | `json;xlsx;xml` | master_data | `json` | json_xml_row_count_consistent;json_xlsx_row_count_consistent |
| `api_common_v1_sites` | 5 | `json;xlsx;xml` | master_data | `json` | json_xml_row_count_consistent;json_xlsx_row_count_consistent |
| `api_service_v1_service-orders` | 10749 | `json;xlsx;xml` | transactional | `json` | json_xml_row_count_consistent;json_xlsx_row_count_consistent |
| `api_service_v1_service-orders_consumption` | 10749 | `json;xlsx;xml` | transactional | `json` | json_xml_row_count_consistent;json_xlsx_row_count_consistent |
| `api_service_v1_service-visits` | 11862 | `json;xlsx;xml` | transactional | `json` | json_xml_row_count_consistent;json_xlsx_row_count_consistent |

## Key Graph

- `api_common_v1_assets.siteId` -> `api_common_v1_sites.id`: many-to-one, match_rate 100.00%.
- `api_common_v1_assets.customerId` -> `api_common_v1_customers.id`: many-to-one, match_rate 100.00%.
- `api_common_v1_assets.serviceContractId` -> `api_common_v1_contracts.id`: many-to-one, match_rate 100.00%.
- `api_service_v1_service-orders.assetId` -> `api_common_v1_assets.id`: many-to-one, match_rate 99.99%.
- `api_service_v1_service-orders.siteId` -> `api_common_v1_sites.id`: many-to-one, match_rate 100.00%.
- `api_service_v1_service-orders.customerId` -> `api_common_v1_customers.id`: many-to-one, match_rate 100.00%.
- `api_service_v1_service-orders.contractId` -> `api_common_v1_contracts.id`: many-to-one, match_rate 100.00%.
- `api_service_v1_service-orders.padId` -> `api_common_v1_assets.padId`: many-to-one, match_rate 99.99%.
- `api_service_v1_service-visits.orderId` -> `api_service_v1_service-orders.id`: many-to-one, match_rate 93.59%.
- `api_service_v1_service-visits.assetId` -> `api_common_v1_assets.id`: many-to-one, match_rate 99.99%.
- `api_service_v1_service-visits.customerId` -> `api_common_v1_customers.id`: many-to-one, match_rate 100.00%.
- `api_service_v1_service-visits.contractId` -> `api_common_v1_contracts.id`: many-to-one, match_rate 100.00%.
- `api_service_v1_service-orders_consumption.orderId` -> `api_service_v1_service-orders.id`: one-to-one_or_sparse, match_rate 100.00%.
- `api_service_v1_service-orders_consumption._serviceOrderId` -> `api_service_v1_service-orders.id`: one-to-one_or_sparse, match_rate 100.00%.

## Where The Signal Is

- `service-orders` carries confirmed `activityType` at 100% coverage and confirmed prose-bearing `descriptionExtended` at about 96.2% non-null coverage.
- `service-visits` carries order-link, asset-link, contract-link, and scheduling/status context.
- `service-orders-consumption` carries structured consumption/material/resource-shaped fields: `totalResourceConsumption`; `resources[]`; `items[]`; `resources[].activityType`; `resources[].date`; `resources[].unitOfMeasure`; `resources[].activityTypeId`; `resources[].quantity`; `items[].itemSerialNumber`; `items[].unitOfMeasure`; `items[].itemId`; `items[].quantity`; `items[].itemDescription`; `items[].date`.
- Consumption order coverage signals: `_serviceOrderId` order_coverage_rate=1.0; `orderId` order_coverage_rate=1.0.
- Object Part verdict: structured_object_part_signal_present_rule_resolvable_with_item_id_and_quantity_fields. Material/resource evidence appears rule-resolvable for coded item/resource fields; prose description residue remains outside deterministic mapping.

## Deterministic vs ML Frontier

| Target | Resolvable by join/rule | Requires ML | Rationale |
|---|---|---|---|
| Object Part | partial_yes | conditional_remainder | Consumption has item/resource arrays with structured itemId, quantity, unit, and order keys. Rule resolution is plausible for coded items; description-only residue remains ML or curation territory. |
| Activity | partial_yes | yes_for_detail | activityType is structured; detailed work action is in prose fields such as workPerformed and descriptions. |
| Activity Type / MAT | yes | no_for_direct_field | Positive control confirms direct activityType coverage in service-orders. |
| FLOC leaf | partial_yes | conditional_remainder | Asset/site/customer/contract keys close deterministically inside the API family; SAP FLOC leaf still requires external catalog alignment. |
| Damage | no_dedicated_field_confirmed | yes | No dedicated damage field was confirmed in the bounded field profile. |
| Cause | no_deterministic_rule_confirmed | yes_or_manual_review | `reason` exists as free text, but root-cause semantics are unconfirmed; it may encode visit/work motive rather than failure cause. |
| Symptom | unknown_or_no | yes_if_required | No dedicated pre-execution reported symptom field was confirmed. |

## Reason Field QA

`reason` is non-empty in `10749` of `10749` profiled records, but three redacted shapes do not establish it as a root-cause label. It remains candidate textual support for Cause, not deterministic Cause evidence.

## Symptom Verdict

Verdict: **no**. No profiled field is dedicated to pre-execution reported symptom capture. `descriptionExtended` is confirmed and prose-bearing, but characterization does not establish it as an initial problem-report field. `activityType` is structured Activity Type/MAT signal, not Symptom signal. This supports treating missing Symptom as a structural availability question, not merely a sparse-label problem.

## CONTRACTOR_PATH_001 Check

Verdict: **yes**. Sanitized evidence: the profiled API-dump family has seven endpoint-like entities, redundant JSON/XLSX/XML serializations, and a service transactional entity with 10,749 records, matching the expected family-scale indicator without emitting raw operational values.

## Red Flags

- PII/location indicators by field name: No PII-indicator field names detected in profiled fields.
- Format redundancy can inflate denominators if JSON/XLSX/XML serializations are counted as separate source objects.
- Description-like fields should not be treated as confirmed symptom fields without pre-execution semantics.
- Key closure is equality/count based only; no target candidates, crosswalks, mappings, or raw evidence were produced.

## Coverage Note

Read scope: 7 entities, at most 60 characterized fields per entity, text/language distributions from at most 30 records per entity. Positive controls present: 6/6. Truncation: no entity exceeded the field budget; XLSX redundancy was checked by sheet shape only; text examples were intentionally omitted to avoid raw prose emission.

raw_operational_values_emitted: false
