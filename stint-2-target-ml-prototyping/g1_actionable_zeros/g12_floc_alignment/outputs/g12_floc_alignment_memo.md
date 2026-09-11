# G1.2 FLOC IH06 Alignment Memo

G1.2 tested whether relational B1 asset references can be aligned to IH06/FLOC.

## Result

- Service orders assessed: 10,749
- Relevant relational sites: 5
- Orders matched to IH06 asset/turbine node: 10,699
- Asset-node match rate: 99.53484%

## Interpretation

The relational path can reach IH06 asset/turbine nodes by site and turbine token. This is useful structural alignment, but it is not yet a FLOC leaf label. The plan constraint still applies: the reachable IH06 leaf is component/maintainable-item depth, and a service order asset reference alone does not select one of the child leaf nodes.

Therefore G1.2 moves FLOC from a raw zero to a bounded alignment result:

- Site and turbine alignment is feasible per site.
- IH06 reachable depth is declared per site.
- FLOC leaf is not admitted as an evaluation/training label from this step alone.
- A future leaf proxy would need a component selector from text or another structured field, constrained to high-band reference anchors.

## Governance

- FLOC remains a separate namespace from SAP catalog targets.
- No cross-site depth aggregation.
- Max depth 4 at a site is not interpreted as asset property; it may reflect extract/modeling depth.
- Versioned outputs contain hashes, counts, statuses, and metadata only.

## Target Registration

G1.2 closes with two distinct target names:

| Target | Registration | Units | Granularity |
|---|---:|---:|---|
| FLOC leaf | HOLD | 0 | component/maintainable-item leaf not reachable from source alone |
| FLOC turbine | ADMIT | 10,699 | site + turbine asset node, match rate 99.53484% |

The descent from turbine to component is registered as debt, not as an open G1 blocker. The only currently available component selector is the G1.1 consumption path, which reaches 3,027 of 10,749 orders (28.160759%) through strong/medium material-to-Catalog-B candidates. That work belongs to G2 or later.

## SITE-003 Exception Audit

SITE-003 has 33 unmatched orders, an order of magnitude more than the other sites. The exception is explained: all 33 use the site-level `Other Equip.` pad, with 32 Substation orders and 1 SCADA System order. They do not carry turbine tokens, so the turbine-node alignment correctly leaves them unmatched.

The count of 1,581 SITE-003 service orders matches the Path A concern-table row count, but this is a numeric coincidence across different namespaces and branches. It is not treated as evidence of overlap.

## Scope Boundary: BOP Assets

The SITE-003 exception audit surfaced a lateral scope boundary: the corpus contains maintenance orders on balance-of-plant assets, not only wind turbines. In this run the visible cases are Substation and SCADA orders.

This does not materially affect the G1.2 volume because it accounts for 33 of 10,749 service orders. It does matter for scope: the current reference taxonomy is turbine-centric, and BOP components do not have a declared landing point in the IEC/ZEUS-style turbine vocabulary. If similar records appear in other branches, they should be tracked as a separate scope boundary rather than forced into turbine component labels.
