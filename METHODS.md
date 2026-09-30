# Method

The source run used PLUM with seed 42 to generate 200,000 candidates in chunks
of 5,000. Chunk `i` used seed `42 + i`. Target lengths were sampled from 8–35.
The decoder samples amino-acid tokens for the requested number of steps,
omitting special tokens from the recorded sequence; it does not terminate the
sampling loop on the stop token. No sequence-specific seed input is used.

Candidates were restricted to canonical amino acids, deduplicated, and excluded
if identical to a PLUM `train.csv` sequence or an official antibacterial reference.
Other filters were instability index ≤40, charge at pH 7 from +2 to +10,
and mean Eisenberg hydrophobicity from −0.5 to +0.8. These are project screening
choices, not additional organizer requirements. The retained pool contained
109,504 unique sequences.

APEX predictions used an eight-model geometric-mean ensemble. Its family score
was the mean percentile rank across 11 outputs. Deep-AMP supplied separate
Gram-negative and Gram-positive percentile ranks. Lower ranks were preferred:

`cheap_score = 0.50 × APEX_family + 0.25 × DeepAMP_Gram_negative + 0.25 × DeepAMP_Gram_positive`

All filter survivors were scored. The first 50,000 by ascending score and then
alphabetical sequence order formed the library. No later model changed its
membership. The original archive's equal-third wording is superseded by this
formula, which matches the executed code and exported scores.

HemoPI2 1.3 model 3, threshold 0.58, screened candidates in library-ranking order:
4,000 initially, then batches of 500. After 8,500 candidates, 2,093 were labeled
Non-Hemolytic. The first 2,000 eligible candidates by library ranking formed the
elite panel. The remaining library members were not all screened for hemolysis.

tsAMP-CS used ESM-1v residue-mean peptide embeddings, released strain embeddings,
and the reconstructed checkpoint-compatible 2560→128→64→1 network with ReLU after
the first two layers. It supplied predictions for 11 exact challenge strains.
LLAMP supplied species-level estimates for the other nine targets, spanning six
species. The same species estimate is repeated for three E. coli targets and
two Salmonella targets. These repeats are not independent strain predictions.

Final sorting used, in order: predicted MIC ≤16 µM passes out of 20, descending;
tsAMP-CS passes out of 11, descending; mean predicted log10 MIC across the 20
targets, ascending; and alphabetical sequence order. Walking that order, a
candidate was accepted only if its Levenshtein ratio was ≤0.80 against every
official reference and previously selected candidate. Selection stopped at 100.
APEX/Deep-AMP affect upstream membership and shortlisting but not this final score.

# Results and evidence

The completed run produced 50,000 library sequences and 100 ranked selections.
All 100 had predicted 20/20 passes. They are computational predictions, not
experimental activity or safety measurements. The archive audit reproduced
library membership, elite ordering, and the Top-100 similarity selection.
All 798 available checkpoint input/output hash comparisons matched; external
model files absent from the archive were not independently hashed in that audit.

LLAMP reproduced the authors' example with absolute log10 difference
0.0002849102, below the notebook's 0.001 tolerance. Prior project records report
tsAMP-CS held-out tests across ten species; raw test runs are not bundled here,
and exact agreement with the authors' implementation is not established.
Prior LLAMP external testing reported weak absolute calibration and uneven
species performance. Neither model's validation guarantees performance for
these newly generated candidates.

The software path is automated. I did not personally hand-edit or select individual
sequences, add outside sequences, or choose the best result among alternative full
runs or random seeds. I chose models and filter settings during development and
used the planned settings for the completed run. These statements describe my
process; automated checks alone cannot establish that history. I did not retrain
any model in the packaged generation path.

# Packaged-run verification

On 2026-09-28, commit `6dc67d47e3074838136bad7d168871de4f4e8644`
completed generation and scoring on a Colab Tesla T4 with no completed stage
checkpoints at generation startup. My run output shows that both
exported FASTA hashes exactly matched the audited source-run files. Official
sequence-check functions passed on these newly generated files. The complete
validator and its same-directory repeat-invocation check were not completed.
This evidence concerns software execution and exported-file agreement, not
experimental activity or independent validation of the scoring models.
