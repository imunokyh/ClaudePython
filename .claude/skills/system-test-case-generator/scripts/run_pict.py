"""Run Microsoft PICT (https://github.com/microsoft/pict) on a model file and save the result as JSON.

Usage:
    python run_pict.py MODEL_FILE --id PICT-01 --out PICT-01.json [--order 2] [--seed 0]

The output JSON is meant to be pasted as-is into the "pict_models" list of the
test-case JSON consumed by build_workbook.py.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys


def find_pict():
    candidates = [
        os.environ.get("PICT_PATH"),
        shutil.which("pict"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "pict", "pict.exe"),
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    sys.exit(
        "ERROR: pict executable not found. Download pict.exe from "
        "https://github.com/microsoft/pict/releases and put it on PATH or set PICT_PATH."
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model", help="PICT model file")
    ap.add_argument("--id", required=True, help="Model ID referenced by test cases, e.g. PICT-01")
    ap.add_argument("--out", required=True, help="Output JSON path")
    ap.add_argument("--order", type=int, default=2, help="Combination order (default 2 = pairwise)")
    ap.add_argument("--seed", type=int, default=0, help="Random seed for reproducible output (default 0)")
    args = ap.parse_args()

    pict = find_pict()
    with open(args.model, encoding="utf-8") as f:
        model_text = f.read()

    cmd = [pict, args.model, f"/o:{args.order}", f"/r:{args.seed}"]
    proc = subprocess.run(cmd, capture_output=True)
    stdout = proc.stdout.decode("utf-8", errors="replace")
    stderr = "\n".join(
        l for l in proc.stderr.decode("utf-8", errors="replace").splitlines()
        if l.strip() and not l.startswith("Used seed")
    )
    if proc.returncode != 0:
        sys.exit(f"ERROR: pict failed (exit {proc.returncode}):\n{stderr}{stdout}")

    lines = [l for l in stdout.splitlines() if l.strip()]
    header = lines[0].split("\t")
    rows = [dict(zip(header, l.split("\t"))) for l in lines[1:]]

    result = {
        "id": args.id,
        "model_file": os.path.basename(args.model),
        "model": model_text,
        "command": "pict " + " ".join(cmd[1:]),
        "pict_version_source": "https://github.com/microsoft/pict",
        "order": args.order,
        "header": header,
        "rows": rows,
        "warnings": stderr.strip(),
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"{args.id}: {len(rows)} combinations ({args.order}-way) -> {args.out}")
    for i, r in enumerate(rows, 1):
        print(f"  #{i}: " + ", ".join(f"{k}={v}" for k, v in r.items()))
    if stderr.strip():
        print("PICT warnings:\n" + stderr.strip())


if __name__ == "__main__":
    main()
