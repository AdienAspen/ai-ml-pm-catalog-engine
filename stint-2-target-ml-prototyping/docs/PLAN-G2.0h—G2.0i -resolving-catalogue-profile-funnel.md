# G2.0h + G2.0i — Resolving the Catalogue Profile Funnel

**FSA BRIDGE / STINT_2 · Priority 1**
Sequential: `G2.0h` first — its result scopes `G2.0i`.

---

## Why this exists

The Wind Catalog inventory established two things:

```
five targets have a verified destination     S · B · C · 5 · A
the Catalog Profile (RBNR) narrows the answer space per record
```

Under `PMMUWW` — the turbine profile — the space collapses from thousands of codes to tens:

```
Symptom      4,171 codes  →  1 group ·  6 codes
Cause        6,232        →  1 group · 13 codes
Damage       1,505        →  9 groups · 94 codes
Activity       490        →  1 group ·  5 codes
Object Part  1,240        →  1 group ·  1 code    ← collapses
```

**Object Part collapsing to a single code shows the turbine profile is not the right level for that target.** The specification requires resolving the equipment or leaf first and using its profile, which is more specific.

Two gaps block that:

```
1,548 orders     reach an IH06 node with an empty RBNR field
0 / 10,749       assetId → IH08.Equipment linkage does not exist
```

**These two steps close the first gap and work around the second.**

---

# G2.0h — Profile Inheritance from Parent Nodes

**Run first.** Estimated: half a day.

## Objective

Determine whether the 1,548 orders without a profile can inherit one from their parent node in the IH06 hierarchy.

In SAP, a functional location without its own `RBNR` commonly operates under the profile of its parent. This is a hierarchy lookup, not an inference.

## Tasks

```
1. For each of the 1,548 orders, walk up the IH06 hierarchy from its
   node until a node with a non-empty RBNR is found.
   Report: how many resolve, at what depth, to which profile.

2. Characterise the nodes that remain unresolved after walking up.
   What kind of asset are they? Subestation, SCADA, balance of plant,
   or turbine nodes that simply lack configuration.

3. Report the profile distribution of the resolved set. If any
   profile other than PMMUWW appears, report it separately — it may
   indicate non-turbine assets in the relational path.
```

## Output

```
g20h_profile_inheritance_sanitized.csv     order · node · depth walked
                                            · inherited RBNR
g20h_unresolved_node_profile_sanitized.csv  what the remainder are
g20h_memo.md
```

⚠️ **Inheritance is a hierarchy lookup, not an assumption.** If a node has no ancestor with `RBNR`, report it as unresolved. Do not assign `PMMUWW` by default because most orders carry it.

---

# G2.0i — Component Resolution from Text

**Run after `G2.0h`.** Estimated: 1–2 days.

## Objective

Resolve the component node for each order using the textual signal we already have, and read the profile from that node instead of from the turbine node.

**This inverts the dependency.** Instead of waiting for a structural link that does not exist in the data, it uses the component vocabulary already built and validated.

## The chain

```
order text
   → component concept          Object Part vocabulary · 7,668 units detected
   → IH06 node for that component under the order's turbine
   → RBNR of that node
   → valid catalogue codes for all five targets
```

## Tasks

```
1. Inventory the IH06 subtree below turbine nodes.
   What component-level nodes exist, at what depth, and how many
   carry their own RBNR. Report per site — depth is not homogeneous.

2. Match the component concepts from G2.0c against those node
   descriptions. Use semantic matching, the same pipeline as
   T5.1b2.X-normalized. Freeze the threshold before running.

3. For orders where a component node resolves, report:
     the node · its RBNR · the answer space it produces per target
     compared against the turbine-level space

4. Report coverage: how many of the 10,749 orders resolve to a
   component node, and how many remain at turbine level.
```

## What this produces

**Two things at once:**

```
FLOC leaf        the target currently at zero
                 the component node IS the leaf code

profile funnel   the correct answer space for the other four targets
                 replacing the turbine-level profile
```

## Provenance

```
evidence_type            expert_inference
tier                     silver-medium maximum
label_generation_method  semantic_component_node_resolution_v1
embedding_model          paraphrase-multilingual-MiniLM-L12-v2
anchor_source            domain_vocabulary
evaluation_independence  derived_from_rules
```

⚠️ **Resolving a component node is a candidate, not a verified FLOC assignment.** The order does not state which component was worked on; this derives it from text. Register it as such.

---

## Constraints — both steps

- Report only. No denominator change, no promotion, no F6 update.
- Never aggregate across paths. This applies to B1; Path A and B2
  have no equivalent structure.
- Sanitised versioned outputs. No raw site names, no PII.
- Freeze thresholds before looking at results.
- `anchor_source` as a literal field on every evidence row.

---

## What these unblock

```
G2.0j     re-measure Symptom and Cause against their real groups
          with the correct profile applied
G2.0e     Activity against its 92 MNGRP, under the right profile
F6        final denominator update
G2        scoping decision with a bounded answer space
```

**Until the profile level is resolved, every answer space we report is either too coarse — turbine level — or absent — the 1,548 without profile.**
