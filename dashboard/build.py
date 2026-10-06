#!/usr/bin/env python3
"""Fold runner + validator records into dashboard/data.json."""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = ROOT / "outputs"
RUNS = ROOT / "results" / "runs.csv"
VALIDATION = ROOT / "results" / "validation"
OUT = Path(__file__).resolve().parent / "data.json"
UI_VIDEOS = ROOT / "ui-tests" / "videos"
DASH_VIDEOS = Path(__file__).resolve().parent / "videos"

# Video file → (group, test title, what it shows). File names come from ui-tests/helpers/fixtures.ts.
VIDEO_INFO = {
    "1-source-connection-gcs-source-bucket-is-connected":
        ("1 · Source connection", "GCS source bucket is connected",
         "Opens the Data Input node's sources and finds rhombus-source marked Connected."),
    "2-ai-built-pipeline-canvas-has-data-input-custom-ai-cleaning-step-data-output":
        ("2 · AI-built pipeline", "Canvas has Data Input → Custom → Data Output",
         "The AI-built pipeline is in place on the canvas."),
    "2-ai-built-pipeline-manual-run-succeeds-and-writes-a-new-cleaned-file-to-gcs":
        ("2 · AI-built pipeline", "Manual run writes a new cleaned file to GCS",
         "Clicks Run, waits for success in the logs, then confirms a new file with the cleaned header in rhombus-target."),
    "3-gcs-destination-data-output-node-exports-to-the-gcs-destination-bucket":
        ("3 · GCS destination", "Data Output exports to the GCS bucket",
         "The output node is configured for rhombus-target."),
    "4-schedule-an-hourly-schedule-can-be-created-and-shows-active-with-a-next-run-time":
        ("4 · Schedule", "Hourly schedule shows Active with a next run time",
         "Creates a schedule and checks it shows Active with a real next-run time."),
    "5-known-issues-confirmed-still-present-f8-s3-connection-is-still-rejected-with-the-generated-bucket-policy":
        ("5 · Known issues", "F8: S3 connection still rejected",
         "Fills in the S3 connection with the generated policy applied; Rhombus still denies access."),
    "5-known-issues-confirmed-still-present-f4-an-active-5-schedule-still-produces-no-run-within-7-minutes":
        ("5 · Known issues", "F4: Active */5 schedule produces no run",
         "Creates a */5 schedule and watches the bucket for 7 minutes; no run happens."),
}


def collect_videos():
    """Copy the UI test videos next to the dashboard (so the hosted page can play them) and list them."""
    if not UI_VIDEOS.exists():
        return []
    DASH_VIDEOS.mkdir(exist_ok=True)
    videos = []
    for src in sorted(UI_VIDEOS.glob("*.webm")):
        dest = DASH_VIDEOS / src.name
        if not dest.exists() or dest.stat().st_size != src.stat().st_size or dest.stat().st_mtime < src.stat().st_mtime:
            shutil.copy2(src, dest)
        group, title, about = VIDEO_INFO.get(src.stem, ("UI tests", src.stem.replace("-", " "), ""))
        videos.append({"file": f"videos/{src.name}", "group": group, "title": title, "about": about,
                       "bytes": src.stat().st_size})
    return videos

CASES = [
    {
        "id": "00-baseline",
        "label": "Baseline",
        "group": "baseline",
        "drift": "None — messy but expected schema",
        "capability": "handled",
        "headline": "handled",
        "detail": "Cleaning is accurate on the original file. 470/470 rows match the answer key aside from export formatting (5.0 vs 5, trailing zeros).",
        "rhombus": "Success (correct)",
        "severity": "low",
    },
    {
        "id": "01-schema-drop-column",
        "label": "Drop column",
        "group": "schema",
        "drift": "email column removed",
        "capability": "breaks",
        "headline": "breaks (stale, then stop)",
        "detail": "First run completed on a snapshot that still had email (383 emails not in the new input). After reconnect it stopped on KeyError 'email'. Chatbot claimed a fix; code_sha did not change.",
        "rhombus": "Stale success, then stopped",
        "severity": "high",
    },
    {
        "id": "02-schema-rename-column",
        "label": "Rename column",
        "group": "schema",
        "drift": "amount_usd → total_amount",
        "capability": "handled",
        "headline": "handled (stops)",
        "detail": "Pipeline stopped on missing amount_usd. Correct to refuse, but the log does not recognise the rename — it only says the old name is missing.",
        "rhombus": "Stopped ('amount_usd')",
        "severity": "medium",
    },
    {
        "id": "03-schema-type-change",
        "label": "Type change",
        "group": "schema",
        "drift": "order_date as Unix timestamps",
        "capability": "missed",
        "headline": "missed (silent blanks)",
        "detail": "Reported success while wiping every date (100% blank vs 8.7% baseline). Two identical failing runs; a later chatbot code patch produced a third, different output that matched the baseline.",
        "rhombus": "Success",
        "severity": "high",
    },
    {
        "id": "04-schema-add-column",
        "label": "Add column",
        "group": "schema",
        "drift": "discount_code added",
        "capability": "silent_drop",
        "headline": "silent drop",
        "detail": "Completed successfully. Values stay correct; the new column is discarded with no warning. Output is byte-identical to baseline.",
        "rhombus": "Success",
        "severity": "medium",
    },
    {
        "id": "05-schema-combined",
        "label": "Combined schema",
        "group": "combined",
        "drift": "Drop + rename + type change + add column",
        "capability": "breaks",
        "headline": "breaks (first error only)",
        "detail": "Stopped on 'email' only. Chatbot said it regenerated code; run 3 failed with the same code_sha. The other three drifts would never be reported.",
        "rhombus": "Stopped ('email')",
        "severity": "high",
    },
    {
        "id": "06-semantic-cents",
        "label": "Semantic: cents",
        "group": "semantic",
        "drift": "Dollars written as cents in amount_usd",
        "capability": "missed",
        "headline": "missed (100× amounts)",
        "detail": "Completed successfully. 425 amounts 100× too high (max 199,849.00). Schema, rows and blank-rate checks all passed; only the range check caught it.",
        "rhombus": "Success",
        "severity": "high",
    },
    {
        "id": "07-semantic-date-swap",
        "label": "Semantic: date swap",
        "group": "semantic",
        "drift": "MM/DD written as DD/MM",
        "capability": "missed",
        "headline": "missed (252 wrong dates)",
        "detail": "Completed successfully. 252 dates changed meaning; 208 fall outside Jan–Mar, 44 swap into another valid date and cannot be seen from the output.",
        "rhombus": "Success",
        "severity": "high",
    },
]


def md5_of(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def read_csv_rows(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def parse_float(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def load_runs():
    if not RUNS.exists():
        return []
    with RUNS.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_validations():
    records = []
    for path in sorted(VALIDATION.glob("*.json")):
        records.append(json.loads(path.read_text()))
    return records


def check_map(record):
    return {c["check"]: c for c in record.get("checks", [])}


def classify_run(row):
    status = row.get("status") or ""
    if status == "output_written":
        return "success"
    if status in ("rhombus_failed", "no_output"):
        return "stopped"
    if status == "aborted":
        return "aborted"
    return status or "unknown"


def duration_seconds(row):
    s = parse_float(row.get("seconds_to_output"))
    if s is not None:
        return s
    # Attached/manual successes often have a long start→finish window that is
    # not pipeline time. Only use wall clock for runs that never wrote output.
    if row.get("status") == "output_written":
        return None
    start, end = row.get("started_at") or "", row.get("finished_at") or ""
    if start and end:
        try:
            a = datetime.fromisoformat(start.replace("Z", "+00:00"))
            b = datetime.fromisoformat(end.replace("Z", "+00:00"))
            return round((b - a).total_seconds(), 1)
        except ValueError:
            return None
    return None


def sample_diff(path_a: Path, path_b: Path, limit=8):
    ha, ra = read_csv_rows(path_a)
    hb, rb = read_csv_rows(path_b)
    cols = list(dict.fromkeys(ha + hb))
    samples = []
    differing = 0
    n = min(len(ra), len(rb))
    for i in range(n):
        cells = []
        for col in cols:
            left, right = ra[i].get(col, ""), rb[i].get(col, "")
            if left != right:
                cells.append({"col": col, "left": left, "right": right})
        if cells:
            differing += 1
            if len(samples) < limit:
                samples.append({
                    "order_id": ra[i].get("order_id") or rb[i].get("order_id"),
                    "cells": cells,
                })
    differing += abs(len(ra) - len(rb))
    return {
        "left": path_a.name,
        "right": path_b.name,
        "rows_left": len(ra),
        "rows_right": len(rb),
        "differing_rows": differing,
        "identical": differing == 0 and len(ra) == len(rb),
        "samples": samples,
    }


def validation_for_output(validations, filename):
    for rec in validations:
        if rec.get("output_file") == filename:
            return rec
    return None


def oracle_examples(record, limit=6):
    correct = check_map(record).get("correct") or {}
    out = []
    for col, stats in (correct.get("columns") or {}).items():
        for ex in stats.get("examples") or []:
            out.append({
                "order_id": ex.get("order_id"),
                "column": col,
                "expected": ex.get("correct"),
                "actual": ex.get("actual"),
            })
            if len(out) >= limit:
                return out
    return out


def main():
    runs = load_runs()
    validations = load_validations()
    outputs = sorted(OUTPUTS.glob("*.csv"))
    outputs_by_case = defaultdict(list)
    for path in outputs:
        case = path.name.split("__")[0]
        outputs_by_case[case].append(path)

    run_rows = []
    for row in runs:
        case = row.get("case_id")
        local = Path(row.get("local_copy") or "").name
        val = validation_for_output(validations, local) if local else None
        if val is None:
            # stopped records are named <case>__runN__<id>
            rid = row.get("run_id") or ""
            run_n = row.get("run") or ""
            for rec in validations:
                name = rec.get("output_file") or ""
                if name.startswith(f"{case}__run{run_n}") and (rid in name or rec.get("verdict") == "STOPPED"):
                    if rec.get("case_id") == case:
                        val = rec
                        break
        checks = check_map(val) if val else {}
        run_rows.append({
            "run_id": row.get("run_id"),
            "case_id": case,
            "run": int(row["run"]) if (row.get("run") or "").isdigit() else row.get("run"),
            "runner_status": row.get("status"),
            "pipeline": classify_run(row),
            "seconds": duration_seconds(row),
            "triggered_at": row.get("triggered_at") or row.get("started_at"),
            "output_file": local or None,
            "output_md5": row.get("output_md5") or None,
            "rhombus_error": (row.get("rhombus_error") or "")[:280] or None,
            "notes": row.get("notes") or None,
            "verdict": (val or {}).get("verdict"),
            "checks": {k: v.get("status") for k, v in checks.items()} if checks else {},
        })

    scenarios = []
    for meta in CASES:
        cid = meta["id"]
        case_runs = [r for r in run_rows if r["case_id"] == cid]
        files = outputs_by_case.get(cid, [])
        md5s = sorted({md5_of(p) for p in files})
        comparisons = []
        if len(files) >= 2:
            first = files[0]
            for other in files[1:]:
                comparisons.append(sample_diff(first, other))
        protocol_complete = len(files) >= 3
        identical = len(md5s) <= 1 and len(files) >= 2
        variance = len(md5s) > 1

        # Health on material outcomes: output_written, rhombus_failed, no_output
        material = [r for r in case_runs if r["pipeline"] in ("success", "stopped")]
        rhombus_ok = sum(1 for r in material if r["pipeline"] == "success")
        validator_pass = sum(
            1 for r in case_runs
            if r.get("verdict") in ("PASS", "PASS (with warnings)")
        )
        validator_fail = sum(1 for r in case_runs if r.get("verdict") == "FAIL")
        validator_stopped = sum(1 for r in case_runs if r.get("verdict") == "STOPPED")
        times = [r["seconds"] for r in case_runs if r["seconds"] is not None]
        times_success = [r["seconds"] for r in case_runs if r["pipeline"] == "success" and r["seconds"] is not None]

        # Representative validation record: the WORST verdict among runs that produced an output,
        # so a later fix (e.g. the case 03 chatbot patch) can't hide Rhombus's default behaviour.
        rank = {"FAIL": 3, "PASS (with warnings)": 2, "WARN": 2, "PASS": 1}
        latest_val = None
        for rec in validations:
            if rec.get("case_id") == cid and rec.get("verdict") != "STOPPED":
                if latest_val is None or rank.get(rec.get("verdict"), 0) > rank.get(latest_val.get("verdict"), 0):
                    latest_val = rec
        if latest_val is None:
            for rec in reversed(validations):
                if rec.get("case_id") == cid:
                    latest_val = rec
                    break

        scenarios.append({
            **meta,
            "runs": case_runs,
            "material_runs": len(material),
            "rhombus_successes": rhombus_ok,
            "rhombus_stops": sum(1 for r in material if r["pipeline"] == "stopped"),
            "aborted": sum(1 for r in case_runs if r["pipeline"] == "aborted"),
            "validator_pass": validator_pass,
            "validator_fail": validator_fail,
            "validator_stopped": validator_stopped,
            "success_rate_rhombus": round(100 * rhombus_ok / len(material), 1) if material else None,
            "pass_rate_validator": round(100 * validator_pass / len(case_runs), 1) if case_runs else None,
            "times": times,
            "times_to_output": times_success,
            "median_seconds": sorted(times_success)[len(times_success) // 2] if times_success else None,
            "output_files": [p.name for p in files],
            "output_md5s": md5s,
            "output_bytes": [p.stat().st_size for p in files],
            "consistency": {
                "protocol_n": 3,
                "captured_outputs": len(files),
                "protocol_complete": protocol_complete,
                "unique_md5s": len(md5s),
                "identical": identical,
                "variance": variance,
                "note": (
                    "Byte-identical across captured outputs."
                    if identical else
                    "Outputs differ between runs — see side-by-side diffs."
                    if variance else
                    "Fewer than two captured outputs; consistency not established."
                ),
                "comparisons": comparisons,
            },
            "oracle_examples": oracle_examples(latest_val) if latest_val else [],
            "latest_verdict": (latest_val or {}).get("verdict"),
            "latest_detail": (
                (check_map(latest_val).get("correct") or {}).get("detail")
                or (check_map(latest_val).get("schema") or {}).get("detail")
                or (check_map(latest_val).get("semantics") or {}).get("detail")
                if latest_val else None
            ),
        })

    # Observation-backed extra for case 01 stop (not in runner csv)
    extra_notes = {
        "01-schema-drop-column": "Runner captured only the stale success. Observation: after reconnect, a second run stopped at 15:09 with KeyError 'email' and wrote nothing.",
        "07-semantic-date-swap": "Observation records three byte-identical successes; two are saved under outputs/.",
        "06-semantic-cents": "One dataset selection produced two outputs ~40s apart; one file is saved.",
        "03-schema-type-change": "Runs 3 and 4 are byte-identical (dates blank). Run 6 differs because the chatbot patched the code between runs, not because of non-determinism.",
    }
    for s in scenarios:
        if s["id"] in extra_notes:
            s["consistency"]["capture_note"] = extra_notes[s["id"]]

    total_material = sum(s["material_runs"] for s in scenarios)
    total_rhombus_ok = sum(s["rhombus_successes"] for s in scenarios)
    silent = [s for s in scenarios if s["capability"] == "missed"]
    true_pass = [s for s in scenarios if s["id"] == "00-baseline"]

    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "results/runs.csv + results/validation/*.json + outputs/*.csv + observations/",
        "pipeline": "Data Input → Custom (clean_orders) → Data Output (gs://rhombus-target)",
        "code_sha_original": "3ca80b148200",
        "suites": {
            "ui": {"pass": 5, "total": 8, "note": "5 of 8 pass; S3 expected-failure not confirmed; 2 opt-in tests not run"},
            "api": {"pass": 16, "known_issues": 3, "total": 16, "note": "16 of 16 pass: 7 positive, 6 negative (security), 3 known issues confirmed still present (F10, F15, F30)"},
        },
        "kpis": {
            "scenarios": len(scenarios),
            "runner_rows": len(run_rows),
            "captured_outputs": len(outputs),
            "rhombus_success_rate": round(100 * total_rhombus_ok / total_material, 1) if total_material else None,
            "silent_fail_scenarios": len(silent),
            "true_clean_pass": len(true_pass),
            "median_success_seconds": None,
        },
        "scenarios": scenarios,
        "runs": run_rows,
        "videos": collect_videos(),
        "heat": [
            {
                "id": s["id"],
                "label": s["label"],
                "group": s["group"],
                "capability": s["capability"],
                "headline": s["headline"],
                "stops": s["capability"] in ("handled", "breaks") and s["id"] != "00-baseline",
                "silent_success": s["capability"] in ("missed", "silent_drop") or s["id"] == "01-schema-drop-column",
                "data_correct": s["id"] in ("00-baseline", "04-schema-add-column") or (
                    s["id"] == "03-schema-type-change" and False
                ),
                "validator_caught": s["id"] not in ("00-baseline", "02-schema-rename-column", "05-schema-combined"),
            }
            for s in scenarios
        ],
    }
    success_times = [t for s in scenarios for t in s["times_to_output"]]
    if success_times:
        payload["kpis"]["median_success_seconds"] = sorted(success_times)[len(success_times) // 2]

    # Fix heat data_correct from verdicts
    for cell, scen in zip(payload["heat"], scenarios):
        cell["data_correct"] = scen["latest_verdict"] in ("PASS", "PASS (with warnings)") and scen["id"] != "01-schema-drop-column"
        if scen["id"] == "04-schema-add-column":
            cell["data_correct"] = True  # values correct; column dropped
            cell["silent_success"] = True
        if scen["id"] == "01-schema-drop-column":
            cell["data_correct"] = False
            cell["stops"] = True
        if scen["id"] == "03-schema-type-change":
            cell["data_correct"] = False  # default/failing behaviour; run 6 is a later patch
            cell["silent_success"] = True
            cell["patched_later"] = True
        if scen["id"] == "00-baseline":
            cell["silent_success"] = False
            cell["stops"] = None
            cell["data_correct"] = True
            cell["validator_caught"] = False

    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()