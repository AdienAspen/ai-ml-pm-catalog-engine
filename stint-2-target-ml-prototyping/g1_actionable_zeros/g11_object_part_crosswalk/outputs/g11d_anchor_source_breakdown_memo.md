# G1.1d Anchor Source Breakdown Memo

G1.1d breaks down the 3,737 B1 no-item orders with at least one high-band Object Part lexical anchor by `anchor_source`.

This is counting only. No candidate was promoted and no denominator was changed.

## Result

All matched high-band Object Part anchors in this pass originate from `sap_catalog` (`SAP_MAPPING` / Catalog B vocabulary). No matched order is anchored exclusively through `domain_vocabulary`, and no matched concept originates from `domain_vocabulary`.

## Interpretation

The 3,737 orders reported in G1.1c should be treated as catalogue-anchored textual residual, not as technician-language residual. Given the known over-generation behavior of catalogue concepts, this is a weaker ML-addressable signal than the headline count alone suggests.
