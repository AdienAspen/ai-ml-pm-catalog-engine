# G1.1c No-Item Signal Profile Memo

G1.1c profiles the 6,670 B1 service orders without consumption item signal. This is a scope audit only: it does not promote candidates and does not alter the Object Part denominator.

## Text Availability

- Non-empty `descriptionExtended`: 6,380 (95.65%)
- Non-empty `reason`: 6,321 (94.77%)
- Non-empty combined text: 6,668 (99.97%)

## Lexical High-Band Anchor

Object Part lexical_layer_v2 high-band canonical concepts were phrase-matched against `descriptionExtended + reason` for profiling only.

- High-band Object Part canonical concepts loaded: 145
- Orders with at least one high-band Object Part anchor: 3,737 (56.03%)
- Unique high-band concepts matched: 70

## Governance

- No parser was introduced.
- No candidate was promoted.
- No denominator was changed.
- Versioned outputs do not emit raw order text.
