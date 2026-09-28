"""Run the organizers' unchanged sequence checks without generation."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[2]
    p = argparse.ArgumentParser(description="Validate existing FASTA files using the official checking functions.")
    p.add_argument("--directory", type=Path, default=root / "results/reference_run")
    p.add_argument("--reference", type=Path, default=root / "data/antibacterial.fasta")
    args = p.parse_args()
    spec = importlib.util.spec_from_file_location("official_validator", root / "scripts/verify_submission.py")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    library_path, top_path = args.directory / "library.fasta", args.directory / "top.fasta"
    full = validator._verify_sequences(library_path)
    validator._verify_top(top_path, full, validator.TOP_SIZE)
    _, references = validator._read_fasta(args.reference)
    validator._verify_no_overlap(full, set(references))
    _, top = validator._read_fasta(top_path)
    validator._veritfy_max_simularity(set(top), set(references))
    print(json.dumps({
        "sequence_checks_passed": True,
        "library_count": len(full),
        "top_count": len(top),
        "sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (library_path, top_path)},
        "scope": "Official sequence checks only; repository installation and generation reproducibility not tested.",
    }, indent=2))


if __name__ == "__main__":
    main()
