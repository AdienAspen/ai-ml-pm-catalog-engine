# IEC Logical Nodes Materialization Note

## Scope

This note closes the immediate T2 input gap that blocked the T6b IH06-vs-IEC contrast.

## Decision

The reference layer now contains a controlled 21-row IEC logical-node intake file:

- `stint-1.1-reference-layer/reference_layer/source_designations/iec_logical_nodes_21_reference_v1.csv`

The file materializes the required shape and expected cardinality, but it does not invent node codes or labels.

## Current Status

- Expected IEC node slots: 21
- Authoritative node codes materialized: 0
- Authoritative node labels materialized: 0
- Status: `pending_authoritative_value`

## Interpretation

The 21-node IEC contrast remains blocked for final missing-node claims until the authoritative node values are supplied from the research source or another citable reference.

The blocker is therefore not an IH06 parsing failure. It is an upstream reference-materialization gap.

## Governance

No invented IEC node names, codes, or labels are included. These pending rows are not usable as reference evidence until populated and reviewed.
