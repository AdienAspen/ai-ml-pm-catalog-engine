# G2.0h - IH06 profile inheritance audit

Scope: B1 relational, 10,749 orders; G1.2 matched turbine nodes only.
Hierarchy: exact `Superior functional location` links in IH06. No default profile.

- Direct RBNR on matched node: 9,151 orders.
- No RBNR on matched node, tested for inheritance: 1,548 orders across 16 nodes.
- Inherited RBNR: 0 orders; distribution: {}.
- `no_profile_no_filter` (no valid RBNR on any ancestor): 1,548 orders.
- Missing parent node: 0; cycles: 0.
- Walked edges (all tested orders): {'1': 1548}.
- Site keys of tested orders: {'SITE-003': 1548}.
- G1.2 unmatched orders outside inheritance scope: 50.

## Unresolved node characterization

- 16 distinct G1.2 turbine nodes remain unresolved by upward inheritance.
- IH06 turbine-description marker present on 16 of 16 nodes.
- The parent root has no RBNR and no further ancestor. These are not classified as substation, SCADA, or balance-of-plant assets.
- Each unresolved turbine node has profiled descendants. Their RBNR values are not inherited upward and require component/leaf resolution (G2.0i).

## G2.0i controls carried forward

- Text-derived Object Part evidence cannot independently evaluate the FLOC/profile-constrained code space it helped create.
- Evaluate FLOC against independent structural evidence where available; otherwise declare the dependency.
- Match within site and turbine, report resolved/ambiguous/abstained per order, and verify profile -> type -> group -> codes before any answer-space figure.
- Information-type presence and classification into catalog codes are separate claims; the latter has not been measured here.

No mapping, candidate promotion, or F6 denominator change was made.
