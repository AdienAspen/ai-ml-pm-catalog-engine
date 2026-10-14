# G2.0e/G2.0f response registration and agreement

Four original user-supplied CSV batches are preserved unchanged in the private
responses tree (mode 600), separately from empty templates. No responses were
assigned, corrected, normalized, merged, or adjudicated by DevOps.

## Structural gate

Activity 01 and 02 are valid (187/188 rows). Damage 01 is rejected: 141 level-1
none_applicable outcomes have a nonempty code. Damage 02 is rejected: the last
record G20EF-DAMAGE-0293 has two CSV fields rather than three. Its intended code
is not inferred. All four batches have the package ID sets and the declared 75
shared IDs per target. Damage agreement at both levels is blocked, not zero.
Corrected whole-file resubmissions must come from the annotators; originals
remain available for provenance.

## Activity agreement

On the 75 shared physical units: 42/75 match;
raw agreement 0.560000, Cohen kappa
0.086379, Gwet AC1 0.537767.
Full confusion and per-class specific agreement are separate sanitized files.
Specific agreement is 2*diagonal/(row marginal + column marginal); unobserved
classes are not estimable. AC1 uses all nine prespecified nominal categories,
not only categories observed in the overlap. Formula reference: https://pmc.ncbi.nlm.nih.gov/articles/PMC5965565/

Both Activity batches have zero abstentions; this is a process-review flag, not
proof of mechanical annotation. Activity 01 assigns TEST once, outside the
overlap; Activity 02 assigns no catalogue code. The 375 annotation responses
are not 375 unique units (300 unique units, including 75 shared). There is no
paired evidence to assess agreement on an assigned catalogue code.

Rates are annotation-sample summaries, not corpus-wide code-coverage estimates.
Activity was sampled only from the 1,234-unit frame left after exclusions. Every
metric is B1_RELATIONAL, g01-v2 blind-LLM non-final evaluation, n=75 for agreement,
with no classifier threshold. eligible_for_final_heldout remains false.
No SAP correctness, final-heldout performance, or definitive absence of corpus
signal follows from these agreement statistics. Damage conclusions await valid
resubmissions. Actual model identity and no-script compliance cannot be verified
from response values alone. No denominator or frozen evaluation set is changed.
