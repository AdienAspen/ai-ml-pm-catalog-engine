# IEC Logical Nodes Materialization Note

## Scope

This note closes the immediate T2 input gap that blocked the T6b IH06-vs-IEC contrast.

## Decision

The reference layer now contains a controlled 21-row IEC logical-node intake file:

- `stint-1.1-reference-layer/reference_layer/source_designations/iec_logical_nodes_21_reference_v1.csv`

The rows were materialized from accessible IEC preview/table material supplied in the Track 1 research handoff. They are source-attested reference entries, not reconstructed or invented node codes.

## Current Status

- Expected IEC node rows: 21
- IEC node codes materialized: 21
- IEC node labels materialized: 21
- Evidence type: `reference_evidence`
- Tier: `silver-high`
- Primary source: `IEC 61400-25-2`
- Primary source version: `Ed. 2.0 (2015)`
- `LTIM` source: `IEC 61850-7-4` derived reference
- Status: `active`

## IH06 Contrast Scope

Only physical turbine subsystem nodes are eligible for IH06 missing-system contrast:

- `WROT`
- `WTRM`
- `WGEN`
- `WCNV`
- `WTRF`
- `WNAC`
- `WYAW`
- `WTOW`

The other nodes are plant, device, alarm, log, availability, power-control, report, time, or general-information nodes. They are valid IEC reference entries, but they are not functional-location subsystem expectations for IH06.

`LTIM` is retained for traceability as an IEC 61850-7-4-derived time-management node. It is not treated as an IEC 61400-25-2 physical wind-turbine subsystem node.

`WTUR` is retained as turbine general/root context, not as a missing subsystem requirement.

## Source Caveat

This file is based on accessible preview/table material and is not claimed to be a complete transcription of the normative document.

Clause/table references come from the accessible preview material.

## Governance

The rows are usable as reference evidence for POC-level semantic design and IH06 contrast scoping. They do not create record-level labels or production-grade standards compliance claims.
