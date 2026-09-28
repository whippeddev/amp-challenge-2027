# Submission document review — 2026-09-28

## Confirmed from code, saved records, and supplied run output

- Public repository contains a defined generation entry point, three dependency locks, reference outputs, methods, and a draft abstract.
- Packaged generation at commit `6dc67d47e3074838136bad7d168871de4f4e8644` completed; both output hashes match the audited original run.
- Newly generated files passed the official sequence-check functions.
- Abstract and methods agree on 200,000 generated candidates, 109,504 filter survivors, a 50,000-member library, 8,500 screened for hemolysis, 2,093 predicted non-hemolytic candidates, and a 2,000-candidate elite panel.
- Early weights are 50% APEX and 25% each Deep-AMP Gram-negative and Gram-positive. Final ranking uses total passes, tsAMP-CS passes, mean predicted log10 MIC, then alphabetical sequence order.
- The Top 100 reference and pairwise Levenshtein limits are ≤0.80.
- Activity and hemolysis are predictions. LLAMP's species estimates repeated across strain targets are not independent strain predictions.

## Submitter-confirmed declaration — 2026-09-28

The submitter confirmed that they did not personally hand-pick, edit, delete, or
reorder individual peptide sequences, or manually add outside sequences. This is
a submitter declaration, not a conclusion established by the automated audit.
Choosing models and filter settings was explicitly excluded from this question.
The response does not establish whether alternative runs or seeds were compared.

## Unresolved before final declarations

| Item | Current evidence and remaining action |
|---|---|
| Run and seed selection | Manual addition of outside sequences was denied in the submitter declaration above. Any sequence-specific seeding or selection among alternative runs/seeds outside the documented workflow remains to be confirmed. |
| Historical experiments | Earlier records mention AMP-Diffusion, OmegAMP benchmark peptides, and BattleAMP website exploration. Complete the factual history and distinguish experiments from inputs to the final pipeline. |
| Upstream training data | A final source inventory exists, but complete training-data provenance, availability, overlaps, and any non-public data remain to be reviewed. |
| Upstream licenses | Project MIT licensing does not establish permission for every upstream codebase, weight file, or dataset. Full review remains open; permissive-release/co-authorship eligibility is not established. |
| Weight access | Weights download from upstream sources and were accessible in the completed run. They are not bundled in this repository. Confirm that this delivery method meets the organizers' model-weight requirement. |
| Repeat-run validation | Existing-checkpoint repeat was not tested after runtime loss. Full official validator remains unrun. Record this limitation; do not claim it passed. |
| Submission fields | Confirm current Kaggle file naming/format, document fields and limits, authorship details, and final uploads before submitting. |

## Corrections made in this review

README, packaging notes, and current validation metadata now reflect the successful packaged run. Original historical records remain unchanged. Run evidence is attributed to submitter-provided output rather than represented as an independent execution by the reviewer.

The abstract remains a draft. No model, weight, filter, ranking rule, or output sequence was changed in this review. Nothing has been submitted to the competition.
