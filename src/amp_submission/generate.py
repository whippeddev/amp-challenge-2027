"""Command-line entry point for actual generation and model inference."""
import argparse
import json
import os
from pathlib import Path
import runpy
import shutil
import sys


def parser():
    p = argparse.ArgumentParser(description="Generate the 50,000-member library and ranked Top 100.")
    p.add_argument("--work-dir", type=Path, default=Path(".amp-work/full-run1"), help="Persistent pipeline checkpoint directory.")
    p.add_argument("--tools-dir", type=Path, default=Path(".amp-tools"), help="Downloaded models and auxiliary environments.")
    p.add_argument("--output-dir", type=Path, default=Path("generate"), help="Destination of library.fasta and top.fasta.")
    p.add_argument("--preflight", action="store_true", help="Check prerequisites without downloading models or running inference.")
    return p


def main():
    args = parser().parse_args()
    root = Path(__file__).resolve().parents[2]
    missing = [name for name in ("git", "git-lfs", "uv") if shutil.which(name) is None]
    if sys.platform != "linux":
        raise SystemExit("This package targets Linux x86_64; use a Linux/Colab runtime.")
    if missing:
        raise SystemExit("Missing system tools: " + ", ".join(missing))
    required = [root / "uv.lock", root / "data/antibacterial.fasta"]
    required += [root / "environments" / env / "uv.lock" for env in ("deepamp", "hemopi2")]
    if absent := [str(p) for p in required if not p.is_file()]:
        raise SystemExit("Missing project files: " + ", ".join(absent))
    if not ((3, 13) <= sys.version_info[:2] < (3, 14)):
        raise SystemExit("Run with the project's Python 3.13 environment through uv.")
    options = {k: str(getattr(args, k).resolve()) for k in ("work_dir", "tools_dir", "output_dir")}
    if len(set(options.values())) != 3:
        raise SystemExit("Work, tools and output directories must be different.")
    if args.preflight:
        print("Project files and system tools are present. Model downloads/inference not tested.")
        print(json.dumps(options, indent=2))
        return
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    runpy.run_path(str(Path(__file__).with_name("pipeline.py")), init_globals={"RUN_OPTIONS": options})
    source = Path(options["work_dir"]) / "final_files"
    destination = Path(options["output_dir"])
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("library.fasta", "top.fasta", "final_checks.json", "method_and_versions.json"):
        temporary = destination / (name + ".tmp")
        shutil.copyfile(source / name, temporary)
        temporary.replace(destination / name)
    print(f"Exported {destination / 'library.fasta'} and {destination / 'top.fasta'}")


if __name__ == "__main__":
    main()
