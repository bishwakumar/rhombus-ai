"""
Runs each test case through the Rhombus pipeline and records every attempt, whatever happens.

Logging guarantees
  * A row is written to results/runs.csv the moment a run starts (status "started").
  * The row is updated after every stage, so a crash leaves the last stage reached.
  * Every event is also appended to results/runs.log (one JSON line, never rewritten).
  * Any failure is recorded with its cause:
      rhombus_failed  no output appeared; the Rhombus error you paste is stored
      bucket_error    a gcloud/GCS command failed; gcloud's message is stored
      aborted         you pressed Ctrl+C; the stage and any pasted error are stored
      runner_error    anything else; the Python error is stored
  * The log is backed up to the results bucket after every update (a failed backup never stops a run).

For every case and run:
  1. make sure the case file is in the source bucket (skips the upload if it's already there, unchanged)
  2. you trigger the run in Rhombus (or --trigger api)
  3. poll the output bucket until a new output file appears (no fixed sleeps)
  4. download it as outputs/<case>__run<N>.csv

Setup (once):
  gcloud auth login
  gcloud config set project ambient-climate-420216

Examples:
  python3 runner/run_cases.py --source-mode per-case --cases 03-schema-type-change
  python3 runner/run_cases.py --source-mode per-case --cases 00-baseline --runs 3
  python3 runner/run_cases.py --source-mode per-case --upload-only --cases 03-schema-type-change
  python3 runner/run_cases.py --cases 03-schema-type-change --attach RhombusAI_output_1791161346159.csv
  python3 runner/run_cases.py --cases 05-schema-combined --record-error "Pipeline failed at clean_orders: ..." --at 2026-10-05T12:15+11:00
"""
import argparse
import base64
import csv
import hashlib
import json
import os
import shutil
import subprocess
import time
import traceback
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------- configuration ----------
SOURCE_BUCKET = "rhombus-source"
SOURCE_OBJECT = "input/orders.csv"     # --source-mode fixed
CASES_PREFIX = "input/"                # --source-mode per-case: input/<case>.csv
OUTPUT_BUCKET = "rhombus-target"
OUTPUT_PREFIX = ""
RESULTS_BUCKET = "rhombus-runs"        # backup of runs.csv; "" disables
RESULTS_OBJECT = "runs.csv"
ROOT = Path(__file__).resolve().parent.parent
DATASETS = next((ROOT / d for d in ("dataset", "datasets") if (ROOT / d).is_dir()), ROOT / "dataset")
OUTPUTS = ROOT / "outputs"
RESULTS = ROOT / "results" / "runs.csv"
EVENTS = ROOT / "results" / "runs.log"
EVIDENCE = ROOT / "observations" / "evidence"
BASELINE = "00-baseline"

ALL_CASES = ["00-baseline", "01-schema-drop-column", "02-schema-rename-column", "03-schema-type-change",
             "04-schema-add-column", "05-schema-combined", "06-semantic-cents", "07-semantic-date-swap"]

FIELDS = ["run_id", "case_id", "run", "status", "stage", "started_at", "finished_at",
          "source_file", "source_object", "source_md5", "source_generation", "uploaded",
          "triggered_at", "output_detected_at", "seconds_to_output", "rhombus_output_file",
          "local_copy", "output_md5", "rhombus_error", "error", "notes"]

GCLOUD = shutil.which("gcloud") or "gcloud"
SOURCE_MODE = "per-case"


class BucketError(Exception):
    """A gcloud / GCS command failed."""


# ---------------------------------------------------------------- helpers
def now():
    return datetime.now(timezone.utc)


def iso(t=None):
    return (t or now()).isoformat(timespec="seconds")


def gcloud(*args):
    try:
        res = subprocess.run([GCLOUD, *args], capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise BucketError(f"gcloud {' '.join(args[:2])}: {e}")
    if res.returncode != 0:
        msg = (res.stderr or res.stdout).strip().splitlines()
        raise BucketError(f"gcloud {' '.join(args[:2])}: {msg[-1] if msg else 'failed'}")
    return res.stdout


def md5_hex(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def md5_b64(path):
    return base64.b64encode(hashlib.md5(Path(path).read_bytes()).digest()).decode()


def source_object(case_id):
    return SOURCE_OBJECT if SOURCE_MODE == "fixed" else f"{CASES_PREFIX}{case_id}.csv"


def source_url(case_id):
    return f"gs://{SOURCE_BUCKET}/{source_object(case_id)}"


def expected_header(case_id):
    with open(DATASETS / f"{case_id}.csv", newline="", encoding="utf-8") as f:
        return next(csv.reader(f))


def parse_time(t):
    t = str(t or "").strip().replace("Z", "+00:00")
    if len(t) > 5 and t[-5] in "+-" and t[-3] != ":":          # +0000 -> +00:00
        t = t[:-2] + ":" + t[-2:]
    try:
        d = datetime.fromisoformat(t)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


# ---------------------------------------------------------------- crash-proof log
def event(run_id, kind, **data):
    """Append-only journal: one JSON line per event, never rewritten."""
    EVENTS.parent.mkdir(parents=True, exist_ok=True)
    with open(EVENTS, "a", encoding="utf-8") as f:
        f.write(json.dumps({"at": iso(), "run_id": run_id, "event": kind, **data}) + "\n")


def _read_rows():
    if not RESULTS.exists():
        return []
    with open(RESULTS, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_rows(rows):
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    tmp = RESULTS.with_suffix(".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})
    tmp.replace(RESULTS)                       # atomic: the file is never half-written


def save(row):
    """Insert or update this run's row, then back it up. Never raises."""
    try:
        rows = _read_rows()
        for r in rows:                         # older logs without run_id get one
            r.setdefault("run_id", "")
            if not r["run_id"]:
                r["run_id"] = f"legacy-{r.get('case_id', '')}-{r.get('run', '')}"
        for i, r in enumerate(rows):
            if r["run_id"] == row["run_id"]:
                rows[i] = row
                break
        else:
            rows.append(row)
        _write_rows(rows)
    except Exception as e:                     # the journal still has everything
        print(f"  ! could not update runs.csv ({e}); see results/runs.log")
    backup()


def backup():
    if not RESULTS_BUCKET or not RESULTS.exists():
        return
    try:
        gcloud("storage", "cp", str(RESULTS), f"gs://{RESULTS_BUCKET}/{RESULTS_OBJECT}",
               "--content-type=text/csv")
    except BucketError as e:
        print(f"  ! run log not backed up ({e})")


def stage(row, name, **fields):
    row.update(stage=name, **fields)
    event(row["run_id"], name, **fields)
    save(row)


# ---------------------------------------------------------------- run steps
def ensure_source(case_id):
    """Upload the case file unless the bucket already has an identical copy. Returns (md5, generation, uploaded)."""
    local = DATASETS / f"{case_id}.csv"
    if not local.exists():
        raise FileNotFoundError(f"{local} not found")
    url = source_url(case_id)
    try:
        meta = json.loads(gcloud("storage", "objects", "describe", url, "--format=json"))
    except BucketError:
        meta = {}
    remote = meta.get("md5_hash") or meta.get("md5Hash")
    if remote == md5_b64(local):
        return md5_hex(local), str(meta.get("generation", "")), "no (already identical)"
    gcloud("storage", "cp", str(local), url, "--content-type=text/csv")
    meta = json.loads(gcloud("storage", "objects", "describe", url, "--format=json"))
    remote = meta.get("md5_hash") or meta.get("md5Hash")
    if remote and remote != md5_b64(local):
        raise BucketError(f"upload verification failed for {url}")
    return md5_hex(local), str(meta.get("generation", "")), "yes"


def list_outputs():
    pattern = f"gs://{OUTPUT_BUCKET}/{OUTPUT_PREFIX}*.csv"
    try:
        items = json.loads(gcloud("storage", "objects", "list", pattern, "--format=json") or "[]")
    except BucketError as e:
        if "matched no objects" in str(e).lower():
            return {}
        raise
    out = {}
    for it in items:
        url = (it.get("storage_url") or f"gs://{OUTPUT_BUCKET}/{it.get('name')}").split("#")[0]
        out[url] = it.get("creation_time") or it.get("timeCreated") or ""
    return out


def prompt_trigger(case_id, run):
    cols = expected_header(case_id)
    name = "_" + case_id.replace("-", "_")
    print(f"\n[{case_id} run {run}] Source ready: {source_url(case_id)}")
    print("  (No timer is running yet. Take as long as you need.)")
    input("  1. Press Enter to start the timer... ")
    if SOURCE_MODE == "fixed":
        print("  2. Reconnect the data source in Rhombus, then press the run button.")
    else:
        print(f"  2. In Rhombus, select dataset {name} in the Data Input node.")
        print("     Selecting it starts the run; press the run button only if nothing happens.")
    print(f"  3. The input preview should show {len(cols)} columns: {', '.join(cols)}")


def trigger(mode, case_id, run):
    if mode == "manual":
        prompt_trigger(case_id, run)
        return
    import requests
    url, token = os.environ.get("RHOMBUS_RUN_URL"), os.environ.get("RHOMBUS_TOKEN")
    if not url or not token:
        raise SystemExit("Set RHOMBUS_RUN_URL and RHOMBUS_TOKEN for api mode.")
    resp = requests.post(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    if resp.status_code >= 300:
        raise RuntimeError(f"run request failed: {resp.status_code} {resp.text[:200]}")


def wait_for_output(at_trigger, timeout):
    """First new CSV that was not in the bucket when Enter was pressed.
    Uses a snapshot, not timestamps, so clock differences can't hide an output.
    Returns (url, created, others) where others are extra new outputs (e.g. automatic runs)."""
    started, delay = now(), 3
    print("  waiting for output (Ctrl+C if Rhombus shows an error)", end="", flush=True)
    while (now() - started).total_seconds() < timeout:
        new = {u: t for u, t in list_outputs().items() if u not in at_trigger}
        if new:
            print()
            url = min(new, key=lambda u: new[u] or "")       # earliest new file
            others = sorted(u.rsplit("/", 1)[-1] for u in new if u != url)
            return url, new[url], others
        print(".", end="", flush=True)
        time.sleep(delay)
        delay = min(delay * 1.5, 15)
    print()
    return None, None, []


def ask_rhombus_error(case_id, run):
    print("  The runner can't see Rhombus errors. Check the Rhombus Logs panel.")
    try:
        msg = input("  Paste the first line of the Rhombus error (Enter if none): ").strip()
    except (EOFError, KeyboardInterrupt):
        msg = ""
    if msg:
        folder = EVIDENCE / case_id
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"run{run}-error.txt").write_text(msg + "\n", encoding="utf-8")
        print(f"  saved to observations/evidence/{case_id}/run{run}-error.txt (add the full log there too)")
    return msg


def next_run_number(case_id):
    used = [int(r["run"]) for r in _read_rows() if r.get("case_id") == case_id and str(r.get("run", "")).isdigit()]
    used += [int(p.stem.split("__run")[1]) for p in OUTPUTS.glob(f"{case_id}__run*.csv")
             if p.stem.split("__run")[1].isdigit()]
    return max(used, default=0) + 1


def run_case(case_id, mode, timeout):
    """One run. Always leaves a complete row in runs.csv, whatever fails."""
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    run = next_run_number(case_id)
    row = {"run_id": uuid.uuid4().hex[:8], "case_id": case_id, "run": run, "status": "started",
           "started_at": iso(), "source_file": f"{DATASETS.name}/{case_id}.csv",
           "source_object": source_url(case_id)}
    print(f"\n▶ {case_id} run {run} (run_id {row['run_id']})")
    stage(row, "started")
    try:
        md5, gen, uploaded = ensure_source(case_id)
        stage(row, "source_ready", source_md5=md5, source_generation=gen, uploaded=uploaded)
        print(f"  source {'uploaded' if uploaded == 'yes' else 'already in bucket'} (generation {gen})")

        before_load = set(list_outputs())
        stage(row, "waiting_for_trigger")
        trigger(mode, case_id, run)                # returns when you press Enter
        pressed = now()
        at_trigger = set(list_outputs())           # snapshot: anything new after this is ours
        early = sorted(u.rsplit("/", 1)[-1] for u in at_trigger - before_load)
        stage(row, "waiting_for_output", triggered_at=iso(pressed))

        url, created, others = wait_for_output(at_trigger, timeout)
        notes = []
        if early:
            notes.append(f"outputs before Enter (not this run): {', '.join(early)}")
            print(f"  ! {len(early)} output(s) appeared before Enter; not counted")
        if others:
            notes.append(f"extra outputs after Enter: {', '.join(others)}")
            print(f"  ! {len(others)} extra output(s) appeared; took the earliest")
        if notes:
            row["notes"] = "; ".join(notes)

        if url is None:
            print(f"  ✘ no output within {timeout}s")
            err = ask_rhombus_error(case_id, run)
            stage(row, "finished", status="rhombus_failed", finished_at=iso(), rhombus_error=err,
                  error="" if err else f"no output within {timeout}s and no Rhombus error recorded")
            return

        local = OUTPUTS / f"{case_id}__run{run}.csv"
        ct = parse_time(created)
        stage(row, "downloading", rhombus_output_file=url.rsplit("/", 1)[-1], output_detected_at=iso(),
              seconds_to_output=round((ct - pressed).total_seconds(), 1) if ct else "")
        gcloud("storage", "cp", url, str(local))
        stage(row, "finished", status="output_written", finished_at=iso(),
              local_copy=str(local.relative_to(ROOT)), output_md5=md5_hex(local))
        print(f"  ✔ {row['rhombus_output_file']} → outputs/{local.name}")

    except KeyboardInterrupt:
        print(f"\n  ⏹ stopped during '{row.get('stage')}'")
        err = ask_rhombus_error(case_id, run) if row.get("stage") == "waiting_for_output" else ""
        stage(row, "finished", status="aborted", finished_at=iso(), rhombus_error=err,
              error=f"stopped by user during {row.get('stage')}")
        raise SystemExit(130)
    except BucketError as e:
        print(f"  ✘ bucket error: {e}")
        stage(row, "finished", status="bucket_error", finished_at=iso(), error=str(e))
    except Exception as e:
        print(f"  ✘ runner error: {e}")
        event(row["run_id"], "traceback", trace=traceback.format_exc())
        stage(row, "finished", status="runner_error", finished_at=iso(), error=f"{type(e).__name__}: {e}")


def attach(case_id, name):
    """Record an existing Rhombus output against a case (e.g. one the runner missed)."""
    name = name.rsplit("/", 1)[-1]
    url = f"gs://{OUTPUT_BUCKET}/{OUTPUT_PREFIX}{name}"
    rows = [r for r in _read_rows() if r.get("case_id") == case_id]
    open_rows = [r for r in rows if r.get("status") in ("started", "aborted", "rhombus_failed")
                 and not r.get("local_copy")]
    row = dict(open_rows[-1]) if open_rows else {
        "run_id": uuid.uuid4().hex[:8], "case_id": case_id, "run": next_run_number(case_id),
        "started_at": iso(), "source_file": f"{DATASETS.name}/{case_id}.csv",
        "source_object": source_url(case_id)}
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    local = OUTPUTS / f"{case_id}__run{row['run']}.csv"
    gcloud("storage", "cp", url, str(local))
    note = f"output attached manually with --attach ({name})"
    row.update(status="output_written", stage="finished", finished_at=iso(), rhombus_output_file=name, error="",
               local_copy=str(local.relative_to(ROOT)), output_md5=md5_hex(local),
               notes="; ".join(x for x in (row.get("notes", ""), note) if x))
    event(row["run_id"], "attached", output=name)
    save(row)
    print(f"  ✔ {name} → outputs/{local.name} (run {row['run']}, recorded in runs.csv)")


def record_error(case_id, message, when=None):
    """Record a failed run that happened outside the runner (e.g. triggered directly in Rhombus)."""
    run = next_run_number(case_id)
    row = {"run_id": uuid.uuid4().hex[:8], "case_id": case_id, "run": run, "status": "rhombus_failed",
           "stage": "finished", "started_at": when or iso(), "triggered_at": when or iso(),
           "finished_at": iso(), "source_file": f"{DATASETS.name}/{case_id}.csv",
           "source_object": source_url(case_id), "rhombus_error": message.strip(),
           "notes": "recorded manually with --record-error (run not started by the runner)"}
    folder = EVIDENCE / case_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"run{run}-error.txt").write_text(message.strip() + "\n", encoding="utf-8")
    event(row["run_id"], "recorded_error", message=message.strip())
    save(row)
    print(f"  ✔ recorded {case_id} run {run} as rhombus_failed in runs.csv "
          f"(error saved to observations/evidence/{case_id}/run{run}-error.txt)")


def main():
    global SOURCE_MODE
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cases", nargs="+", default=ALL_CASES)
    p.add_argument("--runs", type=int, default=1, help="runs per case (3 for the consistency check)")
    p.add_argument("--trigger", choices=["manual", "api"], default="manual")
    p.add_argument("--timeout", type=int, default=120, help="seconds to wait for an output after Enter")
    p.add_argument("--source-mode", choices=["fixed", "per-case"], default="per-case",
                   help="per-case: input/<case>.csv (default); fixed: overwrite input/orders.csv")
    p.add_argument("--upload-only", action="store_true", help="only make sure the case files are in the bucket")
    p.add_argument("--record-error", metavar="TEXT",
                   help="record a failed run that happened outside the runner, with the Rhombus error text")
    p.add_argument("--at", metavar="TIME", help="with --record-error: when it happened, e.g. 2026-10-05T12:15+11:00")
    p.add_argument("--attach", metavar="RHOMBUS_OUTPUT",
                   help="record an existing output file for the given case, e.g. RhombusAI_output_123.csv")
    args = p.parse_args()
    SOURCE_MODE = args.source_mode

    try:
        gcloud("--version")
    except BucketError as e:
        raise SystemExit(f"gcloud is not available: {e}")

    if args.record_error:
        if len(args.cases) != 1:
            raise SystemExit("--record-error needs exactly one case, e.g. --cases 05-schema-combined")
        record_error(args.cases[0], args.record_error, args.at)
        return

    if args.attach:
        if len(args.cases) != 1:
            raise SystemExit("--attach needs exactly one case, e.g. --cases 03-schema-type-change")
        attach(args.cases[0], args.attach)
        return

    if args.upload_only:
        for case_id in args.cases:
            md5, gen, uploaded = ensure_source(case_id)
            print(f"  {case_id}: {source_url(case_id)} uploaded={uploaded} generation={gen}")
        return

    for case_id in args.cases:
        for _ in range(args.runs):
            run_case(case_id, args.trigger, args.timeout)
    print(f"\nDone. Log: {RESULTS.relative_to(ROOT)}  Journal: {EVENTS.relative_to(ROOT)}")
    print("Check: python3 runner/status.py")


if __name__ == "__main__":
    main()