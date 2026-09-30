# AMP Challenge 2027 submission

An automated pipeline for generating and selecting antimicrobial peptides with
pretrained models. PLUM generates 200,000 candidates; sequence and physicochemical
filters, APEX/Deep-AMP scoring, HemoPI2 screening, and tsAMP-CS/LLAMP ranking produce
a library of 50,000 peptides and a ranked top 100.

## Submission

[Submitted on Kaggle](https://www.kaggle.com/competitions/amp-challenge/writeups/plum-generation-with-staged-antimicrobial-peptide) with both FASTA files attached.
The submitted sequences are also available here:

- [library.fasta](results/reference_run/library.fasta): 50,000 peptides.
- [top.fasta](results/reference_run/top.fasta): 100 candidates in rank order.
- [Submission write-up](SUBMISSION.md) and [abstract](ABSTRACT.md).

## Run

Use Linux x86_64 with `uv`, `git`, and `git-lfs` installed. The packaged pipeline
was tested on a Colab Tesla T4. Network access is required for model downloads.
CPU fallback is available, but a complete CPU run has not been timed.

```bash
git clone https://github.com/whippeddev/amp-challenge-2027.git
cd amp-challenge-2027
uv sync
uv run generate
```

Outputs are written to `generate/library.fasta` and `generate/top.fasta`.
Defaults are seed 42, 200,000 raw candidates, 50,000 library members, 2,000
candidates for final activity scoring, and 100 selected peptides.

Checkpoints are stored under `.amp-work/full-run1/`; downloaded models and
auxiliary environments are stored under `.amp-tools/`. Repeating the command
resumes matching checkpoints. For a fresh calculation, use:

```bash
uv run generate --work-dir .amp-work/independent-run
```

Three committed lock files cover the main, Deep-AMP, and HemoPI2 environments.
Auxiliary environments are installed automatically. Weight sources and pinned
revisions are listed in [model_sources.json](records/model_sources.json).

## Colab setup

Select a GPU runtime. In a fresh notebook, install the system tools:

```python
import subprocess
import sys

commands = [
    [sys.executable, "-m", "pip", "install", "-q", "uv"],
    ["apt-get", "update", "-qq"],
    ["apt-get", "install", "-y", "-qq", "git-lfs"],
]
for command in commands:
    subprocess.run(command, check=True)
```

Then clone and run the project in a separate cell:

```python
!git clone https://github.com/whippeddev/amp-challenge-2027.git
%cd amp-challenge-2027
!uv sync
!uv run generate
```

Save the generated files before ending the Colab session; its temporary disk is
cleared when the runtime is lost. The original notebook is in `notebooks/`.

## Method

1. Generate with PLUM and filter for sequence validity, duplicates, reference
   matches, and physicochemical properties.
2. Select the library using 50% APEX, 25% Deep-AMP Gram-negative, and 25%
   Deep-AMP Gram-positive percentile scores.
3. Screen candidates in library order with HemoPI2 and retain the first 2,000
   predicted non-hemolytic peptides for final scoring.
4. Rank by predicted activity across the combined tsAMP-CS/LLAMP panel, then
   apply reference and pairwise similarity limits to select 100 peptides.

See [METHODS.md](METHODS.md) for thresholds, counts, tie-breaking, and limitations.
No model was trained or fine-tuned in this pipeline. Activity and hemolysis are
predictions; the selected peptides have not been experimentally tested.

## Verification

A fresh packaged run on September 28, 2026 produced both FASTA files with hashes
matching the original run. The organizers' sequence-check functions passed on
the newly generated files.
Details are in [the validation record](records/reproduction_validation_2026-09-28.json).

Check the stored reference files:

```bash
uv run check-files
```

Check newly generated files:

```bash
uv run check-files --directory generate
```

The unchanged official validator is also included:

```bash
uv run python scripts/verify_submission.py https://github.com/whippeddev/amp-challenge-2027
```

It clones the repository, installs dependencies, generates and checks the files,
then runs generation again to compare outputs. The pipeline can reuse checkpoints;
a fresh work directory is needed for an independent calculation.

## Documentation and licenses

- [METHODS.md](METHODS.md): generation, selection, results, and limitations.
- [DATA_AND_MODELS.md](DATA_AND_MODELS.md): model and data sources.
- [THIRD_PARTY.md](THIRD_PARTY.md): third-party component licenses.
- [PACKAGING_CHANGES.md](PACKAGING_CHANGES.md): conversion from Colab to the CLI.
- `records/`: saved run and validation records.

Original integration code and documentation use the MIT license. Upstream code,
weights, and data retain their own terms. Historical run records are preserved;
the current methods document corrects their earlier equal-third scoring description.
