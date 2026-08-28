# FLOC Leaf Depth Design Constraint

## Scope

This note records the IH06 depth finding as a design constraint for the FLOC leaf segment target.

## Finding

The IH06 crosscheck read 88,441 rows and measured FLOC hierarchy depth by sanitized site key.

Within the sanitized pass:

- Minimum site max depth: 4
- Maximum site max depth: 5
- Rows observed at depth >= 6: 0

## Design Constraint

For the PoC reference layer, FLOC leaf segment derivation must be constrained to the hierarchy depth observed in IH06. The current evidence suggests the deepest consistently available structure reaches the component/assembly-proxy range, not an arbitrarily deeper hierarchy.

## Interpretation Boundary

This is a structure/readiness constraint, not a final semantic ISO 14224 mapping and not a production runtime guarantee.

The IEC 21-node missing-system analysis remains blocked until the authoritative 21-node reference file is populated with actual node codes and labels.
