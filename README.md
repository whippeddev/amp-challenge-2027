# AMP Challenge 2027 submission

PLUM generation, physicochemical filtering, APEX/Deep-AMP library selection,
HemoPI2 screening, and tsAMP-CS/LLAMP ranking. The default run generates
200,000 raw candidates and writes a 50,000-member library and ranked Top 100.

## Status

The audited original run's sequence files are in `results/reference_run/`.
On 2026-09-28, the packaged pipeline completed a fresh generation and scoring run
on a Colab Tesla T4. Both exported FASTA SHA-256 hashes exactly matched the audited
reference files, and the organizers' sequence-check functions passed on the new
outputs. Evidence is the submitter-provided execution logs and check output.

A second invocation using existing checkpoints was not tested before the Colab
runtime was lost. The full official repository validator has not been run end to
end; installation, generation, and sequence checks were exercised separately.
See `records/reproduction_validation_2026-09-28.json` for the tested commit and
scope, and `SUBMISSION_REVIEW.md` for remaining submission questions.

## Colab setup

In a fresh Colab notebook, select a GPU runtime and run `!nvidia-smi` to
confirm that a GPU is connected. Then run this setup cell:

```python
import subprocess
import sys

commands = [
    [sys.executable, "-m", "pip", "install", "-q", "uv"],
    ["apt-get", "update", "-qq"],
    ["apt-get", "install", "-y", "-qq", "git-lfs"],
    ["uv", "--version"],
    ["git", "--version"],
    ["git", "lfs", "version"],
]

for command in commands:
    subprocess.run(command, check=True)
```

This cell prepares Colab's system tools; it does not run model inference.
The `apt-get` commands are specific to Colab's Debian/Ubuntu-based environment,
not a universal installation procedure. Project Python dependencies are managed
separately by the three committed lock files.

Before running the project, clone the repository and use its root directory.
A private repository requires GitHub authentication in the Colab runtime.
Repeat this setup when using a new runtime. Files on Colab's temporary disk,
including checkpoints, are not durable backups.

## Run

Use Linux x86_64 with `uv`, `git`, and `git-lfs`. The successful source run
used a Tesla T4 GPU and Python 3.13.15. Model downloads require network access;
CPU fallback exists in the source but its full-run duration is unverified.

```bash
uv sync
uv run generate
```

Outputs: `generate/library.fasta`, `generate/top.fasta`, plus method/check records.
Defaults: seed 42, 200,000 raw candidates, 50,000 library members, 2,000 elite
candidates, and 100 final selections. This command runs generation and inference;
it never copies the reference results as a substitute for model execution.

Checkpoints persist under `.amp-work/full-run1/`; models and auxiliary environments
persist under `.amp-tools/`. Repeating the command resumes matching checkpoints.
Use `--work-dir .amp-work/independent-run` for a fresh calculation. All arguments
have defaults. `--output-dir` and `--tools-dir` can also be set explicitly.

Three `uv.lock` files pin the main, Deep-AMP, and HemoPI2 environments. Auxiliary
environments are installed automatically into the tools directory. The source
notebook remains in `notebooks/` as the Colab workflow.

## Validate

Validate the existing reference FASTA files without model inference:

```bash
uv run check-files
```

This invokes the organizers' sequence-check functions. For newly generated files,
use `uv run check-files --directory generate`. These checks do not establish
installation reproducibility, scientific performance, or licensing eligibility.

The unchanged official validator is available for end-to-end verification:

```bash
uv run python scripts/verify_submission.py <github-url>
```

It clones into `submission/`, installs dependencies, runs generation, checks the
FASTA files against `data/antibacterial.fasta`, and invokes generation again to
compare both files byte-for-byte. A repeat with warm checkpoints is not an
independent cold-start rerun; a separate fresh work directory can test that too.

## Documentation

- `METHODS.md`: implemented selection procedure and limitations.
- `DATA_AND_MODELS.md`: component sources and data-disclosure gaps.
- `ABSTRACT_DRAFT.md`: draft method summary for review.
- `PACKAGING_CHANGES.md`: notebook-to-command changes.
- `THIRD_PARTY.md`: scope of bundled and downloaded components.
- `records/`: original run records, audit, and packaging validation.

The original records are retained verbatim and include superseded descriptions
of early scoring weights. `METHODS.md` and `PACKAGING_CHANGES.md` identify those
corrections. No submitter declaration is inferred from the automated checks.
