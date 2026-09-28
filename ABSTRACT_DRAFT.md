# Draft abstract

We assembled a computational pipeline for generating and selecting antimicrobial
peptide candidates using released pretrained models. PLUM generated 200,000
candidates with a fixed random seed. Canonical-residue, length, uniqueness,
reference-exclusion, and physicochemical filters retained 109,504 sequences.
APEX and Deep-AMP percentile scores selected a 50,000-member library. HemoPI2
screening identified an elite panel of 2,000 candidates predicted to be
non-hemolytic. tsAMP-CS supplied activity estimates for 11 challenge strains,
while LLAMP supplied species-level estimates for nine remaining targets.
Candidates were ranked by predicted activity coverage at MIC ≤16 µM, followed
by tsAMP-CS coverage and mean predicted log10 MIC. Reference and internal
similarity constraints produced the final ranked Top 100. All selected
candidates had predicted coverage of 20/20 targets; this has not been confirmed
experimentally. Limitations include reconstructed tsAMP-CS inference, imperfect
MIC calibration, and repeated species-level LLAMP estimates across related
strain targets. The pipeline uses checkpointed stages and records model
revisions, software environments, and output fingerprints.
