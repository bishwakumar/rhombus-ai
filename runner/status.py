"""
Shows where every test case stands, in one table.

Reads only local files:
  results/runs.csv                 written by runner/run_cases.py
  outputs/<case>__run<N>.csv       downloaded Rhombus outputs
  results/validation/summary.csv   written by data-validation/validate.py

Usage:
  python3 runner/status.py            # one line per case
  python3 runner/status.py --runs     # one line per run, with notes
"""
import argparse
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "results" / "runs.csv"
OUTPUTS = ROOT / "outputs"
VALIDATION = ROOT / "results" / "validation" / "summary.csv"
DATASETS = next((ROOT / d for d in ("dataset", "datasets") if (ROOT / d).is_dir()), ROOT / "dataset")


def read(path):
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def cases():
    return sorted(p.stem for p in DATASETS.glob("*.csv") if not p.stem.endswith(".expected"))


def latest_verdicts():
    """Most recent validator verdict per output file."""
    out = {}
    for r in read(VALIDATION):
        out[r["output_file"]] = r
    return out


def short(text, n):
    text = text or ""
    return text if len(text) <= n else text[: n - 1] + "…"


def per_case(runs, verdicts):
    print(f"{'case':<26} {'runs':>4}  {'last status':<15} {'last output':<28} {'validator':<21} next step")
    print("-" * 110)
    for case in cases():
        rows = [r for r in runs if r["case_id"] == case]
        if not rows:
            print(f"{case:<26} {0:>4}  {'—':<15} {'—':<28} {'—':<21} not run yet")
            continue
        last = rows[-1]
        status = last.get("status", "")
        local = Path(last.get("local_copy") or "").name
        key = local or f"{case}__run{last.get('run')}__{last.get('run_id') or 'legacy'}"   # stopped runs
        v = verdicts.get(key, {}).get("verdict", "")
        if status == "output_written" and not v:
            step = f"validate: python3 data-validation/validate.py {case}"
        elif status == "output_written":
            step = ("done" if v == "PASS" else
                    "done (read the warnings)" if v in ("PASS (with warnings)", "WARN") else
                    "check validator detail, then chatbot if needed")
        elif status in ("no_output", "rhombus_failed", "aborted") and not v:
            step = f"record it: python3 data-validation/validate.py {case}"
        elif status in ("no_output", "rhombus_failed", "aborted"):
            err = last.get("rhombus_error") or ""
            step = (f"Rhombus: {short(err, 45)} → save full log; chatbot step" if err
                    else "check Rhombus log for this time; save it as evidence; chatbot step")
        elif status == "bucket_error":
            step = f"bucket problem: {short(last.get('error', ''), 50)} → fix, then rerun"
        elif status == "runner_error":
            step = f"runner problem: {short(last.get('error', ''), 50)} → see results/runs.log"
        elif status == "started":
            step = f"interrupted at stage '{last.get('stage', '')}' → rerun"
        else:
            step = "check runs.csv row"
        print(f"{case:<26} {len(rows):>4}  {status:<15} {short(local, 28):<28} {v or '—':<21} {step}")


def per_run(runs, verdicts):
    print(f"{'case':<26} {'run':>3}  {'triggered (UTC)':<20} {'status':<15} {'validator':<21} notes")
    print("-" * 120)
    for r in runs:
        local = Path(r.get("local_copy") or "").name
        key = local or f"{r['case_id']}__run{r.get('run')}__{r.get('run_id') or 'legacy'}"
        v = verdicts.get(key, {}).get("verdict", "—")
        info = r.get("rhombus_error") or r.get("error") or r.get("notes") or ""
        print(f"{r['case_id']:<26} {r['run']:>3}  {short(r.get('triggered_at', '') or r.get('started_at', ''), 20):<20} "
              f"{r.get('status', ''):<15} {v:<21} {short(info, 50)}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--runs", action="store_true", help="show every run instead of one line per case")
    args = p.parse_args()

    runs, verdicts = read(RUNS), latest_verdicts()
    if not runs:
        print(f"No runs recorded yet ({RUNS.relative_to(ROOT)} not found).")
        return
    (per_run if args.runs else per_case)(runs, verdicts)

    stray = sorted(f.name for f in OUTPUTS.glob("*.csv")
                   if f.name not in {Path(r.get("local_copy") or "").name for r in runs})
    if stray:
        print(f"\nOutputs not in runs.csv (captured by hand?): {', '.join(stray)}")


if __name__ == "__main__":
    main()