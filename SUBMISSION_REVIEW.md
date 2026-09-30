# Submission summary

## Current status

The [Kaggle write-up](https://www.kaggle.com/competitions/amp-challenge/writeups/plum-generation-with-staged-antimicrobial-peptide) is submitted, with
`library.fasta` and `top.fasta` attached and this repository linked.
The final write-up is in [SUBMISSION.md](SUBMISSION.md).

## Completed checks

- The packaged run at commit `6dc67d47e3074838136bad7d168871de4f4e8644`
  completed on September 28, 2026. Both exported FASTA hashes matched the original run.
- Newly generated files passed the organizers' sequence-check functions.
- The run produced 200,000 candidates, 109,504 filter survivors, a 50,000-member
  library, and 100 ranked selections.
- HemoPI2 screened 8,500 peptides, identified 2,093 as predicted non-hemolytic,
  and the first 2,000 by library ranking advanced to final scoring.
- Current documentation uses the executed 50%/25%/25% early scoring weights.
  Final ranking uses total predicted passes, tsAMP-CS passes, mean predicted
  log10 MIC, and alphabetical sequence order.
- Top-100 reference and pairwise Levenshtein limits are ≤0.80.

## Development process

I chose the models and filter settings during development and used the planned
settings for the completed run. I did not manually select, edit, delete, reorder,
or add individual peptide sequences, or choose the best result among alternative
full runs or random seeds. Earlier development tests are described in SUBMISSION.md.

## Remaining limitations

The full official repository validator and its same-directory repeat invocation
were not completed. Activity and hemolysis remain predictions, and LLAMP's repeated
species estimates are not independent strain predictions. Scientific limitations
are described in METHODS.md; unresolved upstream terms are recorded in THIRD_PARTY.md.

Model weights download from upstream at runtime and are not bundled. Organizer
acceptance of this delivery method and complete upstream training-data provenance
have not been established.

This summary replaces the pre-submission checklist. Original run records remain
in `records/`.
