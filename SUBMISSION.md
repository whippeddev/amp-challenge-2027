# PLUM generation with staged antimicrobial peptide selection

Submission scope: minimum benchmark participation; co-authorship eligibility is not claimed.

## Submission files and code

- [50,000-sequence library](https://github.com/whippeddev/amp-challenge-2027/blob/main/results/reference_run/library.fasta)
- [Ranked top 100](https://github.com/whippeddev/amp-challenge-2027/blob/main/results/reference_run/top.fasta)
- [Inference code and usage instructions](https://github.com/whippeddev/amp-challenge-2027)
- [Detailed selection and ranking procedure](https://github.com/whippeddev/amp-challenge-2027/blob/main/METHODS.md)
- [Model sources, revisions, and weight locations](https://github.com/whippeddev/amp-challenge-2027/blob/main/records/model_sources.json)

The FASTA files are the completed-run outputs. Their sequence order is preserved.

## Abstract

We developed an automated pipeline for antimicrobial peptide generation and selection using released pretrained models without additional model training. PLUM generated 200,000 candidates using a fixed seed schedule. Sequence-validity, duplicate, reference-exclusion, and physicochemical filters retained 109,504 unique peptides. A weighted combination of APEX and Deep-AMP percentile scores selected a 50,000-member library, with weights of 50% for APEX and 25% each for Deep-AMP Gram-negative and Gram-positive predictions. HemoPI2 screened 8,500 library members; 2,093 were predicted non-hemolytic, and the first 2,000 by library ranking advanced to activity scoring.

tsAMP-CS provided predictions for 11 challenge strains, while LLAMP provided species-level estimates for the remaining nine targets. Candidates were ranked by the number of targets with predicted minimum inhibitory concentration (MIC) ≤16 µM, with ties resolved by higher tsAMP-CS coverage, lower mean predicted log10 MIC, and alphabetical sequence order. The final 100 candidates met the official reference-exclusion criterion of Levenshtein similarity ratios ≤0.80; an additional project diversity filter imposed the same limit between selected candidates. All 100 met the predicted activity threshold for all 20 targets. These predictions have not been experimentally validated; LLAMP estimates shared across strains are not independent strain-level predictions. Additional limitations include uncertain MIC calibration and a reconstructed tsAMP-CS inference implementation whose exact equivalence to the authors’ implementation has not been established. An audit of saved run records reproduced library membership and final selection. A subsequent fresh packaged run produced byte-identical library and top-100 files and passed the organizers' sequence-check functions, according to the submitter's execution logs. The complete end-to-end repository validator was not run.


## Data, models, and filters

No model was trained or fine-tuned in this submission pipeline. It uses released pretrained PLUM, APEX, Deep-AMP, HemoPI2 1.3, tsAMP-CS, ESM-1v, LLAMP, and the peptide-tuned ESM-2 model. The component sources are listed in [DATA_AND_MODELS.md](https://github.com/whippeddev/amp-challenge-2027/blob/main/DATA_AND_MODELS.md), with exact revisions and weight locations in [model_sources.json](https://github.com/whippeddev/amp-challenge-2027/blob/main/records/model_sources.json).

PLUM's released `data/train.csv` and the organizers' `antibacterial.fasta` are used for sequence exclusion. Candidates must use canonical amino acids and pass duplicate removal, an instability index limit of 40, charge at pH 7 between +2 and +10, and mean Eisenberg hydrophobicity between -0.5 and +0.8. The full library excludes exact matches to both reference inputs. The top 100 additionally satisfy Levenshtein ratios no greater than 0.80 against the official antibacterial reference and previously selected candidates. HemoPI2 model 3 uses threshold 0.58. Full scoring, filtering, and tie-breaking details are in METHODS.md.

Earlier development included AMP-Diffusion experiments, external benchmark comparisons including OmegAMP, and BattleAMP website exploration. These were not sources of peptide sequences inserted into the final PLUM-generated library. Upstream models' complete training-data provenance and overlap have not been independently established; identifying their public sources does not certify all upstream training data or redistribution permissions.

## Manual intervention

As confirmed by the submitter on September 28, 2026: the submitter did not personally hand-pick, edit, delete, or reorder individual peptide sequences, or manually add outside sequences. Models and filter settings were selected during development. The completed run used the planned settings; it was not selected as the best result among alternative full runs or random seeds. Earlier development tests did occur. These are submitter declarations, not conclusions inferred from automated checks.

## Weight access and verification

The code downloads released weights from upstream sources at runtime. Weight locations and pinned revisions are recorded in the repository; the weights are not bundled here. The packaged pipeline completed a fresh generation and scoring run on a Colab Tesla T4 on September 28, 2026. Both exported FASTA hashes matched the audited reference files, and the organizers' sequence-check functions passed, as recorded from submitter-provided run output.

The complete official repository validator and its same-directory repeat invocation were not completed. This submission does not claim those checks passed. The predictions are not experimental measurements of antimicrobial activity or safety. Third-party licenses retain their own terms; the project's MIT license does not relicense upstream weights, code, or data.

## Unresolved eligibility disclosures

This is a request for minimum benchmark participation, not a certification that all eligibility questions have been resolved. The existing [third-party review](https://github.com/whippeddev/amp-challenge-2027/blob/main/THIRD_PARTY.md) records that the pinned LLAMP source code uses PolyForm Noncommercial 1.0.0 and flags a potential conflict with competition rule 6(c). Minimum participation does not itself resolve that issue. Permissions for the tsAMP checkpoints/strain embeddings and peptide-tuned ESM-2 release, and separate LLAMP weight/data terms, remain unestablished in the current review. Complete upstream training-data provenance and acceptance of runtime weight downloads also remain unresolved. No contrary compliance declaration is made here.
