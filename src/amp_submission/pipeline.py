"""Executable pipeline adapted from the audited v14 notebook.

Run through the generate entry point. Model inference and selection equations
retain the completed-run implementation; runtime/path adaptations are recorded
in PACKAGING_CHANGES.md.
"""

# Stage from notebook cell 1
from pathlib import Path
import os

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

MODE = "full"  # test | full
RUN_NAME = "full-run1"
SAVE_TO_DRIVE = False
SEED = 42
RESET_FINAL_FILES = False
APEX_WEIGHT = 0.5  # APEX share of the cheap potency score; Deep-AMP gets the rest

# Historical project records are retained separately from submitter declarations.
# This notebook cannot establish actions taken outside its recorded computation.
# tsAMP-CS reconstruction, evaluated on the authors' released held-out test data.
# Retrieved from project records; not recomputed by this notebook.
TSAMP_HELDOUT_RESULTS = {
    "_source": "Released tsAMP-CS held-out test data; retrieved from project records",
    "_metrics": "mse = mean squared error on log10 MIC; spearman = rank correlation",
    "_detail_example": {
        "species": "Acinetobacter baumannii",
        "rows": 164,
        "mse": 0.2614,
        "pearson": 0.7541,
        "spearman": 0.7506,
    },
    "_relu_ablation": {
        "with_relu_mse": 0.2614,
        "without_relu_mse": 3.6024,
        "species": "Acinetobacter baumannii",
        "reading": "Removing the ReLU activations degrades MSE ~14x.",
    },
    "mse_by_species": {
        "Acinetobacter baumannii": 0.261,
        "Bacillus subtilis": 0.413,
        "Candida albicans": 0.289,
        "Enterococcus faecalis": 0.343,
        "Escherichia coli": 0.321,
        "Klebsiella pneumoniae": 0.244,
        "Pseudomonas aeruginosa": 0.242,
        "Salmonella enterica": 0.488,
        "Staphylococcus aureus": 0.364,
        "Staphylococcus epidermidis": 0.259,
    },
    "spearman_range": [0.502, 0.770],
}

HISTORICAL_MANUAL_INTERVENTION_RECORD = (
    "No manual editing, removal, injection or reordering of submitted sequences. Every "
    "sequence in library.fasta and top.fasta was produced and ordered by the code in this "
    "notebook. Separately, external published peptides (five OmegAMP peptides and the "
    "46-peptide AMP-Diffusion wet-lab set) were used as inputs to benchmarking work that "
    "evaluated candidate scoring models. Those peptides were human-selected for "
    "benchmarking, were never added to the submission candidate pool, and do not appear in "
    "either submitted file. A proposal to generate PLUM analogues seeded from an OmegAMP "
    "peptide was discussed and not executed; the PLUM run is de novo."
)
MANUAL_INTERVENTION_DECLARATION = None  # Set only to a statement confirmed by the submitter.

SEED_SELECTION_DECLARATION = (
    "Fixed default seed 42; each generation chunk uses 42 plus its chunk index so that a "
    "restart reproduces the same chunk output. No search over seeds and no selection of a "
    "preferred seed is recorded. The origin of the value 42 itself is not recorded."
)

MAX_RAW = 1000 if MODE == "test" else 200000
TARGET_FILTERED = None
GENERATION_CHUNK = 1000 if MODE == "test" else 5000
GENERATION_BATCH = 256

ELITE_TARGET = 200 if MODE == "test" else 2000
HEMO_INITIAL = 400 if MODE == "test" else 4000
HEMO_TOPUP = 100 if MODE == "test" else 500
HEMO_MAX_SCREEN = 1000 if MODE == "test" else 10000
FINAL_TOP_TARGET = 100
TSAMP_EMBED_BATCH = 16
LLAMP_BATCH = 64

if MODE not in {"test", "full"}:
    raise ValueError('MODE must be "test" or "full".')

RUN_ROOT = Path(RUN_OPTIONS["work_dir"]).resolve()
PROJECT_ROOT = Path(__file__).resolve().parents[2]

RUN_ROOT.mkdir(parents=True, exist_ok=True)

print(f"Mode: {MODE}")
print(f"Raw generation ceiling: {MAX_RAW:,}")
print(f"Elite target: {ELITE_TARGET:,}")
print(f"Results folder: {RUN_ROOT}")

if RESET_FINAL_FILES:
    for name in [
        "library.fasta",
        "top.fasta",
        "preview_library.fasta",
        "preview_top.fasta",
        "final_checks.json",
    ]:
        (RUN_ROOT / "final_files" / name).unlink(missing_ok=True)
    (RUN_ROOT.parent / f"{MODE}_results_backup.zip").unlink(missing_ok=True)
    print("Previous exported files cleared.")


# Stage from notebook cell 3
import subprocess
import sys
import shutil
import json
import hashlib
import re
import platform

PROJECT = RUN_ROOT
PREDICTIONS = PROJECT / "predictions"
REFERENCE_DIR = PROJECT / "reference"
TOOLS = Path(RUN_OPTIONS["tools_dir"]).resolve()

PLUM = TOOLS / "PLUM"
APEXGO = TOOLS / "APEXGo"
APEX = APEXGO / "optimization" / "apex_oracle"

DEEPAMP = TOOLS / "BattleAMP-deep-amp"
DEEPAMP_ENV = TOOLS / "deepamp-env"
DEEPAMP_PYTHON = DEEPAMP_ENV / ".venv" / "bin" / "python"

HEMO_ENV = TOOLS / "hemo-env"
HEMO_PYTHON = HEMO_ENV / ".venv" / "bin" / "python"

TSAMP = TOOLS / "tsAMP"
TSAMP_CS = TSAMP / "model" / "tsAMP-CS"
TSAMP_STRAINS = TSAMP / "data" / "tsAMP-CS" / "target_strains"

LLAMP = TOOLS / "LLAMP"
LLAMP_WEIGHT = LLAMP / "model_weight" / "LLAMP.pth"
LLAMP_GENOME = LLAMP / "data" / "Genomic_featrues" / "genome_features.pt"

ANTIBACTERIAL_FASTA = REFERENCE_DIR / "antibacterial.fasta"
elite_dir = PROJECT / "elite"

for folder in [PROJECT, PREDICTIONS, REFERENCE_DIR, TOOLS, elite_dir]:
    folder.mkdir(parents=True, exist_ok=True)


def run(command, cwd=None, env=None):
    subprocess.run(command, cwd=cwd, env=env, check=True)


def ensure_environment(name, destination):
    source = PROJECT_ROOT / "environments" / name
    destination.mkdir(parents=True, exist_ok=True)
    for filename in ["pyproject.toml", "uv.lock", ".python-version"]:
        shutil.copyfile(source / filename, destination / filename)
    run(["uv", "sync", "--locked", "--project", str(destination)], env={
        key: value for key, value in os.environ.items()
        if key not in {"VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT"}
    })


print("PLUM setup")
PLUM_COMMIT = "650fdae718f8e761deb2c96ff428766854d050a3"
if not PLUM.exists():
    run(["git", "clone", "https://github.com/priyamayur/PLUM.git", str(PLUM)])
run(["git", "fetch", "origin", PLUM_COMMIT, "--depth", "1"], cwd=PLUM)
run(["git", "checkout", "--detach", PLUM_COMMIT], cwd=PLUM)
PLUM_CHECKPOINT = PLUM / "models" / "generative_model" / "PLUM_new_analysis_renew_part4_v2_004.pth"
if not PLUM_CHECKPOINT.exists():
    raise FileNotFoundError(f"PLUM checkpoint missing: {PLUM_CHECKPOINT}")
if hashlib.sha256(PLUM_CHECKPOINT.read_bytes()).hexdigest() != "8c5607765cbb448c7e7ccdd40ef6afb7f6d87781f571ffa8868eba651d532f43":
    raise RuntimeError("PLUM checkpoint differs from the completed run.")
if hashlib.sha256((PLUM / "data" / "train.csv").read_bytes()).hexdigest() != "e1595f002d386e0308d93111e811b7da1747caf511fdc449172ddc7fbc4316fd":
    raise RuntimeError("PLUM training reference differs from the completed run.")
print(f"PLUM checkpoint: {PLUM_CHECKPOINT.stat().st_size / 1024 ** 2:.2f} MB")

print("APEX setup")
APEX_COMMIT = "10a355a4220e6f8f432d62b267317b5b8b337dc8"
if not APEXGO.exists():
    run(
        [
            "git",
            "clone",
            "--filter=blob:none",
            "--sparse",
            "https://github.com/Yimeng-Zeng/APEXGo.git",
            str(APEXGO),
        ]
    )
    run(["git", "sparse-checkout", "set", "optimization/apex_oracle"], cwd=APEXGO)
run(["git", "fetch", "origin", APEX_COMMIT, "--depth", "1"], cwd=APEXGO)
run(["git", "checkout", "--detach", APEX_COMMIT], cwd=APEXGO)
apex_models = list((APEX / "APEX_pathogen_models").glob("APEX_*"))
if len(apex_models) != 8:
    raise RuntimeError(f"Expected 8 APEX models, found {len(apex_models)}.")
print(f"APEX models found: {len(apex_models)}")

print("Deep-AMP setup")
DEEPAMP_COMMIT = "0a31ad796732b5e5874c3f92e771057e887f58a9"
if not DEEPAMP.exists():
    run(["git", "clone", "https://github.com/szczurek-lab/BattleAMP-deep-amp.git", str(DEEPAMP)])
run(["git", "fetch", "origin", DEEPAMP_COMMIT, "--depth", "1"], cwd=DEEPAMP)
run(["git", "checkout", "--detach", DEEPAMP_COMMIT], cwd=DEEPAMP)
deepamp_pin = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=DEEPAMP, text=True).strip()
if deepamp_pin != DEEPAMP_COMMIT:
    raise RuntimeError("Deep-AMP checkout did not match its fixed revision.")
deepamp_pin_file = PROJECT / "deepamp_revision.json"
deepamp_pin_file.write_text(json.dumps({"commit": DEEPAMP_COMMIT}))
ensure_environment("deepamp", DEEPAMP_ENV)
DEEPAMP_MODELS = DEEPAMP / "saved_models" / "paper" / "regressor"
for model_name in ["CNN_gr_neg", "CNN_gr_pos"]:
    assert (
        DEEPAMP_MODELS / model_name / "saved_model.pb"
    ).exists(), f"Missing Deep-AMP model: {model_name}"
print("Deep-AMP CNN Gram+ and Gram- ready")

print("Reference verification")
REFERENCE_COMMIT = "5c8a5d8e2551c8cf572d3d3bfcfe7633b109d91e"
REFERENCE_SHA256 = "cbbeac64ba95746d87961e8ad9dd0849ae8058d15a300b2e7f6990730ca521e9"
REFERENCE_URL = (
    "https://raw.githubusercontent.com/szczurek-lab/amp-challenge-2027/"
    + REFERENCE_COMMIT
    + "/data/antibacterial.fasta"
)


def reference_matches(path):
    return path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == REFERENCE_SHA256


if not reference_matches(ANTIBACTERIAL_FASTA):
    temporary_reference = ANTIBACTERIAL_FASTA.with_suffix(".download")
    shutil.copyfile(PROJECT_ROOT / "data" / "antibacterial.fasta", temporary_reference)
    if not reference_matches(temporary_reference):
        temporary_reference.unlink(missing_ok=True)
        raise RuntimeError("Official reference download failed its checksum check.")
    temporary_reference.replace(ANTIBACTERIAL_FASTA)
print("Official reference verified by SHA-256.")

print("HemoPI2 setup")
ensure_environment("hemopi2", HEMO_ENV)

print("tsAMP-CS setup")
TSAMP_COMMIT = "82c722090b10878edb0b9f45033e1806a659f2b7"
if shutil.which("git-lfs") is None:
    raise RuntimeError("git-lfs is required. Install it before running the pipeline.")
if not TSAMP.exists():
    lfs_env = dict(os.environ)
    lfs_env["GIT_LFS_SKIP_SMUDGE"] = "1"
    run(["git", "clone", "https://github.com/YangLab-BUPT/tsAMP.git", str(TSAMP)], env=lfs_env)
run(["git", "fetch", "origin", TSAMP_COMMIT, "--depth", "1"], cwd=TSAMP)
run(["git", "checkout", "--detach", TSAMP_COMMIT], cwd=TSAMP)
run(
    [
        "git",
        "lfs",
        "pull",
        "--include=model/tsAMP-CS/strain/**,data/tsAMP-CS/target_strains/**",
    ],
    cwd=TSAMP,
)
tsamp_models = sorted((TSAMP_CS / "strain").glob("*.pt"))
if len(tsamp_models) != 10:
    raise RuntimeError(f"Expected 10 tsAMP-CS checkpoints, found {len(tsamp_models)}.")
if not list(TSAMP_STRAINS.glob("*.pt")):
    raise RuntimeError("No tsAMP-CS strain embeddings found.")
tsamp_pin_file = PROJECT / "tsamp_revision.json"
tsamp_pin_file.write_text(json.dumps({"commit": TSAMP_COMMIT, "architecture": "2560-128-64-1"}))

print(f"tsAMP-CS: {len(tsamp_models)} species checkpoints ready")

print("LLAMP setup")
LLAMP_COMMIT = "bb48daaa94b947edac46e498dec741911cf98edc"
LLAMP_HF_MODEL = "Daehun/peptide_tuned_ESM-2"
LLAMP_HF_REVISION = "16b0dddc26541a33740a1bf084a7030b373622d5"
LLAMP_WEIGHT_ID = "1hmfL7uRZsHo4pn0o0nqaqPcntxGJIhE7"
LLAMP_WEIGHT_SOURCE = (
    "https://drive.google.com/file/d/"
    + LLAMP_WEIGHT_ID
    + "/view?usp=sharing"
)

if not LLAMP.exists():
    run(["git", "clone", "https://github.com/GIST-CSBL/LLAMP.git", str(LLAMP)])
run(["git", "fetch", "origin", LLAMP_COMMIT, "--depth", "1"], cwd=LLAMP)
run(["git", "checkout", "--detach", LLAMP_COMMIT], cwd=LLAMP)

LLAMP_WEIGHT.parent.mkdir(parents=True, exist_ok=True)
if not LLAMP_WEIGHT.exists():
    run(["gdown", "--id", LLAMP_WEIGHT_ID, "-O", str(LLAMP_WEIGHT)])

if not LLAMP_GENOME.exists():
    raise FileNotFoundError(f"LLAMP genome features missing: {LLAMP_GENOME}")
if LLAMP_WEIGHT.stat().st_size < 1_000_000:
    raise RuntimeError("LLAMP weight download is unexpectedly small.")

llamp_weight_sha256 = hashlib.sha256(LLAMP_WEIGHT.read_bytes()).hexdigest()
if llamp_weight_sha256 != "be331f32d8df620a955dfd86647cedd81f91fd315e5a8cefbc1cdd66c43f7f6e":
    raise RuntimeError("LLAMP weights differ from the completed run.")
from huggingface_hub import snapshot_download
LLAMP_HF_RESOLVED = snapshot_download(
    repo_id=LLAMP_HF_MODEL, revision=LLAMP_HF_REVISION,
)
llamp_pin_file = PROJECT / "llamp_revision.json"
llamp_pin_file.write_text(
    json.dumps(
        {
            "commit": LLAMP_COMMIT,
            "weight_source": LLAMP_WEIGHT_SOURCE,
            "weight_sha256": llamp_weight_sha256,
            "peptide_model": LLAMP_HF_MODEL,
            "peptide_model_revision": LLAMP_HF_REVISION,
            "output": "log10 MIC in uM",
        },
        indent=2,
    )
)
print(f"LLAMP weight: {LLAMP_WEIGHT.stat().st_size / 1024 ** 2:.2f} MB")
print(f"LLAMP SHA-256: {llamp_weight_sha256[:16]}...")

import numpy as np
import pandas as pd
import torch
def display(value):
    print(value.to_string(index=False) if hasattr(value, "to_string") else value)

print("Setup complete.")
print(f"Project folder: {PROJECT}")


# Stage from notebook cell 5
from itertools import groupby

LIBRARY_ALPHABET = "ACDEFGHIKLMNPQRSTVWY"


def library_read_fasta(path):
    sequences, parts = ([], None)
    for raw in Path(path).read_text().splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(">"):
            if parts is not None:
                sequences.append("".join(parts))
            parts = []
        else:
            if parts is None:
                raise ValueError(f"Missing FASTA header in {Path(path).name}.")
            parts.append(line)
    if parts is not None:
        sequences.append("".join(parts))
    if any((not sequence for sequence in sequences)):
        raise ValueError(f"Empty FASTA record in {Path(path).name}.")
    return sequences


def library_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def library_validate_sequences(sequences, label):
    if not sequences:
        raise ValueError(f"{label}: no peptides found.")
    if len(sequences) != len(set(sequences)):
        raise ValueError(f"{label}: duplicate peptides found.")
    alphabet = set(LIBRARY_ALPHABET)
    if any((not 8 <= len(s) <= 50 or not set(s) <= alphabet for s in sequences)):
        raise ValueError(
            f"{label}: peptides must use the 20 standard letters and be 8–50 letters long."
        )


def library_longest_hydrophobic_run(sequence):
    hydrophobic = set("AVILMFWY")
    longest = current = 0
    for aa in sequence:
        current = current + 1 if aa in hydrophobic else 0
        longest = max(longest, current)
    return longest



def library_build_ranking(candidates, potency, references):
    library_validate_sequences(candidates, "Filtered pool")
    if set(candidates) & set(references):
        raise ValueError("The filtered pool still contains exact reference matches.")
    required = {"Sequence", "Cheap potency score"}
    if not required <= set(potency.columns):
        raise ValueError("Missing potency columns.")
    if potency["Sequence"].duplicated().any() or set(potency["Sequence"]) != set(candidates):
        raise ValueError("Potency results do not match the filtered pool.")
    table = potency[["Sequence", "Cheap potency score"]].copy()
    table = table.sort_values("Sequence", kind="stable").reset_index(drop=True)
    values = table["Cheap potency score"].to_numpy(dtype=float)
    if not np.isfinite(values).all() or ((values < 0) | (values > 1)).any():
        raise ValueError("Cheap potency scores must be finite values between 0 and 1.")
    table["Length"] = table["Sequence"].str.len()
    table["Longest hydrophobic stretch"] = table["Sequence"].map(library_longest_hydrophobic_run)
    table["Longest repeated letter"] = table["Sequence"].map(
        lambda s: max((sum((1 for _ in chunk)) for _, chunk in groupby(s)))
    )
    table["Library selection score"] = table["Cheap potency score"]
    return table.sort_values(["Cheap potency score", "Sequence"], kind="stable").reset_index(
        drop=True
    )



def library_validate_top100(sequences, pool, references):
    from Levenshtein import ratio

    library_validate_sequences(sequences, "Top 100")
    if len(sequences) != 100 or not set(sequences) <= set(pool):
        raise ValueError("Top 100 must contain exactly 100 members of the scored pool.")
    for number, sequence in enumerate(sequences, 1):
        for reference in references:
            if 2 * min(len(sequence), len(reference)) / (len(sequence) + len(reference)) <= 0.8:
                continue
            if ratio(sequence, reference) > 0.8:
                raise ValueError(f"Top-100 peptide {number} exceeds 80% reference identity.")


def library_write_fasta(sequences, path, prefix):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("".join((f">{prefix}_{i:05d}\n{s}\n" for i, s in enumerate(sequences, 1))))
    temporary.replace(path)


import time
import zipfile
from Levenshtein import ratio


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2))
    temporary.replace(path)


def stage_signature(sources=(), settings=None):
    return {"files": {str(p): library_hash(p) for p in sources}, "settings": settings or {}}


# Reuse only when input and output hashes match.
def stage_ready(name, sources, outputs, settings=None):
    record = PROJECT / "checkpoints" / f"{name}.json"
    try:
        saved = json.loads(record.read_text())
        return saved["inputs"] == stage_signature(sources, settings) and all(
            (p.exists() and library_hash(p) == saved["outputs"][str(p)] for p in outputs)
        )
    except (OSError, ValueError, KeyError):
        return False


def stage_done(name, sources, outputs, settings=None):
    save_json(
        PROJECT / "checkpoints" / f"{name}.json",
        {
            "inputs": stage_signature(sources, settings),
            "outputs": {str(p): library_hash(p) for p in outputs},
        },
    )


def validate_prediction_rows(frame, expected, numeric=(), labels=None):
    if "Sequence" not in frame or frame["Sequence"].duplicated().any():
        raise ValueError("Prediction output has missing sequence names or duplicate rows.")
    if set(frame["Sequence"]) != set(expected):
        raise ValueError("Prediction output does not match the input peptides.")
    if numeric:
        values = frame[list(numeric)].to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError("Prediction output contains missing or invalid numbers.")
    if labels and (not frame["Prediction"].isin(labels).all()):
        raise ValueError("Unexpected HemoPI2 label.")
    return frame.set_index("Sequence").loc[list(expected)].reset_index()


def choose_shortlist(table, size=5000):
    ordered = table.sort_values(["Library selection score", "Sequence"], kind="stable")
    size = min(size, len(ordered))
    result = ordered.head(size).copy()
    result["Shortlist reason"] = (
        "All candidates" if size == len(ordered) else "Rank"
    )
    if len(result) != size or result["Sequence"].nunique() != size:
        raise RuntimeError("Shortlist count mismatch.")
    return result.reset_index(drop=True)


# Upper bound on Levenshtein.ratio from lengths alone; skips most comparisons.
def too_similar(sequence, reference, cutoff=0.8):
    bound = 2 * min(len(sequence), len(reference)) / (len(sequence) + len(reference))
    return bound > cutoff and ratio(sequence, reference) > cutoff


def finalize_outputs(ranking, top, references, output_dir, mode):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    library_validate_sequences(ranking["Sequence"].tolist(), "Ranked pool")
    if set(ranking["Sequence"]) & set(references):
        raise ValueError("Exact reference matches remain in the pool.")
    if mode == "full":
        if len(ranking) < 50000:
            raise ValueError("Not enough peptides for 50,000. No final files were written.")
        library_validate_top100(top, ranking["Sequence"], references)
        if any((too_similar(a, b) for i, a in enumerate(top) for b in top[:i])):
            raise ValueError("Top-100 internal identity exceeds 80%.")
    elif mode != "test":
        raise ValueError("Mode must be test or full.")
    if len(top) > 100 or len(top) != len(set(top)) or (not set(top) <= set(ranking["Sequence"])):
        raise ValueError("Invalid Top-100 list.")

    target = 50000 if mode == "full" else min(50000, len(ranking))
    selected = ranking.sort_values(["Cheap potency score", "Sequence"], kind="stable").head(target).copy()
    if mode == "full" and set(top) - set(selected["Sequence"]):
        raise ValueError("Top-100 contains a peptide outside the selected 50,000 library.")
    selected = selected.reset_index(drop=True)
    prefix = "" if mode == "full" else "preview_"
    library_write_fasta(selected["Sequence"], output_dir / f"{prefix}library.fasta", "library")
    library_write_fasta(top, output_dir / f"{prefix}top.fasta", "top")
    selected.to_csv(output_dir / "selected_library.csv", index=False)
    checks = {
        "mode": mode,
        "library_count": len(selected),
        "top_count": len(top),
        "unique_library": selected["Sequence"].nunique() == len(selected),
        "top_is_in_library": set(top) <= set(selected["Sequence"]),
        "library_selection": "Top 50,000 by Cheap potency score after complete APEX + Deep-AMP screening; Sequence ascending resolves exact ties.",
        "reference_identity_limit": 0.8,
        "internal_top_identity_limit": 0.8,
        "chemistry": "linear peptides, free termini; no terminal modifications specified",
        "official_repository_validator_run": False,
        "status": (
            "Sequence files ready; repository submission checks remain"
            if mode == "full"
            else "TEST ONLY — not submission files"
        ),
    }
    save_json(output_dir / "final_checks.json", checks)
    return checks

def elite_safety_eligibility(table, labels):
    checked = validate_prediction_rows(
        labels, table["Sequence"].tolist(), labels=["Hemolytic", "Non-Hemolytic"]
    )
    joined = table[["Sequence"]].merge(
        checked[["Sequence", "Prediction"]], on="Sequence", validate="one_to_one"
    )
    joined["Eligibility"] = np.where(
        joined["Prediction"].eq("Non-Hemolytic"),
        "Eligible for stronger scoring",
        "Predicted hemolytic",
    )
    return joined[["Sequence", "Eligibility"]]


def prepare_elite_panel(ranking, eligibility, target=2000):
    if eligibility["Sequence"].duplicated().any():
        raise ValueError("Duplicate elite eligibility records.")
    eligible = set(
        eligibility.loc[eligibility["Eligibility"] == "Eligible for stronger scoring", "Sequence"]
    )
    if not eligible <= set(ranking["Sequence"]):
        raise ValueError("Elite eligibility contains unknown sequences.")
    panel = choose_shortlist(ranking[ranking["Sequence"].isin(eligible)], size=target)
    panel = panel.rename(columns={"Shortlist reason": "Elite selection reason"})
    panel["Candidate ID"] = [f"elite_{i:05d}" for i in range(1, len(panel) + 1)]
    return panel

# Official 20-strain challenge panel.
CHALLENGE_STRAINS = [
    "Acinetobacter baumannii ATCC 19606",
    "Acinetobacter baumannii ATCC BAA-1605",
    "Enterobacter cloacae ATCC 13047",
    "Escherichia coli ATCC 11775",
    "Escherichia coli AIC221",
    "Escherichia coli AIC222",
    "Escherichia coli ATCC BAA-3170",
    "Escherichia coli K-12 BW25113",
    "Klebsiella pneumoniae ATCC 13883",
    "Klebsiella pneumoniae ATCC BAA-2342",
    "Pseudomonas aeruginosa PAO1",
    "Pseudomonas aeruginosa PA14",
    "Pseudomonas aeruginosa ATCC BAA-3197",
    "Salmonella enterica ATCC 9150",
    "Salmonella enterica Typhimurium ATCC 700720",
    "Bacillus subtilis ATCC 23857",
    "Staphylococcus aureus ATCC 12600",
    "Staphylococcus aureus ATCC BAA-1556",
    "Enterococcus faecalis ATCC 700802",
    "Enterococcus faecium ATCC 700221",
]


# tsAMP-CS covers the 11 strains with both a species checkpoint and a released
# exact-strain embedding. LLAMP covers the remaining 9 at species level.
TSAMP_PRIMARY_TARGETS = [
    "Acinetobacter baumannii ATCC 19606",
    "Acinetobacter baumannii ATCC BAA-1605",
    "Escherichia coli ATCC 11775",
    "Escherichia coli K-12 BW25113",
    "Klebsiella pneumoniae ATCC 13883",
    "Pseudomonas aeruginosa PAO1",
    "Pseudomonas aeruginosa PA14",
    "Bacillus subtilis ATCC 23857",
    "Staphylococcus aureus ATCC 12600",
    "Staphylococcus aureus ATCC BAA-1556",
    "Enterococcus faecalis ATCC 700802",
]

LLAMP_FALLBACK_TARGETS = {
    "Enterobacter cloacae ATCC 13047": "Enterobacter cloacae",
    "Escherichia coli AIC221": "Escherichia coli",
    "Escherichia coli AIC222": "Escherichia coli",
    "Escherichia coli ATCC BAA-3170": "Escherichia coli",
    "Klebsiella pneumoniae ATCC BAA-2342": "Klebsiella pneumoniae",
    "Pseudomonas aeruginosa ATCC BAA-3197": "Pseudomonas aeruginosa",
    "Salmonella enterica ATCC 9150": "Salmonella enterica",
    "Salmonella enterica Typhimurium ATCC 700720": "Salmonella enterica",
    "Enterococcus faecium ATCC 700221": "Enterococcus faecium",
}

if set(TSAMP_PRIMARY_TARGETS) & set(LLAMP_FALLBACK_TARGETS):
    raise ValueError("tsAMP-CS and LLAMP target sets overlap.")
if set(TSAMP_PRIMARY_TARGETS) | set(LLAMP_FALLBACK_TARGETS) != set(CHALLENGE_STRAINS):
    raise ValueError("tsAMP-CS + LLAMP target sets must cover the full 20-strain panel.")

TSAMP_ALIASES = {
    "Escherichia coli AIC221": ["Escherichia coli AIG221"],
    "Escherichia coli AIC222": ["Escherichia coli AIG222"],
    "Escherichia coli K-12 BW25113": [
        "Escherichia coli K12 BW25113",
        "Escherichia coli BW25113",
    ],
    "Pseudomonas aeruginosa PAO1": ["Pseudomonas aeruginosa PA01"],
    "Salmonella enterica Typhimurium ATCC 700720": [
        "Salmonella Typhimurium ATCC 700720",
        "Salmonella enterica serovar Typhimurium ATCC 700720",
    ],
}


def normalize_target_name(value):
    return "".join(ch.lower() for ch in str(value) if ch.isalnum())


def resolve_tsamp_targets(strain_dir, model_dir):
    available = {normalize_target_name(p.stem): p for p in Path(strain_dir).glob("*.pt")}
    model_names = {p.stem for p in Path(model_dir).glob("*.pt")}
    rows = []
    for target in CHALLENGE_STRAINS:
        species = " ".join(target.split()[:2])
        model_file = Path(model_dir) / f"{species}.pt"
        candidates = [target] + TSAMP_ALIASES.get(target, [])
        matched = None
        for candidate in candidates:
            matched = available.get(normalize_target_name(candidate))
            if matched is not None:
                break
        rows.append(
            {
                "Challenge strain": target,
                "Species checkpoint": species if species in model_names else None,
                "Strain embedding": matched.name if matched is not None else None,
                "Usable": (species in model_names) and (matched is not None),
            }
        )
    return pd.DataFrame(rows)


class TSAMPCSRecovered(torch.nn.Module):
    # Architecture inferred from the released checkpoint tensor shapes, then evaluated on
    # the authors' released held-out test data for all 10 species (see
    # TSAMP_HELDOUT_RESULTS). Removing these ReLUs degrades A. baumannii MSE from 0.2614
    # to 3.6024, which is why they are here. Exact agreement with the authors' own
    # predictions is still not established.
    def __init__(self):
        super().__init__()
        self.fc1 = torch.nn.Linear(2560, 128)
        self.fc3 = torch.nn.Linear(128, 64)
        self.fc4 = torch.nn.Linear(64, 1)

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc3(x))
        return self.fc4(x)


def validate_tsamp_checkpoint(state):
    expected = {
        "fc1.weight": (128, 2560),
        "fc1.bias": (128,),
        "fc3.weight": (64, 128),
        "fc3.bias": (64,),
        "fc4.weight": (1, 64),
        "fc4.bias": (1,),
    }
    shapes = {name: tuple(tensor.shape) for name, tensor in state.items()}
    if shapes != expected:
        raise ValueError(f"Unexpected tsAMP-CS checkpoint architecture: {shapes}")


# Loaded once per session; reloading per batch dominated the embedding runtime.
_ESM1V_CACHE = {}


def tsamp_load_esm1v():
    if "model" not in _ESM1V_CACHE:
        import esm

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model, alphabet = esm.pretrained.esm1v_t33_650M_UR90S_1()
        _ESM1V_CACHE["model"] = model.eval().to(device)
        _ESM1V_CACHE["converter"] = alphabet.get_batch_converter()
        _ESM1V_CACHE["device"] = device
        print(f"ESM-1v loaded once on {device}.")
    return _ESM1V_CACHE["model"], _ESM1V_CACHE["converter"], _ESM1V_CACHE["device"]


def tsamp_release_esm1v():
    if "model" in _ESM1V_CACHE:
        was_cuda = _ESM1V_CACHE["device"].type == "cuda"
        _ESM1V_CACHE.clear()
        if was_cuda:
            torch.cuda.empty_cache()
        print("ESM-1v released.")


def tsamp_extract_esm1v(sequences, batch_size=16):
    model, converter, device = tsamp_load_esm1v()
    embeddings = []

    with torch.no_grad():
        for start in range(0, len(sequences), batch_size):
            subset = sequences[start : start + batch_size]
            labels = [f"elite_{start + i:05d}" for i in range(len(subset))]
            _, _, tokens = converter(list(zip(labels, subset)))
            tokens = tokens.to(device)
            out = model(tokens, repr_layers=[33], return_contacts=False)
            reps = out["representations"][33]
            for i, sequence in enumerate(subset):
                embeddings.append(reps[i, 1 : len(sequence) + 1].mean(0).cpu())
    return torch.stack(embeddings).numpy().astype(np.float32)


# Passes /20, then tsAMP-CS passes /11, then mean predicted log10 MIC. The third
# key is continuous, so large pass-count ties do not resolve on sequence order.
def rank_elite_by_coverage(tsamp_frame, llamp_frame, sequences, cutoff_uM):
    sequences = list(sequences)
    if tsamp_frame["Sequence"].tolist() != sequences:
        raise ValueError("tsAMP-CS predictions are not aligned with the elite panel.")
    if llamp_frame["Sequence"].tolist() != sequences:
        raise ValueError("LLAMP predictions are not aligned with the elite panel.")

    def mic_matrix(frame, expected, label):
        columns = [c for c in frame.columns if c.startswith("MIC uM | ")]
        if len(columns) != expected:
            raise ValueError(f"{label}: expected {expected} strain columns, found {len(columns)}.")
        matrix = frame.set_index("Sequence")[columns]
        values = matrix.to_numpy(dtype=float)
        if not np.isfinite(values).all() or (values <= 0).any():
            raise ValueError(f"{label}: predicted MIC values must be finite and positive.")
        return matrix

    tsamp_mic = mic_matrix(tsamp_frame, len(TSAMP_PRIMARY_TARGETS), "tsAMP-CS")
    llamp_mic = mic_matrix(llamp_frame, len(LLAMP_FALLBACK_TARGETS), "LLAMP")
    combined = pd.concat([tsamp_mic, llamp_mic], axis=1)
    if combined.shape[1] != len(CHALLENGE_STRAINS):
        raise ValueError(f"Expected {len(CHALLENGE_STRAINS)} strain columns, found {combined.shape[1]}.")

    tsamp_passes = (tsamp_mic <= cutoff_uM).sum(axis=1)
    llamp_passes = (llamp_mic <= cutoff_uM).sum(axis=1)
    scores = pd.DataFrame(
        {
            "Sequence": combined.index.to_numpy(),
            "Predicted passes /20": (tsamp_passes + llamp_passes).to_numpy(),
            "tsAMP-CS passes /11": tsamp_passes.to_numpy(),
            "LLAMP passes /9": llamp_passes.to_numpy(),
            "Mean predicted log10 MIC": np.log10(combined.to_numpy(dtype=float)).mean(axis=1),
        }
    )
    scores = scores.sort_values(
        [
            "Predicted passes /20",
            "tsAMP-CS passes /11",
            "Mean predicted log10 MIC",
            "Sequence",
        ],
        ascending=[False, False, True, True],
        kind="stable",
    ).reset_index(drop=True)
    scores["Coverage rank"] = np.arange(1, len(scores) + 1)
    return scores, tsamp_mic, llamp_mic


def choose_final_top(table, references, count=100, identity_limit=0.8, strict=True):
    ordered = table.sort_values(["Elite model score", "Sequence"], kind="stable")
    by_length = {}
    for reference in set(references):
        by_length.setdefault(len(reference), []).append(reference)

    def reference_clear(sequence):
        for length, refs in by_length.items():
            bound = 2 * min(len(sequence), length) / (len(sequence) + length)
            if bound > identity_limit and any(
                too_similar(sequence, reference, identity_limit) for reference in refs
            ):
                return False
        return True

    picked = []
    for sequence in ordered["Sequence"]:
        if not reference_clear(sequence):
            continue
        if all(not too_similar(sequence, previous, identity_limit) for previous in picked):
            picked.append(sequence)
        if len(picked) == count:
            break
    if strict and len(picked) != count:
        raise RuntimeError(
            f"Could select only {len(picked)}/{count} Top peptides under the identity limits."
        )
    return picked


# Stage from notebook cell 6
checkpoint_dir = PROJECT / "checkpoints"
completed = sorted(p.stem for p in checkpoint_dir.glob("*.json")) if checkpoint_dir.exists() else []
print(f"Drive checkpoint directory: {checkpoint_dir}")
print(f"Completed stage/model checkpoints found: {len(completed)}")
if completed:
    print(" | ".join(completed[:30]))
print("The same work directory can resume from these checkpoints.")

# Stage from notebook cell 8
import random
import torch.nn.functional as F

MIN_LENGTH = 8
MAX_LENGTH = 35
CHECKPOINT = PLUM / "models" / "generative_model" / "PLUM_new_analysis_renew_part4_v2_004.pth"
sys.path.insert(0, str(PLUM))
from training_generative_model.generative_model import (
    PeptideCSVAE_LSTM,
    AA_TO_IDX,
    IDX_TO_AA,
    PAD_TOKEN,
    START_TOKEN,
    STOP_TOKEN,
    length_to_bin,
    NUM_LENGTH_BINS,
)

torch.use_deterministic_algorithms(True)
torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device: {DEVICE}")
checkpoint = torch.load(CHECKPOINT, map_location=DEVICE, weights_only=False)
cfg = checkpoint["model_config"]
model = PeptideCSVAE_LSTM(
    seq_len=cfg["seq_len"],
    z_dim=cfg["z_dim"],
    w_dim=cfg["w_dim"],
    v_dim=cfg["v_dim"],
    hidden_dim=cfg["hidden_dim"],
    cond_dim=cfg["cond_dim"],
).to(DEVICE)
model.load_state_dict(checkpoint["model_state_dict"])
model.eval()
for name, tensor in model.state_dict().items():
    if not torch.isfinite(tensor).all():
        raise ValueError(f"Non-finite PLUM weights found: {name}")
print("PLUM checkpoint OK.")
train_df = pd.read_csv(PLUM / "data" / "train.csv")
training_sequences = set(train_df["sequence"].astype(str))
CANONICAL = set("ACDEFGHIKLMNPQRSTVWY")


@torch.no_grad()
def generate_batch(target_length, batch_size):
    length_bin = int(np.argmax(length_to_bin(target_length)))
    y_func = torch.ones((batch_size, 1), dtype=torch.float32, device=DEVICE)
    y_len = F.one_hot(
        torch.full((batch_size,), length_bin, dtype=torch.long, device=DEVICE),
        num_classes=NUM_LENGTH_BINS,
    ).float()
    z = torch.randn(batch_size, model.z_dim, device=DEVICE)
    mu_w, logvar_w = model.p_w_prior(y_func)
    w = model.reparameterize(mu_w, logvar_w)
    mu_v, logvar_v = model.p_v_prior(y_len)
    v = model.reparameterize(mu_v, logvar_v)
    h = torch.zeros(model.lstm_layers, batch_size, model.hidden_dim, device=DEVICE)
    c = torch.zeros(model.lstm_layers, batch_size, model.hidden_dim, device=DEVICE)
    input_idx = torch.full((batch_size,), AA_TO_IDX[START_TOKEN], dtype=torch.long, device=DEVICE)
    sequences = [""] * batch_size
    for _ in range(target_length):
        input_t = F.one_hot(input_idx, num_classes=model.input_dim).float().unsqueeze(1)
        decoder_input = torch.cat([input_t, z.unsqueeze(1), w.unsqueeze(1), v.unsqueeze(1)], dim=2)
        out, (h, c) = model.decoder_lstm(decoder_input, (h, c))
        logits = model.out_x(out).squeeze(1)
        probs = F.softmax(logits, dim=1)
        input_idx = torch.multinomial(probs, 1).squeeze(1)
        sampled = input_idx.cpu().numpy()
        for i, token in enumerate(sampled):
            aa = IDX_TO_AA[int(token)]
            if aa in (PAD_TOKEN, START_TOKEN, STOP_TOKEN):
                continue
            sequences[i] += aa
    return sequences


from Bio.SeqUtils.ProtParam import ProteinAnalysis
from seqme.models import Charge, Hydrophobicity

reference_set = set(library_read_fasta(ANTIBACTERIAL_FASTA))
if not reference_set:
    raise ValueError("Reference file is empty.")
charge_model = Charge(ph=7.0)
hydrophobicity_model = Hydrophobicity(scale="eisenberg")
chunk_dir = PROJECT / "generation_chunks"
chunk_dir.mkdir(exist_ok=True)
generation_settings = {
    "version": 1,
    "seed": SEED,
    "mode": MODE,
    "raw_limit": MAX_RAW,
    "chunk_size": GENERATION_CHUNK,
    "batch_size": GENERATION_BATCH,
    "target_filtered": TARGET_FILTERED,
    "length": [8, 35],
    "instability_max": 40.0,
    "charge": [2.0, 10.0],
    "eisenberg": [-0.5, 0.8],
    "checkpoint": library_hash(CHECKPOINT),
    "reference": library_hash(ANTIBACTERIAL_FASTA),
    "training_data": library_hash(PLUM / "data" / "train.csv"),
}
contract = chunk_dir / "settings.json"
if contract.exists() and json.loads(contract.read_text()) != generation_settings:
    raise ValueError("RUN_NAME conflicts with saved generation settings.")
save_json(contract, generation_settings)
generation_fasta = PROJECT / "physicochemical_passed.fasta"
generation_summary_file = PROJECT / "generation_summary.json"
generation_sources = [CHECKPOINT, ANTIBACTERIAL_FASTA, PLUM / "data" / "train.csv"]
generation_outputs = [generation_fasta, generation_summary_file]
start_time = time.time()

if stage_ready("generation", generation_sources, generation_outputs, generation_settings):
    kept = library_read_fasta(generation_fasta)
    generation_summary = json.loads(generation_summary_file.read_text())
    total_raw = int(generation_summary["raw_generated"])
    print(f"Generation: cached ({len(kept):,} unique filter-passing peptides)")
else:
    kept, seen = ([], set())
    total_raw = 0
    for chunk_number, offset in enumerate(range(0, MAX_RAW, GENERATION_CHUNK)):
        if TARGET_FILTERED is not None and len(kept) >= TARGET_FILTERED:
            break
        count = min(GENERATION_CHUNK, MAX_RAW - offset)
        cache = chunk_dir / f"chunk_{chunk_number:04d}.json"
        if cache.exists():
            saved_chunk = json.loads(cache.read_text())
            passed = saved_chunk["passed"]
        else:
            # Per-chunk seed: chunk output does not depend on restart order.
            block_seed = SEED + chunk_number
            random.seed(block_seed)
            np.random.seed(block_seed)
            torch.manual_seed(block_seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(block_seed)
            rng = np.random.default_rng(block_seed)
            lengths = rng.integers(MIN_LENGTH, MAX_LENGTH + 1, size=count)
            raw = []
            for length in sorted(np.unique(lengths)):
                number = int(np.sum(lengths == length))
                for batch_start in range(0, number, GENERATION_BATCH):
                    raw.extend(generate_batch(int(length), min(GENERATION_BATCH, number - batch_start)))
            clean = list(
                dict.fromkeys(
                    (
                        s
                        for s in raw
                        if MIN_LENGTH <= len(s) <= MAX_LENGTH
                        and set(s) <= CANONICAL
                        and (s not in training_sequences)
                        and (s not in reference_set)
                    )
                )
            )
            stable = [s for s in clean if ProteinAnalysis(s).instability_index() <= 40.0]
            charges = np.asarray(charge_model(stable), dtype=float) if stable else np.array([])
            if charges.shape != (len(stable),) or not np.isfinite(charges).all():
                raise ValueError("Invalid charge values.")
            charged = [s for s, value in zip(stable, charges) if 2.0 <= value <= 10.0]
            hydro = np.asarray(hydrophobicity_model(charged), dtype=float) if charged else np.array([])
            if hydro.shape != (len(charged),) or not np.isfinite(hydro).all():
                raise ValueError("Invalid hydrophobicity values.")
            passed = [s for s, value in zip(charged, hydro) if -0.5 <= value <= 0.8]
            save_json(
                cache,
                {
                    "raw": count,
                    "clean": len(clean),
                    "stable": len(stable),
                    "charged": len(charged),
                    "passed": passed,
                    "seed": block_seed,
                },
            )
        for sequence in passed:
            if sequence not in seen:
                seen.add(sequence)
                kept.append(sequence)
        total_raw += count
        print(f"Generated {total_raw:,}; unique filter-passing peptides: {len(kept):,}")
    if TARGET_FILTERED is not None:
        kept = kept[:TARGET_FILTERED]
    library_validate_sequences(kept, "Generated pool")
    library_write_fasta(kept, PROJECT / "physicochemical_passed.fasta", "candidate")
    save_json(
        PROJECT / "generation_summary.json",
        {"raw_generated": total_raw, "filtered_unique": len(kept), "settings": generation_settings},
    )
stage_done("generation", generation_sources, generation_outputs, generation_settings)

del model
if torch.cuda.is_available():
    torch.cuda.empty_cache()
print(f"Ready: {len(kept):,} peptides. Stage time this session: {time.time() - start_time:.1f} seconds.")
if MODE == "full" and len(kept) < 50000:
    raise ValueError("Generation limit reached with fewer than 50,000 eligible peptides.")


# Stage from notebook cell 10
apex_sources = [PROJECT / "physicochemical_passed.fasta"] + sorted(
    (APEX / "APEX_pathogen_models").glob("APEX_*")
)
apex_outputs = [PREDICTIONS / "apex.csv"]
apex_settings = {"version": 3, "commit": APEX_COMMIT, "ensemble": "geometric mean of 8 models"}
if stage_ready("apex", apex_sources, apex_outputs, apex_settings):
    print("APEX: cached")
else:
    input_file = PROJECT / "physicochemical_passed.fasta"
    output_file = PROJECT / "predictions" / "apex.csv"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    candidates = [
        line.strip()
        for line in input_file.read_text().splitlines()
        if line.strip() and (not line.startswith(">"))
    ]
    if not candidates:
        raise ValueError("No peptides passed screening.")
    sys.path.insert(0, str(APEX))
    import APEX_models  # Required for checkpoint deserialization.

    PATHOGENS = [
        "A. baumannii ATCC 19606",
        "E. coli ATCC 11775",
        "E. coli AIG221",
        "E. coli AIG222",
        "K. pneumoniae ATCC 13883",
        "P. aeruginosa PA01",
        "P. aeruginosa PA14",
        "S. aureus ATCC 12600",
        "S. aureus ATCC BAA-1556 (MRSA)",
        "VRE E. faecalis ATCC 700802",
        "VRE E. faecium ATCC 700221",
    ]
    AA_INDEX = {
        "A": 3,
        "C": 4,
        "D": 5,
        "E": 6,
        "F": 7,
        "G": 8,
        "H": 9,
        "I": 10,
        "K": 11,
        "L": 12,
        "M": 13,
        "N": 14,
        "P": 15,
        "Q": 16,
        "R": 17,
        "S": 18,
        "T": 19,
        "V": 20,
        "W": 21,
        "Y": 22,
    }

    def encode_sequences(sequences):
        max_len = 52
        encoded = np.zeros((len(sequences), max_len), dtype=np.int64)
        for i, sequence in enumerate(sequences):
            sequence = sequence[: max_len - 2].upper()
            encoded[i, 0] = 1
            for j, aa in enumerate(sequence, start=1):
                encoded[i, j] = AA_INDEX[aa]
            encoded[i, len(sequence) + 1] = 2
        return encoded

    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"APEX device: {DEVICE}")
    model_files = sorted((APEX / "APEX_pathogen_models").glob("APEX_*"))
    if len(model_files) != 8:
        raise RuntimeError(f"Expected 8 APEX models; found {len(model_files)}")
    batch_size = 1000 if DEVICE.type == "cuda" else 128
    model_cache = PREDICTIONS / "apex_models"
    model_cache.mkdir(exist_ok=True)
    prediction_sum = None
    for number, model_file in enumerate(model_files, start=1):
        print(f"APEX model {number}/8")
        cache_file = model_cache / f"model_{number:02d}.npy"
        model_stage = f"apex_model_{number:02d}"
        model_inputs = [input_file, model_file]
        model_settings = {
            "commit": APEX_COMMIT,
            "version": 2,
            "stored": "log10 MIC in uM (6 - raw model output)",
        }
        if stage_ready(model_stage, model_inputs, [cache_file], model_settings):
            model_prediction = np.load(cache_file, allow_pickle=False)
            print("  Loaded completed model.")
        else:
            model = torch.load(model_file, map_location=DEVICE, weights_only=False)
            model = model.to(DEVICE).eval()
            batches = []
            with torch.no_grad():
                for start in range(0, len(candidates), batch_size):
                    sequences = candidates[start : start + batch_size]
                    encoded = encode_sequences(sequences)
                    X = torch.tensor(encoded, dtype=torch.long, device=DEVICE)
                    prediction = model(X).cpu().numpy()
                    # log10 MIC (uM); the ensemble is averaged in log space.
                    batches.append(6 - prediction)
            model_prediction = np.vstack(batches)
            if (
                model_prediction.shape != (len(candidates), 11)
                or not np.isfinite(model_prediction).all()
            ):
                raise ValueError("Invalid APEX model predictions.")
            temporary = cache_file.with_suffix(".tmp")
            with temporary.open("wb") as handle:
                np.save(handle, model_prediction, allow_pickle=False)
            temporary.replace(cache_file)
            stage_done(model_stage, model_inputs, [cache_file], model_settings)
            del model
            if DEVICE.type == "cuda":
                torch.cuda.empty_cache()
        if (
            model_prediction.shape != (len(candidates), 11)
            or not np.isfinite(model_prediction).all()
        ):
            raise ValueError("Invalid APEX checkpoint shape or numbers.")
        if prediction_sum is None:
            prediction_sum = model_prediction
        else:
            prediction_sum += model_prediction
    predictions = 10 ** (prediction_sum / len(model_files))
    if predictions.shape != (len(candidates), 11):
        raise ValueError(f"Unexpected APEX shape: {predictions.shape}")
    results = pd.DataFrame(predictions, index=candidates, columns=PATHOGENS)
    results.index.name = "Sequence"
    results.to_csv(output_file)
    print(f"Done: {len(results)} peptides scored across 11 pathogens.")
    print(f"Saved: {output_file}")
    stage_done("apex", apex_sources, apex_outputs, apex_settings)


# Stage from notebook cell 12
deep_sources = [PROJECT / "physicochemical_passed.fasta", deepamp_pin_file]
deep_outputs = [PREDICTIONS / "deepamp.csv"]
if stage_ready("deepamp", deep_sources, deep_outputs, {"version": 2}):
    print("Deep-AMP: cached")
else:
    expected = library_read_fasta(deep_sources[0])
    parts = []
    deep_chunks = PREDICTIONS / "deepamp_chunks"
    deep_chunks.mkdir(exist_ok=True)
    for start in range(0, len(expected), 5000):
        sequences = expected[start : start + 5000]
        fasta = deep_chunks / f"batch_{start:06d}.fasta"
        library_write_fasta(sequences, fasta, "candidate")
        outputs = []
        for name in ["CNN_gr_neg", "CNN_gr_pos"]:
            result_file = deep_chunks / f"{start:06d}_{name}.tsv"
            stage = f"deepamp_{start:06d}_{name}"
            if not stage_ready(stage, [fasta, deepamp_pin_file], [result_file], {"version": 1}):
                result_file.unlink(missing_ok=True)
                subprocess.run(
                    [
                        str(DEEPAMP_PYTHON),
                        "inference.py",
                        "-i",
                        str(fasta),
                        "-o",
                        str(result_file),
                        "-m",
                        f"saved_models/paper/regressor/{name}",
                    ],
                    cwd=DEEPAMP,
                    check=True,
                )
                checked = validate_prediction_rows(
                    pd.read_csv(result_file, sep="\t"), sequences, numeric=["MIC"]
                )
                stage_done(stage, [fasta, deepamp_pin_file], [result_file], {"version": 1})
            checked = validate_prediction_rows(
                pd.read_csv(result_file, sep="\t"), sequences, numeric=["MIC"]
            )
            outputs.append(checked)
        part = (
            outputs[0][["Sequence", "MIC"]]
            .rename(columns={"MIC": "DeepAMP CNN Gram- MIC"})
            .merge(
                outputs[1][["Sequence", "MIC"]].rename(columns={"MIC": "DeepAMP CNN Gram+ MIC"}),
                on="Sequence",
                validate="one_to_one",
            )
        )
        parts.append(part)
        print(f"Deep-AMP: {min(start + 5000, len(expected)):,}/{len(expected):,} saved.")
    results = pd.concat(parts, ignore_index=True)
    results.to_csv(deep_outputs[0], index=False)
    stage_done("deepamp", deep_sources, deep_outputs, {"version": 2})


# Stage from notebook cell 14
cheap_file = PREDICTIONS / "cheap_potency.csv"
potency_sources = [PREDICTIONS / "apex.csv", PREDICTIONS / "deepamp.csv", PROJECT / "physicochemical_passed.fasta"]
if not 0.0 <= APEX_WEIGHT <= 1.0:
    raise ValueError("APEX_WEIGHT must be between 0 and 1.")
potency_settings = {
    "version": 4,
    "definition": (
        "APEX_WEIGHT x APEX family percentile + (1 - APEX_WEIGHT) x Deep-AMP family "
        "percentile, where the Deep-AMP family is the mean of its Gram-negative and "
        "Gram-positive percentiles; lower is better"
    ),
    "apex_weight": APEX_WEIGHT,
    "direction": "ascending",
}

if stage_ready("cheap_potency", potency_sources, [cheap_file], potency_settings):
    combined = pd.read_csv(cheap_file, index_col="Sequence")
    print("Cheap potency ranking: cached")
else:
    apex = pd.read_csv(PREDICTIONS / "apex.csv", index_col="Sequence")
    deepamp = pd.read_csv(PREDICTIONS / "deepamp.csv").set_index("Sequence")
    if set(apex.index) != set(deepamp.index):
        raise ValueError("APEX and Deep-AMP scored different peptides.")
    if apex.index.duplicated().any() or deepamp.index.duplicated().any():
        raise ValueError("Duplicate potency predictions.")
    expected = library_read_fasta(PROJECT / "physicochemical_passed.fasta")
    if set(apex.index) != set(expected):
        raise ValueError("Predictions do not match the current peptide pool.")
    if (
        not np.isfinite(apex.to_numpy(dtype=float)).all()
        or not np.isfinite(deepamp.to_numpy(dtype=float)).all()
    ):
        raise ValueError("Invalid potency predictions.")
    apex_rank = apex.rank(pct=True, ascending=True).mean(axis=1)
    gramneg_rank = deepamp["DeepAMP CNN Gram- MIC"].rank(pct=True, ascending=True)
    grampos_rank = deepamp["DeepAMP CNN Gram+ MIC"].rank(pct=True, ascending=True)
    combined = pd.DataFrame(
        {"APEX rank": apex_rank, "DeepAMP Gram- rank": gramneg_rank, "DeepAMP Gram+ rank": grampos_rank}
    )
    # Deep-AMP contributes two columns; collapse them to one family score so the
    # APEX/Deep-AMP split is APEX_WEIGHT and not 1:2.
    combined["DeepAMP family rank"] = combined[["DeepAMP Gram- rank", "DeepAMP Gram+ rank"]].mean(axis=1)
    combined["Cheap potency score"] = (
        APEX_WEIGHT * combined["APEX rank"]
        + (1.0 - APEX_WEIGHT) * combined["DeepAMP family rank"]
    )
    combined = combined.sort_values(["Cheap potency score"], kind="stable")
    combined.to_csv(cheap_file)
    stage_done("cheap_potency", potency_sources, [cheap_file], potency_settings)
    print(f"Combined potency scores: {len(combined):,} peptides")
display(combined.head(10))


# Stage from notebook cell 16
selection_dir = PROJECT / "library_selection"
selection_dir.mkdir(exist_ok=True)
rank_sources = [
    PROJECT / "physicochemical_passed.fasta",
    PREDICTIONS / "cheap_potency.csv",
    ANTIBACTERIAL_FASTA,
]
rank_outputs = [selection_dir / "ranked_pool.csv"]
rank_settings = {
    "version": 4,
    "selection_rule": "top 50,000 from all basic-filter survivors after complete APEX + Deep-AMP scoring",
    "library_order": ["Cheap potency score", "Sequence"],
    "cheap_potency_definition": "weighted percentile rank of the APEX family and the Deep-AMP family; lower is better",
    "apex_weight": APEX_WEIGHT,
    "library_target": 50000,
    "no_secondary_library_heuristic": True,
}
if stage_ready("ranking", rank_sources, rank_outputs, rank_settings):
    library_ranking = pd.read_csv(rank_outputs[0])
    print("50k library selection: cached")
else:
    candidates = library_read_fasta(rank_sources[0])
    references = library_read_fasta(ANTIBACTERIAL_FASTA)
    full_ranking = library_build_ranking(
        candidates, pd.read_csv(rank_sources[1]), references
    )
    if MODE == "full" and len(full_ranking) < 50000:
        raise ValueError(
            f"Only {len(full_ranking):,} candidates survived basic filters/APEX/Deep-AMP; "
            "cannot build the required 50,000-member library."
        )
    target = 50000 if MODE == "full" else len(full_ranking)
    library_ranking = full_ranking.head(target).copy().reset_index(drop=True)
    library_ranking.to_csv(rank_outputs[0], index=False)
    stage_done("ranking", rank_sources, rank_outputs, rank_settings)
print(
    f"Library candidate pool: {len(library_ranking):,} peptides; "
    "this is the exact top pool after complete APEX/Deep-AMP scoring."
)
print("HemoPI2, tsAMP-CS and LLAMP operate inside this pool and never change its membership.")
display(library_ranking.head(10))


# Stage from notebook cell 18
shortlist_file = elite_dir / "shortlist.csv"
shortlist_fasta = elite_dir / "shortlist.fasta"
shortlist_settings = {"version": 2, "size": HEMO_INITIAL, "pool": "selected_50k_library"}
if stage_ready("hemo_shortlist", [selection_dir / "ranked_pool.csv"], [shortlist_file, shortlist_fasta], shortlist_settings):
    shortlist = pd.read_csv(shortlist_file)
    print("HemoPI2 shortlist: cached")
else:
    shortlist = choose_shortlist(library_ranking, size=HEMO_INITIAL)
    shortlist.to_csv(shortlist_file, index=False)
    library_write_fasta(shortlist["Sequence"], shortlist_fasta, "shortlist")
    stage_done("hemo_shortlist", [selection_dir / "ranked_pool.csv"], [shortlist_file, shortlist_fasta], shortlist_settings)
print(f"HemoPI2 will check {len(shortlist):,} peptides from the selected 50k library.")
print(shortlist["Shortlist reason"].value_counts().to_string())


# Stage from notebook cell 20
hemo_script = Path(
    subprocess.check_output(
        [
            str(HEMO_PYTHON),
            "-c",
            "from importlib.metadata import distribution; from pathlib import Path; d=distribution('hemopi2'); print(next(Path(d.locate_file(f)) for f in d.files if f.name=='hemopi2_classification.py'))",
        ],
        text=True,
    ).strip()
)
hemo_root = PROJECT / "hemopi2_elite"
hemo_root.mkdir(exist_ok=True)
references = library_read_fasta(ANTIBACTERIAL_FASTA)
hemo_parts, eligibility_parts = ([], [])
screened_sequences = set()
pending = shortlist.copy()
offset = 0
while len(pending):
    sequences = pending["Sequence"].tolist()
    for start in range(0, len(sequences), 500):
        subset = sequences[start : start + 500]
        batch_number = offset + start
        work = hemo_root / f"batch_{batch_number:05d}"
        work.mkdir(exist_ok=True)
        fasta = work / "input.fasta"
        output = work / "predictions.csv"
        library_write_fasta(subset, fasta, "candidate")
        hemo_settings = {"package": "hemopi2==1.3", "model": 3, "threshold": 0.58, "version": 1}
        stage = f"hemo_{batch_number:05d}"
        if not stage_ready(stage, [fasta], [output], hemo_settings):
            output.unlink(missing_ok=True)
            subprocess.run(
                [
                    str(HEMO_PYTHON),
                    "-u",
                    str(hemo_script),
                    "-i",
                    str(fasta),
                    "-wd",
                    str(work),
                    "-o",
                    "predictions.csv",
                    "-j",
                    "1",
                    "-m",
                    "3",
                    "-t",
                    "0.58",
                    "-d",
                    "2",
                ],
                cwd=hemo_script.parent,
                check=True,
            )
            validate_prediction_rows(
                pd.read_csv(output), subset, labels=["Hemolytic", "Non-Hemolytic"]
            )
            stage_done(stage, [fasta], [output], hemo_settings)
        checked = validate_prediction_rows(
            pd.read_csv(output), subset, labels=["Hemolytic", "Non-Hemolytic"]
        )
        hemo_parts.append(checked)
        decisions = elite_safety_eligibility(pd.DataFrame({"Sequence": subset}), checked)
        eligibility_parts.append(decisions)
        print(f"HemoPI2: {offset + min(start + 500, len(sequences)):,} checked and saved.")
    screened_sequences.update(sequences)
    offset += len(sequences)
    hemo_predictions = pd.concat(hemo_parts, ignore_index=True)
    eligibility = pd.concat(eligibility_parts, ignore_index=True)
    hemo_predictions.to_csv(elite_dir / "hemopi2_predictions.csv", index=False)
    eligibility.to_csv(elite_dir / "eligibility.csv", index=False)
    available = int((eligibility["Eligibility"] == "Eligible for stronger scoring").sum())
    print(f"Eligible for stronger scoring: {available:,}/{ELITE_TARGET:,}")
    if available >= ELITE_TARGET or offset >= HEMO_MAX_SCREEN:
        break
    remaining = library_ranking[~library_ranking["Sequence"].isin(screened_sequences)]
    pending = choose_shortlist(remaining, size=min(HEMO_TOPUP, HEMO_MAX_SCREEN - offset))
    if len(pending):
        print(f"Checking {len(pending):,} more candidates with HemoPI2.")
if not hemo_parts:
    raise ValueError("No candidates available for HemoPI2.")


# Stage from notebook cell 22
elite_files = [
    elite_dir / "elite_candidates.csv",
    elite_dir / "elite_candidates.fasta",
]
preview_files = [
    elite_dir / "preview_elite_candidates.csv",
    elite_dir / "preview_elite_candidates.fasta",
]
elite_settings = {"version": 3, "target": ELITE_TARGET, "selection_pool": "selected_50k_library"}
cached_full = stage_ready(
    "elite_panel", [selection_dir / "ranked_pool.csv", elite_dir / "eligibility.csv"], elite_files, elite_settings
)
cached_preview = stage_ready(
    "elite_panel", [selection_dir / "ranked_pool.csv", elite_dir / "eligibility.csv"], preview_files, elite_settings
)
if cached_full or cached_preview:
    panel_files = elite_files if cached_full else preview_files
    elite_panel = pd.read_csv(panel_files[0])
    panel_fasta = panel_files[1]
    complete_panel = len(elite_panel) == ELITE_TARGET
    print("Elite panel: cached")
else:
    elite_panel = prepare_elite_panel(library_ranking, eligibility, target=ELITE_TARGET)
    complete_panel = len(elite_panel) == ELITE_TARGET
    panel_files = elite_files if complete_panel else preview_files
    for path in elite_files + preview_files:
        path.unlink(missing_ok=True)
    elite_panel.to_csv(panel_files[0], index=False)
    panel_fasta = panel_files[1]
    library_write_fasta(elite_panel["Sequence"], panel_fasta, "elite")
    stage_done(
        "elite_panel",
        [selection_dir / "ranked_pool.csv", elite_dir / "eligibility.csv"],
        panel_files,
        elite_settings,
    )
    print("Elite panel checkpoint saved.")

if not panel_fasta.exists():
    raise FileNotFoundError(f"Elite panel FASTA missing: {panel_fasta}")
elite_sequences = elite_panel["Sequence"].tolist()
save_json(
    elite_dir / "scoring_status.json",
    {
        "target": ELITE_TARGET,
        "actual": len(elite_panel),
        "complete_panel": complete_panel,
        "fasta_sha256": library_hash(panel_fasta),
        "reference_sha256": library_hash(ANTIBACTERIAL_FASTA),
        "tsAMP_CS": "ready to run",
        "final_top100_ready": False,
    },
)
print(f"Prepared {len(elite_panel):,}/{ELITE_TARGET:,} candidates for stronger scoring.")
if not complete_panel:
    print("Elite target not fully met; downstream test will use the candidates available.")


# Stage from notebook cell 24
tsamp_dir = PREDICTIONS / "tsamp_cs"
tsamp_dir.mkdir(exist_ok=True)

elite_sequences = elite_panel["Sequence"].tolist()
esm_batch_dir = tsamp_dir / "esm_batches"
esm_batch_dir.mkdir(exist_ok=True)
esm_batch_settings = {
    "version": 2,
    "commit": TSAMP_COMMIT,
    "model": "esm1v_t33_650M_UR90S_1",
    "layer": 33,
    "mean_over_residues": True,
    "batch_size": TSAMP_EMBED_BATCH,
}

batch_arrays = []
for start in range(0, len(elite_sequences), TSAMP_EMBED_BATCH):
    subset = elite_sequences[start : start + TSAMP_EMBED_BATCH]
    batch_id = f"{start:06d}"
    fasta = esm_batch_dir / f"batch_{batch_id}.fasta"
    output = esm_batch_dir / f"batch_{batch_id}.npy"
    settings = {**esm_batch_settings, "start": start, "count": len(subset)}
    library_write_fasta(subset, fasta, "candidate")
    if not stage_ready(
        f"tsamp_esm1v_batch_{batch_id}",
        [fasta, tsamp_pin_file],
        [output],
        settings,
    ):
        values = tsamp_extract_esm1v(subset, batch_size=TSAMP_EMBED_BATCH)
        if values.shape != (len(subset), 1280):
            raise ValueError(f"Unexpected ESM-1v batch shape: {values.shape}")
        temporary = output.with_suffix(".tmp")
        with temporary.open("wb") as handle:
            np.save(handle, values, allow_pickle=False)
        temporary.replace(output)
        stage_done(
            f"tsamp_esm1v_batch_{batch_id}",
            [fasta, tsamp_pin_file],
            [output],
            settings,
        )
    batch_arrays.append(np.load(output, allow_pickle=False))

elite_esm = np.concatenate(batch_arrays, axis=0)
esm_file = tsamp_dir / "elite_esm1v.npy"
esm_settings = {**esm_batch_settings, "assembled": True, "batch_count": len(batch_arrays)}
if not stage_ready(
    "tsamp_esm1v",
    [esm_batch_dir / f"batch_{s:06d}.fasta" for s in range(0, len(elite_sequences), TSAMP_EMBED_BATCH)] + [tsamp_pin_file],
    [esm_file],
    esm_settings,
):
    temporary = esm_file.with_suffix(".tmp")
    with temporary.open("wb") as handle:
        np.save(handle, elite_esm, allow_pickle=False)
    temporary.replace(esm_file)
    stage_done(
        "tsamp_esm1v",
        [esm_batch_dir / f"batch_{s:06d}.fasta" for s in range(0, len(elite_sequences), TSAMP_EMBED_BATCH)] + [tsamp_pin_file],
        [esm_file],
        esm_settings,
    )

tsamp_release_esm1v()

if elite_esm.shape != (len(elite_sequences), 1280):
    raise ValueError(f"Unexpected elite ESM-1v shape: {elite_esm.shape}")

target_map = resolve_tsamp_targets(TSAMP_STRAINS, TSAMP_CS / "strain")
target_map.to_csv(tsamp_dir / "target_map.csv", index=False)
usable_targets = target_map[
    target_map["Usable"]
    & target_map["Challenge strain"].isin(TSAMP_PRIMARY_TARGETS)
].copy()

if set(usable_targets["Challenge strain"]) != set(TSAMP_PRIMARY_TARGETS):
    missing = sorted(set(TSAMP_PRIMARY_TARGETS) - set(usable_targets["Challenge strain"]))
    raise RuntimeError(f"Missing intended tsAMP-CS challenge targets: {missing}")

print(
    f"tsAMP-CS deployment coverage: {len(usable_targets)}/{len(CHALLENGE_STRAINS)} challenge strains."
)
display(target_map)

tsamp_output = tsamp_dir / "predictions.csv"
tsamp_settings = {
    "version": 2,
    "commit": TSAMP_COMMIT,
    "architecture": "2560->128->64->1",
    "activation": "ReLU after fc1 and fc3",
    "output": "log10 MIC uM; converted to MIC uM",
    "targets": usable_targets["Challenge strain"].tolist(),
    "panel_count": len(elite_sequences),
}

tsamp_parts = []
for row in usable_targets.to_dict("records"):
    target = row["Challenge strain"]
    safe_target = re.sub(r"[^A-Za-z0-9]+", "_", target).strip("_")
    output = tsamp_dir / "target_predictions" / f"{safe_target}.csv"
    output.parent.mkdir(exist_ok=True)
    checkpoint = TSAMP_CS / "strain" / f"{row['Species checkpoint']}.pt"
    strain_file = TSAMP_STRAINS / row["Strain embedding"]
    target_settings = {**tsamp_settings, "target": target}
    if stage_ready(
        f"tsamp_cs_target_{safe_target}",
        [panel_fasta, esm_file, tsamp_pin_file, checkpoint, strain_file],
        [output],
        target_settings,
    ):
        target_result = pd.read_csv(output)
    else:
        try:
            state = torch.load(checkpoint, map_location="cpu", weights_only=True)
        except TypeError:
            state = torch.load(checkpoint, map_location="cpu")
        validate_tsamp_checkpoint(state)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = TSAMPCSRecovered().to(device)
        model.load_state_dict(state, strict=True)
        model.eval()
        try:
            strain_obj = torch.load(strain_file, map_location="cpu", weights_only=True)
        except TypeError:
            strain_obj = torch.load(strain_file, map_location="cpu")
        strain_rep = strain_obj["mean_representations"][33].float().to(device)
        if tuple(strain_rep.shape) != (1280,):
            raise ValueError(f"Unexpected strain embedding shape: {strain_file.name}")
        peptide_tensor = torch.tensor(elite_esm, dtype=torch.float32, device=device)
        strain_batch = strain_rep.unsqueeze(0).expand(len(peptide_tensor), -1)
        combined = torch.cat([peptide_tensor, strain_batch], dim=1)
        with torch.no_grad():
            log_mic = model(combined).squeeze(1).cpu().numpy()
        if not np.isfinite(log_mic).all():
            raise ValueError(f"Invalid tsAMP-CS predictions for {target}.")
        target_result = pd.DataFrame({
            "Sequence": elite_sequences,
            f"log10 MIC | {target}": log_mic,
            f"MIC uM | {target}": np.power(10.0, log_mic),
        })
        temporary = output.with_suffix(".tmp")
        target_result.to_csv(temporary, index=False)
        temporary.replace(output)
        stage_done(
            f"tsamp_cs_target_{safe_target}",
            [panel_fasta, esm_file, tsamp_pin_file, checkpoint, strain_file],
            [output],
            target_settings,
        )
        del model
        if device.type == "cuda":
            torch.cuda.empty_cache()
    if target_result["Sequence"].tolist() != elite_sequences:
        raise ValueError(f"tsAMP-CS prediction order does not match elite panel for {target}.")
    tsamp_parts.append(target_result)

tsamp_predictions = tsamp_parts[0]
for part in tsamp_parts[1:]:
    tsamp_predictions = tsamp_predictions.merge(part, on="Sequence", validate="one_to_one")
if tsamp_predictions["Sequence"].duplicated().any():
    raise ValueError("Duplicate tsAMP-CS prediction rows.")
if tsamp_predictions["Sequence"].tolist() != elite_sequences:
    raise ValueError("tsAMP-CS prediction order does not match elite panel.")
temporary = tsamp_output.with_suffix(".tmp")
tsamp_predictions.to_csv(temporary, index=False)
temporary.replace(tsamp_output)
stage_done("tsamp_cs", [panel_fasta, esm_file, tsamp_pin_file] + [
    TSAMP_CS / "strain" / f"{row['Species checkpoint']}.pt" for row in usable_targets.to_dict("records")
] + [TSAMP_STRAINS / row["Strain embedding"] for row in usable_targets.to_dict("records")], [tsamp_output], tsamp_settings)

mic_columns = [c for c in tsamp_predictions if c.startswith("MIC uM | ")]
print(f"tsAMP-CS finished: {len(tsamp_predictions):,} peptides x {len(mic_columns)} challenge strains.")
display(tsamp_predictions[["Sequence"] + mic_columns[:5]].head(10))


# Stage from notebook cell 26
llamp_dir = PREDICTIONS / "llamp"
llamp_dir.mkdir(exist_ok=True)

llamp_output = llamp_dir / "predictions.csv"
llamp_verification_file = llamp_dir / "official_example.json"
llamp_species_dir = llamp_dir / "species"
llamp_species_dir.mkdir(exist_ok=True)

llamp_settings = {
    "version": 2,
    "commit": LLAMP_COMMIT,
    "peptide_model": LLAMP_HF_MODEL,
    "peptide_model_revision": LLAMP_HF_REVISION,
    "batch": LLAMP_BATCH,
    "output": "log10 MIC uM; converted to MIC uM",
    "fallback_targets": LLAMP_FALLBACK_TARGETS,
    "official_example_tolerance_log10": 0.001,
}

llamp_sources = [panel_fasta, llamp_pin_file, LLAMP_GENOME]
needed_species = sorted(set(LLAMP_FALLBACK_TARGETS.values()))

if stage_ready(
    "llamp_verification",
    [llamp_pin_file, LLAMP_WEIGHT, LLAMP_GENOME],
    [llamp_verification_file],
    {"version": 1, "tolerance": 0.001},
):
    llamp_verification = json.loads(llamp_verification_file.read_text())
    llamp_example_delta = float(llamp_verification["absolute_log10_difference"])
    print("LLAMP official example verification: cached")
else:
    import importlib.util
    from transformers import EsmTokenizer
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    module_spec = importlib.util.spec_from_file_location(
        "llamp_official_model", LLAMP / "utils" / "model.py"
    )
    llamp_official_model = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(llamp_official_model)
    verification_model = llamp_official_model.LLAMP(
        hidden_feat=256, pooling="CLS", pretrained_model=LLAMP_HF_RESOLVED
    )
    try:
        llamp_state = torch.load(LLAMP_WEIGHT, map_location="cpu", weights_only=True)
    except TypeError:
        llamp_state = torch.load(LLAMP_WEIGHT, map_location="cpu")
    load_result = verification_model.load_state_dict(llamp_state, strict=False)
    if load_result.missing_keys:
        raise RuntimeError(f"LLAMP missing checkpoint keys: {load_result.missing_keys}")
    allowed_unexpected = {
        "bert.embeddings.position_ids",
        "bert.embeddings.position_embeddings.weight",
    }
    unexpected = set(load_result.unexpected_keys)
    if unexpected - allowed_unexpected:
        raise RuntimeError(
            "Unexpected LLAMP checkpoint keys beyond the known transformers compatibility "
            f"difference: {sorted(unexpected - allowed_unexpected)}"
        )
    verification_model = verification_model.to(device).eval()
    tokenizer = EsmTokenizer.from_pretrained(LLAMP_HF_RESOLVED)
    try:
        genome_feat_dict = torch.load(LLAMP_GENOME, map_location="cpu", weights_only=False)
    except TypeError:
        genome_feat_dict = torch.load(LLAMP_GENOME, map_location="cpu")
    missing_species = sorted(set(needed_species) - set(genome_feat_dict))
    if missing_species:
        raise RuntimeError(f"LLAMP genome features missing fallback species: {missing_species}")

    def llamp_single_batch_predict(model, sequences, species):
        genome_vector = torch.as_tensor(
            genome_feat_dict[species][0], dtype=torch.float32, device=device
        )
        values = []
        with torch.no_grad():
            for start in range(0, len(sequences), LLAMP_BATCH):
                subset = sequences[start : start + LLAMP_BATCH]
                encoded = tokenizer(subset, padding=True, return_tensors="pt")
                output = model(
                    encoded["input_ids"].to(device),
                    encoded["attention_mask"].to(device),
                    genome_vector.unsqueeze(0).expand(len(subset), -1),
                )
                values.extend(np.asarray(output.detach().cpu(), dtype=float).reshape(-1).tolist())
        return np.asarray(values, dtype=np.float64)

    official_sequence = "SSSSSSAAAAARRRRRRRGGGGGGGG"
    official_species = "Escherichia coli"
    official_log10 = 1.8840848207473755
    reproduced_log10 = float(llamp_single_batch_predict(verification_model, [official_sequence], official_species)[0])
    llamp_example_delta = abs(reproduced_log10 - official_log10)
    if llamp_example_delta > 0.001:
        raise RuntimeError(
            "LLAMP official example did not reproduce closely enough. "
            "Benchmark/deployment predictions are blocked."
        )
    llamp_verification = {
        "sequence": official_sequence,
        "species": official_species,
        "authors_log10_mic": official_log10,
        "reproduced_log10_mic": reproduced_log10,
        "reproduced_mic_uM": 10 ** reproduced_log10,
        "absolute_log10_difference": llamp_example_delta,
        "tolerance": 0.001,
        "pass": True,
        "transformers_version": __import__("transformers").__version__,
        "hf_model_commit": getattr(verification_model.bert.config, "_commit_hash", None),
    }
    save_json(llamp_verification_file, llamp_verification)
    stage_done(
        "llamp_verification",
        [llamp_pin_file, LLAMP_WEIGHT, LLAMP_GENOME],
        [llamp_verification_file],
        {"version": 1, "tolerance": 0.001},
    )
    del verification_model
    if device.type == "cuda":
        torch.cuda.empty_cache()

import importlib.util
from transformers import EsmTokenizer

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
module_spec = importlib.util.spec_from_file_location(
    "llamp_official_model", LLAMP / "utils" / "model.py"
)
llamp_official_model = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(llamp_official_model)
llamp_model = llamp_official_model.LLAMP(
    hidden_feat=256, pooling="CLS", pretrained_model=LLAMP_HF_RESOLVED
)
try:
    llamp_state = torch.load(LLAMP_WEIGHT, map_location="cpu", weights_only=True)
except TypeError:
    llamp_state = torch.load(LLAMP_WEIGHT, map_location="cpu")
load_result = llamp_model.load_state_dict(llamp_state, strict=False)
allowed_unexpected = {
    "bert.embeddings.position_ids",
    "bert.embeddings.position_embeddings.weight",
}
if load_result.missing_keys or set(load_result.unexpected_keys) - allowed_unexpected:
    raise RuntimeError("LLAMP checkpoint compatibility check failed.")
llamp_model = llamp_model.to(device).eval()
tokenizer = EsmTokenizer.from_pretrained(LLAMP_HF_RESOLVED)
try:
    genome_feat_dict = torch.load(LLAMP_GENOME, map_location="cpu", weights_only=False)
except TypeError:
    genome_feat_dict = torch.load(LLAMP_GENOME, map_location="cpu")


def llamp_batch_predict(sequences, species):
    genome_vector = torch.as_tensor(genome_feat_dict[species][0], dtype=torch.float32, device=device)
    values = []
    with torch.no_grad():
        for start in range(0, len(sequences), LLAMP_BATCH):
            subset = sequences[start : start + LLAMP_BATCH]
            encoded = tokenizer(subset, padding=True, return_tensors="pt")
            output = llamp_model(
                encoded["input_ids"].to(device),
                encoded["attention_mask"].to(device),
                genome_vector.unsqueeze(0).expand(len(subset), -1),
            )
            values.extend(np.asarray(output.detach().cpu(), dtype=float).reshape(-1).tolist())
    return np.asarray(values, dtype=np.float64)

llamp_species_results = {}
for species in needed_species:
    safe_species = re.sub(r"[^A-Za-z0-9]+", "_", species).strip("_")
    output = llamp_species_dir / f"{safe_species}.csv"
    species_settings = {**llamp_settings, "species": species, "panel_count": len(elite_sequences)}
    if stage_ready(
        f"llamp_species_{safe_species}",
        [panel_fasta, llamp_pin_file, LLAMP_GENOME, LLAMP_WEIGHT],
        [output],
        species_settings,
    ):
        species_result = pd.read_csv(output)
    else:
        species_log10 = llamp_batch_predict(elite_sequences, species)
        if len(species_log10) != len(elite_sequences) or not np.isfinite(species_log10).all():
            raise RuntimeError(f"Invalid LLAMP predictions for {species}.")
        species_result = pd.DataFrame({
            "Sequence": elite_sequences,
            "log10 MIC": species_log10,
            "MIC uM": np.power(10.0, species_log10),
        })
        temporary = output.with_suffix(".tmp")
        species_result.to_csv(temporary, index=False)
        temporary.replace(output)
        stage_done(
            f"llamp_species_{safe_species}",
            [panel_fasta, llamp_pin_file, LLAMP_GENOME, LLAMP_WEIGHT],
            [output],
            species_settings,
        )
    if species_result["Sequence"].tolist() != elite_sequences:
        raise ValueError(f"LLAMP prediction order does not match elite panel for {species}.")
    llamp_species_results[species] = species_result
    print(f"LLAMP species checkpoint ready: {species}")

a = pd.DataFrame({"Sequence": elite_sequences})
for target, species in LLAMP_FALLBACK_TARGETS.items():
    species_values = llamp_species_results[species]["MIC uM"].to_numpy(dtype=float)
    species_log10 = llamp_species_results[species]["log10 MIC"].to_numpy(dtype=float)
    a[f"log10 MIC | {target}"] = species_log10
    a[f"MIC uM | {target}"] = species_values
llamp_predictions = a
if llamp_predictions["Sequence"].duplicated().any():
    raise ValueError("Duplicate LLAMP prediction rows.")
if llamp_predictions["Sequence"].tolist() != elite_sequences:
    raise ValueError("LLAMP prediction order does not match elite panel.")
temporary = llamp_output.with_suffix(".tmp")
llamp_predictions.to_csv(temporary, index=False)
temporary.replace(llamp_output)
stage_done(
    "llamp",
    llamp_sources + [llamp_species_dir / f"{re.sub(r'[^A-Za-z0-9]+', '_', s).strip('_')}.csv" for s in needed_species],
    [llamp_output, llamp_verification_file],
    llamp_settings,
)

del llamp_model
if device.type == "cuda":
    torch.cuda.empty_cache()

llamp_mic_columns = [c for c in llamp_predictions if c.startswith("MIC uM | ")]
if len(llamp_mic_columns) != len(LLAMP_FALLBACK_TARGETS):
    raise RuntimeError(
        f"Expected {len(LLAMP_FALLBACK_TARGETS)} LLAMP fallback targets, found {len(llamp_mic_columns)}."
    )
print(
    f"LLAMP finished: {len(llamp_predictions):,} peptides x "
    f"{len(llamp_mic_columns)} fallback challenge targets "
    f"({len(set(LLAMP_FALLBACK_TARGETS.values()))} species)."
)
display(llamp_predictions[["Sequence"] + llamp_mic_columns[:5]].head(10))


# Stage from notebook cell 28
ELITE_RANKING = {
    "version": 2,
    "activity_cutoff_uM": 16.0,
    "pass_rule": "MIC <= cutoff",
    "primary": "Predicted passes /20 (descending)",
    "tie_breaker": "tsAMP-CS passes /11 (descending)",
    "second_tie_breaker": "Mean predicted log10 MIC across all 20 targets (ascending)",
    "exact_ties": "Sequence (ascending; reproducible order only)",
    "final_models": ["tsAMP-CS", "LLAMP"],
    "interpretation": "Predicted pass count, not a calibrated expected experimental score",
}

final_table_file = elite_dir / "top100_metrics_tsamp_llamp.csv"
top_fasta = elite_dir / (
    "top100_tsamp_llamp.fasta" if MODE == "full" else "preview_top100_tsamp_llamp.fasta"
)
ranking_sources = [
    elite_dir / ("elite_candidates.csv" if complete_panel else "preview_elite_candidates.csv"),
    tsamp_output,
    llamp_output,
    ANTIBACTERIAL_FASTA,
]
ranking_outputs = [final_table_file, top_fasta]
final_ranking_settings = {
    "version": 4,
    "activity_cutoff_uM": 16.0,
    "primary": "Predicted passes /20 descending",
    "tie_breaker": "tsAMP-CS passes /11 descending",
    "second_tie_breaker": "Mean predicted log10 MIC ascending",
    "exact_ties": "Sequence ascending",
    "identity_limit": 0.8,
}

if stage_ready("final_ranking", ranking_sources, ranking_outputs, final_ranking_settings):
    final_table = pd.read_csv(final_table_file)
    top_sequences = library_read_fasta(top_fasta)
    scores = final_table.copy()
    tsamp_mic = tsamp_predictions.set_index("Sequence")[[c for c in tsamp_predictions.columns if c.startswith("MIC uM | ")]]
    llamp_mic = llamp_predictions.set_index("Sequence")[[c for c in llamp_predictions.columns if c.startswith("MIC uM | ")]]
    print("Final elite ranking: cached")
else:
    scores, tsamp_mic, llamp_mic = rank_elite_by_coverage(
        tsamp_predictions, llamp_predictions, elite_sequences,
        ELITE_RANKING["activity_cutoff_uM"],
    )
    final_table = scores.merge(
        elite_panel[
            ["Sequence", "Elite selection reason", "Cheap potency score",
             "Library selection score"]
        ],
        on="Sequence", validate="one_to_one",
    ).sort_values("Coverage rank", kind="stable").reset_index(drop=True)

    # Applies the <=80% identity guard against the reference set and within the
    # selection itself.
    top_sequences = choose_final_top(
        final_table.rename(columns={"Coverage rank": "Elite model score"}),
        references=references,
        count=min(FINAL_TOP_TARGET, len(final_table)),
        identity_limit=0.8,
        strict=(MODE == "full"),
    )
    rank_lookup = {seq: rank for rank, seq in enumerate(top_sequences, start=1)}
    final_table["Top selected"] = final_table["Sequence"].isin(top_sequences)
    final_table["Final rank"] = final_table["Sequence"].map(rank_lookup).astype("Int64")
    for matrix in [tsamp_mic, llamp_mic]:
        final_table = final_table.merge(
            matrix.reset_index(), on="Sequence", how="left", validate="one_to_one",
        )
    final_table.to_csv(final_table_file, index=False)
    library_write_fasta(top_sequences, top_fasta, "top")
    save_json(elite_dir / "ranking_method.json", ELITE_RANKING)
    stage_done("final_ranking", ranking_sources, ranking_outputs, final_ranking_settings)

print(f"Re-ranked {len(final_table):,} elite peptides; selected Top {len(top_sequences)}.")
print(f"Predicted pass: MIC <= {ELITE_RANKING['activity_cutoff_uM']:g} uM.")
print("Order: total passes /20, then tsAMP-CS passes /11 (both descending),")
print("then mean predicted log10 MIC ascending. Sequence order resolves exact ties.")
print("APEX/Deep-AMP do not contribute to this final ranking.")
print(f"Metrics: {final_table_file}")
print(f"FASTA: {top_fasta}")
display(final_table.loc[final_table["Top selected"], [
    "Final rank", "Sequence", "Predicted passes /20", "tsAMP-CS passes /11",
    "LLAMP passes /9", "Mean predicted log10 MIC", "Coverage rank",
]].head(25))


# Stage from notebook cell 30
export_dir = PROJECT / "final_files"
prefix = "" if MODE == "full" else "preview_"
final_output_files = [
    export_dir / f"{prefix}library.fasta",
    export_dir / f"{prefix}top.fasta",
    export_dir / "selected_library.csv",
    export_dir / "final_checks.json",
]
final_output_sources = [selection_dir / "ranked_pool.csv", top_fasta, ANTIBACTERIAL_FASTA]
final_output_settings = {"version": 3, "library_rule": "exact top 50,000 cheap-potency-ranked peptides", "mode": MODE}
if stage_ready("final_outputs", final_output_sources, final_output_files, final_output_settings):
    checks = json.loads((export_dir / "final_checks.json").read_text())
    print("Final submission files: cached")
else:
    checks = finalize_outputs(library_ranking, top_sequences, references, export_dir, MODE)
checks.update(
    {
        "run_mode": MODE,
        "elite_count": len(elite_panel),
        "top_count": len(top_sequences),
        "tsAMP_challenge_strains": len(
            [c for c in tsamp_predictions.columns if c.startswith("MIC uM | ")]
        ),
        "llamp_fallback_strains": len(LLAMP_FALLBACK_TARGETS),
        "llamp_fallback_species": len(set(LLAMP_FALLBACK_TARGETS.values())),
        "elite_ranking": ELITE_RANKING,
    }
)
checks["sequence_file_sha256"] = {
    name: library_hash(export_dir / f"{prefix}{name}")
    for name in ["library.fasta", "top.fasta"]
}
save_json(
    elite_dir / "scoring_status.json",
    {
        "target": ELITE_TARGET,
        "actual": len(elite_panel),
        "complete_panel": complete_panel,
        "fasta_sha256": library_hash(panel_fasta),
        "reference_sha256": library_hash(ANTIBACTERIAL_FASTA),
        "tsAMP_CS": "completed",
        "LLAMP": "completed",
        "final_top100_ready": MODE == "full" and len(top_sequences) == 100,
        "official_repository_validator_run": False,
        "sequence_file_sha256": checks["sequence_file_sha256"],
    },
)
save_json(export_dir / "final_checks.json", checks)
stage_done("final_outputs", final_output_sources, final_output_files, final_output_settings)
print(checks["status"])
print(f"Library: {checks['library_count']:,} unique peptides")
print(f"Top list: {checks['top_count']:,} peptides")


# Stage from notebook cell 32
method = {
    "generator": "PLUM",
    "PLUM_commit": PLUM_COMMIT,
    "APEX_commit": APEX_COMMIT,
    "DeepAMP_commit": deepamp_pin,
    "tsAMP_commit": TSAMP_COMMIT,
    "LLAMP_commit": LLAMP_COMMIT,
    "LLAMP_weight_source": LLAMP_WEIGHT_SOURCE,
    "LLAMP_weight_sha256": llamp_weight_sha256,
    "LLAMP_peptide_model": LLAMP_HF_MODEL,
    "LLAMP_peptide_model_revision": LLAMP_HF_REVISION,
    "seed": SEED,
    "run_mode": MODE,
    "raw_generation_ceiling": MAX_RAW,
    "raw_generated": total_raw,
    "target_basic_filtered_pool": TARGET_FILTERED,
    "library_target": 50000,
    "elite_target": ELITE_TARGET,
    "filters": {
        "length_generated": [8, 35],
        "canonical_only": True,
        "unique": True,
        "exclude_exact_training_and_reference": True,
        "instability_max": 40,
        "charge_pH7": [2, 10],
        "Eisenberg_hydrophobicity": [-0.5, 0.8],
    },
    "filter_provenance": {
        "length_generated": (
            "Upper bound 35 follows PLUM's trained length bins, which end at 31-35. "
            "Generating longer would exceed the released generator's conditioning range. "
            "The competition itself permits up to 50, so this is a self-imposed limit."
        ),
        "instability_max": (
            "Conventional instability-index cutoff of 40. Implemented as <= 40, not < 40."
        ),
        "charge_pH7": "Project screening choice; original source not recorded.",
        "Eisenberg_hydrophobicity": "Project screening choice; original source not recorded.",
        "note": (
            "None of these are competition requirements. All are screening choices applied "
            "before any potency model sees a candidate, and they therefore shape the pool "
            "the 50,000 library is drawn from."
        ),
    },
    "hemolysis_provenance": (
        "HemoPI2 model 3 was chosen over model 4 after model 4 showed problematic motif "
        "handling (negative motif credit on a no-hit branch); model 3 uses the supported "
        "ESM-only route. The 0.58 threshold is a deliberate departure from the documented "
        "default of 0.55; the origin of the specific value 0.58 is not recorded. Neither "
        "the model choice nor the threshold is a competition requirement."
    ),
    "component_licenses": {
        "PLUM": "MIT",
        "Deep-AMP": "MIT",
        "Meta ESM code": "MIT",
        "seqme": "BSD-3-Clause",
        "APEX": "University of Pennsylvania research-only",
        "HemoPI2": "GPL-3.0",
        "tsAMP": "no license file found",
        "LLAMP": "not established",
        "Daehun/peptide_tuned_ESM-2": "not established",
        "_status": (
            "Historical audit, not a fresh legal determination, and not complete: separate "
            "conclusions for individual weight files and datasets are not recorded. No "
            "third-party weights are redistributed in this package. Repositories and the "
            "LLAMP embedding model use pinned revisions; package distributions and "
            "upstream downloader assets retain their own provenance. The APEX research-only "
            "terms, the HemoPI2 GPL-3.0 terms and the absence of a tsAMP license should be "
            "reviewed before any public release of a repository that vendors them."
        ),
    },
    "cheap_potency": (
        f"Weighted percentile rank, lower is better. APEX family "
        f"(mean percentile across the 11 APEX strains) carries weight {APEX_WEIGHT}; "
        f"the Deep-AMP family carries {1 - APEX_WEIGHT}, and is itself the mean of the "
        f"Deep-AMP CNN Gram-negative and Gram-positive percentiles. At the run's "
        f"APEX_WEIGHT={APEX_WEIGHT} this is {APEX_WEIGHT:.0%} APEX, "
        f"{(1 - APEX_WEIGHT) / 2:.0%} Deep-AMP Gram-negative, "
        f"{(1 - APEX_WEIGHT) / 2:.0%} Deep-AMP Gram-positive."
    ),
    "apex_weight": APEX_WEIGHT,
    "apex_ensemble": (
        "Geometric mean of the 8 APEX models: each model's output is converted to "
        "log10 MIC (uM) as 6 - raw, the 8 log values are averaged, and the mean is "
        "converted back with 10**x."
    ),
    "library_selection": (
        "From all basic-filter survivors, retain the top 50,000 by Cheap potency score "
        "(weighted APEX/Deep-AMP percentile as described above; lower is better), "
        "with Sequence as deterministic tie-break. "
        "HemoPI2/strong models then operate only within this 50,000-member pool."
    ),
    "hemolysis": "HemoPI2 1.3 model 3, threshold 0.58; elite shortlist only",
    "tsAMP_CS": (
        "Released ESM-1v peptide embeddings plus released strain embeddings. "
        "Checkpoint-compatible 2560->128->64->1 architecture with ReLU after fc1/fc3."
    ),
    "tsAMP_CS_verification_status": (
        "Functionally validated on the authors' released held-out test data. "
        "Exact numerical agreement with the authors' own implementation is NOT established."
    ),
    "tsAMP_CS_verification_evidence": TSAMP_HELDOUT_RESULTS,
    "tsAMP_CS_verification_detail": (
        "Established. (a) The released checkpoint loads into the reconstructed module with "
        "strict=True and every tensor shape matches (2560->128->64->1). (b) The "
        "reconstruction was evaluated on the authors' released held-out test data for all "
        "10 species; per-species mean squared error and Spearman rank correlation are "
        "recorded in tsAMP_CS_verification_evidence. (c) An ablation removing the ReLU "
        "activations raised mean squared error on A. baumannii from 0.2614 to 3.6024, a "
        "~14x degradation, which is strong evidence that the ReLU placement in this "
        "reconstruction matches the original. "
        "NOT established. Exact numerical reproduction of the authors' own predictions for "
        "the same inputs. Layer shapes are recoverable from a checkpoint; dropout placement "
        "and any output transform are not, and the held-out results above would still look "
        "reasonable under small architectural differences. "
        "These are different claims and only the first is made here. For LLAMP the stronger "
        "claim does hold: the authors' published worked example is reproduced to within "
        "0.001 log10 units before any prediction is accepted."
    ),
    "LLAMP": (
        "Frozen released species-level model for the 9 challenge targets outside the "
        "11-strain tsAMP-CS deployment set. Output is log10 MIC in uM, converted with 10**x. "
        "Official authors' example must reproduce within 0.001 log10 units before use."
    ),
    "LLAMP_external_validation": (
        "46-peptide AMP-Diffusion wet-lab benchmark: absolute MIC calibration was poor and "
        "ranking performance was species-dependent. Pseudomonas was strongest; E. coli was "
        "mainly a coarse strong-vs-weak signal; Klebsiella and E. faecium were weak. "
        "Salmonella enterica and Enterobacter cloacae were not externally validated there."
    ),
    "elite_ranking": ELITE_RANKING,
    "top100": (
        "Descending predicted passes /20, then descending tsAMP-CS passes /11, then "
        "ascending mean predicted log10 MIC across all 20 targets; sequence order "
        "resolves exact ties. Subject to reference and internal identity <=0.80. "
        "APEX/Deep-AMP affect upstream shortlisting only, not final elite ordering."
    ),
    "elite_actual": len(elite_panel),
    "top_actual": len(top_sequences),
    "sequence_file_sha256": checks["sequence_file_sha256"],
    "reference_commit": REFERENCE_COMMIT,
    "chemistry": "Linear, free termini; no modifications requested",
    "manual_intervention": MANUAL_INTERVENTION_DECLARATION,
    "manual_intervention_declaration_status": (
        "submitter-confirmed statement supplied"
        if MANUAL_INTERVENTION_DECLARATION else "not recorded as a confirmed submitter declaration"
    ),
    "historical_manual_intervention_record": HISTORICAL_MANUAL_INTERVENTION_RECORD,
    "manual_intervention_basis": (
        "The code automates sequence generation, filtering, selection and ordering. "
        "The historical project record above is retained for review, not automatically "
        "treated as a declaration confirmed by the submitter. These artifacts cannot "
        "establish the absence of outside edits, discarded runs, or unrecorded seed searches."
    ),
    "seed_selection": SEED_SELECTION_DECLARATION,
    "reference_sha256": library_hash(ANTIBACTERIAL_FASTA),
    "python": platform.python_version(),
    "numpy": np.__version__,
    "torch": torch.__version__,
    "hardware": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
    "limitations": (
        "All potency and safety values are model predictions. tsAMP-CS is used only for "
        "11 exact challenge strains. LLAMP is species-level and therefore cannot distinguish "
        "multiple challenge strains within the same species; its external wet-lab benchmark "
        "also showed weak absolute MIC calibration and uneven ranking performance. "
        "LLAMP is also species-level, so the three E. coli and two Salmonella "
        "challenge strains that fall back to it receive identical predictions; those "
        "species therefore carry more weight in the passes /20 count than a strain-"
        "specific model would give them. "
        "Each major inference stage is checkpointed to the work directory so interrupted sessions can resume; the official repository submission validator remains a separate packaging step."
    ),
}
save_json(export_dir / "method_and_versions.json", method)

for name, executable in [
    ("pipeline", sys.executable),
    ("deepamp", str(DEEPAMP_PYTHON)),
    ("hemopi2", str(HEMO_PYTHON)),
]:
    frozen = subprocess.check_output(["uv", "pip", "freeze", "--python", executable], text=True)
    (export_dir / f"{name}_packages.txt").write_text(frozen)

print("Generation and scoring complete; files are ready for export.")
