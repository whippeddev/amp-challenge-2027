# Packaging changes

The source is `notebooks/AMP_Library_Selection.ipynb`; its original SHA-256 is
recorded in `records/notebook_source.json`. `src/amp_submission/pipeline.py`
contains the same computational stages as a command-line script.

Changes made for packaging:

- Replace Colab Drive mounting and `/content` paths with configurable work/tools
  directories. Remove automatic browser downloads and backup-ZIP creation.
- Replace runtime pip installs with three dependency-locked `uv` environments.
  Require preinstalled git-lfs instead of changing system packages.
- Replace notebook table display with console output.
- Copy the bundled, checksum-verified official reference instead of downloading it.
- Verify PLUM checkpoint, PLUM training-reference, and LLAMP checkpoint hashes
  against the completed run's recorded values.
- Pin the LLAMP Hugging Face snapshot to the revision recorded by its successful
  official-example check. Pass the resolved local snapshot to the same model and
  tokenizer constructors; retain the published model identifier in provenance.
- Export generated results to `generate/`. Stored reference FASTA files are used
  only for comparison and file validation, never as the `generate` output source.

Generation parameters, filter thresholds, model forward passes, scoring weights,
ranking keys, and similarity thresholds were preserved. The preceding v14 edit
also corrected stale completion status and scoring descriptions, recorded output
hashes, and clarified the development history.

Original Colab environments are recorded under `records/original_*_packages.txt`.
Package locks are generated for the portable environments. A fresh packaged run
on 2026-09-28 produced byte-identical library and Top-100 FASTA files compared with
the audited source run. This establishes agreement for those exports, not every
intermediate numerical score. See `records/reproduction_validation_2026-09-28.json`.

The CLI now selects the non-interactive Matplotlib Agg backend before loading the
pipeline. This fixes a Colab-inherited notebook backend error without changing
sequence generation, model scoring, or selection.

The historical source records are not rewritten. In particular,
`original_method_and_versions.json` contains stale equal-third scoring wording
and an earlier manual-intervention statement. The executed weighting is
50%/25%/25%; the current development summary is in SUBMISSION.md.
