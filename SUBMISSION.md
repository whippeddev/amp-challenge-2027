# PLUM generation with staged antimicrobial peptide selection

## Abstract

I developed an automated pipeline that combines pretrained models to generate and select antimicrobial peptides. PLUM generated 200,000 candidates, which were filtered for sequence validity, duplicates, reference matches, and physicochemical properties. APEX and Deep-AMP scores were then used to build a library of 50,000 peptides. HemoPI2 screening identified a shortlist of 2,000 predicted non-hemolytic candidates for final activity scoring.

tsAMP-CS supplied predictions for 11 challenge strains, while LLAMP supplied species-level estimates for the remaining nine targets. Candidates were ranked primarily by the number of targets with predicted minimum inhibitory concentration (MIC) at or below 16 µM. Similarity filtering against the official reference set and between selected candidates produced the ranked top 100. All 100 met the predicted activity threshold across the combined 20-target panel. These results are computational predictions and have not been experimentally validated; LLAMP estimates are shared by targets of the same species and do not establish activity against each individual strain.

## Data, models, and filters

I used released pretrained models without training or fine-tuning them. The pipeline combines PLUM, APEX, Deep-AMP, HemoPI2 1.3, tsAMP-CS, ESM-1v, LLAMP, and peptide-tuned ESM-2. [DATA_AND_MODELS.md](https://github.com/whippeddev/amp-challenge-2027/blob/main/DATA_AND_MODELS.md) lists their sources and roles; [model_sources.json](https://github.com/whippeddev/amp-challenge-2027/blob/main/records/model_sources.json) records revisions and weight locations. The upstream models' complete training-data provenance and overlap have not been independently verified.

The submitted peptides are linear, have free termini, and use only the standard amino acids. Filtering removed duplicates and exact matches to PLUM's released training CSV and the organizers' antibacterial reference. Candidates also had to meet an instability index of at most 40, charge at pH 7 between +2 and +10, and mean Eisenberg hydrophobicity between −0.5 and +0.8. These filters retained 109,504 unique peptides.

## Selection and ranking

The first 50,000 peptides by a weighted percentile score formed the library: 50% APEX, 25% Deep-AMP Gram-negative, and 25% Deep-AMP Gram-positive, with lower scores preferred and alphabetical sequence order breaking ties.

HemoPI2 model 3, at threshold 0.58, screened 8,500 candidates in library order. Of these, 2,093 were predicted non-hemolytic; the first 2,000 by library ranking advanced to tsAMP-CS and LLAMP scoring. The rest of the library was not fully screened for hemolysis.

Final ranking used:

1. Number of targets with predicted MIC ≤16 µM across the combined panel of 20, highest first.
2. Number meeting that threshold among the 11 tsAMP-CS strains, highest first.
3. Mean predicted log10 MIC across the 20 targets, lowest first.
4. Alphabetical sequence order.

Walking this ranking, a peptide was selected only if its Levenshtein similarity ratio was ≤0.80 against every official reference peptide and every previously selected candidate. Selection stopped at 100. The attached top.fasta preserves this order, and every selected peptide belongs to library.fasta. APEX and Deep-AMP were used for the earlier library selection, not the final ranking. [METHODS.md](https://github.com/whippeddev/amp-challenge-2027/blob/main/METHODS.md) gives the full procedure.

## Development and manual intervention

I chose the models and filter settings during development. The completed run used the planned settings; I did not choose it as the best result among alternative full runs or random seeds. I did not manually select, edit, delete, reorder, or add individual peptide sequences.

Earlier development included AMP-Diffusion experiments, OmegAMP benchmark comparisons, and BattleAMP website exploration. These did not supply sequences to the final PLUM-generated library.

## Limitations

Predicted activity and hemolysis still need experimental testing. LLAMP's nine target estimates cover six species, with one estimate reused for three E. coli targets and another for two Salmonella targets. Absolute MIC calibration is uncertain. The tsAMP-CS inference network was reconstructed to load the released checkpoints, but exact agreement with the authors' implementation has not been established.

## Code and verification

Repository and run instructions. Model weights are downloaded from upstream sources at runtime rather than bundled in the repository.

A fresh packaged run on a Colab Tesla T4 on September 28, 2026 produced library and top-100 FASTA files with hashes matching the original run. The organizers' sequence-check functions passed. The full repository validator, including its repeat invocation in the same directory, was not completed.

THIRD_PARTY.md documents third-party licenses.
