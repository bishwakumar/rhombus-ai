"""
Validates Rhombus AI pipeline outputs against the inputs that produced them.

Independent of Rhombus: it reads only local files.
  input     datasets/<case>.csv  (or dataset/)
  outputs   outputs/<case>__run<N>.csv        (saved by runner/run_cases.py)
  reference datasets/00-baseline.expected.csv (correct cleaned baseline)

Overall verdict per run:
  PASS                  every check passed
  PASS (with warnings)  nothing wrong with the values, but remarks worth reading (e.g. formatting)
  FAIL                  at least one check failed
  STOPPED               the pipeline produced no output (from results/runs.csv)

Checks, in the order they are reported (each gives PASS, WARN or FAIL):
  schema       expected columns present, no extras, same order; no input column silently dropped,
               renamed or recreated; no data in columns the input doesn't have (stale input)
  freshness    a drift case's output is not identical to the baseline's or another case's (stale input)
  rows         every unique input order_id appears exactly once
  correct      every value matches the true answer: the baseline's expected output, blank only where
               the case input no longer has the data. This is the test oracle
  rules        each original cleaning rule applied, value by value. Formatting-only differences are
               WARN; wrong values FAIL, unless every value is correct (rules changed, e.g. by a fix)
  blanks       no column loses far more values than in the baseline (columns the input no longer
               has are excluded)
  semantics    amounts and dates within the ranges the data should have (cents, day/month swaps)
  determinism  every run of the same case produced identical output (WARN if not: the code may
               have changed between runs)

Runs that produced no output (pipeline stopped in Rhombus) are read from results/runs.csv and
recorded as STOPPED, with the Rhombus error, so every run has a validation record.

Writes results/validation/<case>__run<N>.json, appends results/validation/summary.csv,
and exits with code 1 if any check FAILs.

Usage:
  python3 data-validation/validate.py 00-baseline           # all saved runs of one case
  python3 data-validation/validate.py --all                 # every case with outputs or runs
  python3 data-validation/validate.py 06-semantic-cents --run 2
"""
import argparse
import csv
import hashlib
import json
import math
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = next((ROOT / d for d in ("dataset", "datasets") if (ROOT / d).is_dir()), ROOT / "dataset")
OUTPUTS = ROOT / "outputs"
RESULTS = ROOT / "results" / "validation"
REFERENCE = DATASET_DIR / "00-baseline.expected.csv"
RUNS_LOG = ROOT / "results" / "runs.csv"

EXPECTED_COLUMNS = ["order_id", "customer_name", "email", "order_date",
                    "amount_usd", "quantity", "country", "status"]
RULE_COLUMNS = EXPECTED_COLUMNS[1:]

# Ranges the clean data must fall in (from the baseline answer key)
AMOUNT_MAX = 2500.00                      # baseline max is about $2,000
DATE_MIN, DATE_MAX = date(2026, 1, 1), date(2026, 3, 31)
BLANK_INCREASE_FAIL = 20.0                # percentage points above baseline
OUT_OF_RANGE_FAIL = 1.0                   # percent of non-blank values

PASS, WARN, FAIL, STOPPED = "PASS", "WARN", "FAIL", "STOPPED"
PASS_WARN = "PASS (with warnings)"      # overall verdict: passed, but with remarks worth reading


# ---------------------------------------------------------------- reading
def read_csv(path):
    """Columns and rows. Missing trailing fields become "", extra fields are dropped,
    so a malformed row can't crash a check."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = [{k: (v if v is not None else "") for k, v in r.items() if k is not None} for r in reader]
        return list(reader.fieldnames or []), rows


def md5(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


# ------------------------------------------- independent reference cleaning
# Written from the rule list, not copied from the Rhombus-generated code.
WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
         "eight": 8, "nine": 9, "ten": 10}
COUNTRIES = {
    "Australia": ["au", "aus", "australia"],
    "United States": ["us", "usa", "u.s.", "u.s.a.", "united states"],
    "United Kingdom": ["uk", "gb", "great britain", "united kingdom"],
    "New Zealand": ["nz", "new zealand"],
    "India": ["in", "india"],
}
COUNTRY_MAP = {v: k for k, vs in COUNTRIES.items() for v in vs}
STATUSES = {"shipped", "delivered", "pending", "cancelled"}


def clean_name(s):
    return s.strip().title()


def clean_email(s):
    s = s.strip().lower()
    return s if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", s) else ""


def clean_date(s):
    for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%B %d %Y", "%d %B %Y"):
        try:
            return datetime.strptime(s.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""


def clean_amount(s):
    t = re.sub(r"(?i)usd", "", s).replace("$", "").replace(",", "").strip()
    try:
        v = float(t)
    except ValueError:
        return ""
    return "" if v < 0 else f"{v:.2f}"


def clean_quantity(s):
    s = s.strip().lower()
    if s in WORDS:
        return str(WORDS[s])
    try:
        v = float(s)
    except ValueError:
        return ""
    return str(int(v)) if v > 0 and v == int(v) else ""


def clean_country(s):
    s = s.strip()
    return COUNTRY_MAP.get(s.lower(), s)


def clean_status(s):
    s = s.strip().lower()
    return s if s in STATUSES else ""


CLEANERS = {"customer_name": clean_name, "email": clean_email, "order_date": clean_date,
            "amount_usd": clean_amount, "quantity": clean_quantity,
            "country": clean_country, "status": clean_status}


def reference_clean(cols, rows):
    """Dedupe (exact, then first per order_id) and apply the rules to whatever columns exist."""
    seen_rows, seen_ids, out = set(), set(), []
    for r in rows:
        key = tuple(r.get(c, "") for c in cols)
        if key in seen_rows:
            continue
        seen_rows.add(key)
        oid = r.get("order_id", "")
        if oid in seen_ids:
            continue
        seen_ids.add(oid)
        out.append({c: CLEANERS[c](r[c]) if c in CLEANERS else r[c] for c in cols})
    return out


# ---------------------------------------------------------------- checks
def check(name, status, detail, **data):
    return {"check": name, "status": status, "detail": detail, **data}


def same_number(a, b):
    try:
        return float(a) == float(b)
    except (TypeError, ValueError):
        return False


def check_schema(in_cols, out_cols, out_rows):
    missing = [c for c in EXPECTED_COLUMNS if c not in out_cols]
    extra = [c for c in out_cols if c not in EXPECTED_COLUMNS]
    dropped = [c for c in in_cols if c not in out_cols]       # in the input, gone from the output
    invented = [c for c in out_cols if c not in in_cols]      # in the output, never in the input
    data = dict(missing=missing, extra=extra, dropped_from_input=dropped, not_in_input=invented)
    if missing:
        return check("schema", FAIL, f"Missing columns: {', '.join(missing)}"
                     + (f"; unexpected columns: {', '.join(extra)}" if extra else ""), **data)
    filled = {c: sum(1 for r in out_rows if r.get(c, "").strip()) for c in invented}
    filled = {c: n for c, n in filled.items() if n}
    if filled:
        desc = ", ".join(f"{c} ({n} values)" for c, n in filled.items())
        return check("schema", FAIL, f"Output contains data for columns that are not in the input: {desc}; "
                     "the output may come from old or cached data", populated_columns=filled, **data)
    notes = []
    if extra:
        notes.append(f"unexpected extra columns passed through: {', '.join(extra)}")
    if dropped:
        notes.append(f"input columns silently dropped: {', '.join(dropped)}")
    if invented:
        notes.append(f"output columns not in the input (renamed or recreated?): {', '.join(invented)}")
    if out_cols != EXPECTED_COLUMNS and not extra:
        notes.append("columns in a different order")
    if notes:
        text = "; ".join(notes)
        return check("schema", WARN, text[:1].upper() + text[1:], **data)
    return check("schema", PASS, "All 8 expected columns, correct order, matches input", **data)


def check_rows(in_rows, out_rows):
    in_ids = list(dict.fromkeys(r.get("order_id", "") for r in in_rows))
    out_ids = [r.get("order_id", "") for r in out_rows]
    out_set = set(out_ids)
    missing = [i for i in in_ids if i not in out_set]
    dupes = sorted({i for i in out_ids if out_ids.count(i) > 1})
    unknown = sorted(set(out_ids) - set(in_ids))
    detail = f"input {len(in_rows)} rows ({len(in_ids)} unique orders), output {len(out_rows)} rows"
    data = dict(input_rows=len(in_rows), unique_orders=len(in_ids), output_rows=len(out_rows),
                missing_order_ids=missing[:20], duplicate_order_ids=dupes[:20])
    if missing or dupes or unknown:
        parts = [f"{len(missing)} orders missing"] if missing else []
        parts += [f"{len(dupes)} order_ids duplicated"] if dupes else []
        parts += [f"{len(unknown)} unknown order_ids"] if unknown else []
        return check("rows", FAIL, f"{detail}; " + ", ".join(parts), **data)
    return check("rows", PASS, f"{detail}; every order present once", **data)


def check_rules(in_cols, in_rows, out_cols, out_rows):
    expected = {r["order_id"]: r for r in reference_clean(in_cols, in_rows)}
    actual = {r.get("order_id"): r for r in out_rows}
    results, worst = {}, PASS
    for col in RULE_COLUMNS:
        if col not in in_cols or col not in out_cols:
            results[col] = {"skipped": "column not in both input and output"}
            continue
        correct = fmt = wrong = 0
        examples = []
        for oid, exp in expected.items():
            if oid not in actual:
                continue
            e, a = exp[col], actual[oid].get(col, "")
            if e == a:
                correct += 1
            elif e and a and same_number(e, a):
                fmt += 1
                if len(examples) < 3:
                    examples.append({"order_id": oid, "expected": e, "actual": a, "type": "format"})
            else:
                wrong += 1
                if len(examples) < 6:
                    examples.append({"order_id": oid, "expected": e, "actual": a, "type": "wrong"})
        results[col] = {"correct": correct, "format_only": fmt, "wrong": wrong, "examples": examples}
        if wrong:
            worst = FAIL
        elif fmt and worst == PASS:
            worst = WARN
    bad = [f"{c}: {v['wrong']} wrong" for c, v in results.items() if v.get("wrong")]
    fmts = [f"{c}: {v['format_only']} format-only" for c, v in results.items() if v.get("format_only")]
    detail = "; ".join(bad + fmts) or "All checked values match the cleaning rules"
    return check("rules", worst, detail, columns=results)


def blank_pct(rows, col):
    vals = [r.get(col, "") for r in rows]
    return round(100 * sum(1 for v in vals if v.strip() == "") / len(vals), 1) if vals else 0.0


def check_blanks(out_cols, out_rows, ref_rows, lost=()):
    issues, pct = [], {}
    for col in RULE_COLUMNS:
        if col not in out_cols or col in lost:
            continue
        now, base = blank_pct(out_rows, col), blank_pct(ref_rows, col)
        pct[col] = {"output": now, "baseline": base}
        if now - base > BLANK_INCREASE_FAIL:
            issues.append(f"{col} {now}% blank (baseline {base}%)")
    if issues:
        return check("blanks", FAIL, "Unexpected data loss: " + "; ".join(issues), blank_percent=pct)
    return check("blanks", PASS, "Blank rates in line with the baseline", blank_percent=pct)


def check_semantics(out_cols, out_rows):
    problems, data = [], {}
    if "amount_usd" in out_cols:
        vals = [float(v) for v in (r["amount_usd"] for r in out_rows) if _is_num(v)]
        high = [v for v in vals if v > AMOUNT_MAX]
        data["amount"] = {"count": len(vals), "max": max(vals, default=None), "above_limit": len(high)}
        if vals and 100 * len(high) / len(vals) > OUT_OF_RANGE_FAIL:
            problems.append(f"{len(high)} of {len(vals)} amounts above ${AMOUNT_MAX:,.0f} "
                            f"(max {max(vals):,.2f}); possible unit change such as cents")
    if "order_date" in out_cols:
        dates = [d for d in (_to_date(r["order_date"]) for r in out_rows) if d]
        outside = [d for d in dates if not DATE_MIN <= d <= DATE_MAX]
        future = [d for d in dates if d > datetime.now(timezone.utc).date()]
        months = sorted({d.month for d in dates})
        data["order_date"] = {"count": len(dates), "outside_window": len(outside),
                              "in_future": len(future), "months_seen": months}
        if dates and 100 * len(outside) / len(dates) > OUT_OF_RANGE_FAIL:
            problems.append(f"{len(outside)} of {len(dates)} dates outside "
                            f"{DATE_MIN}–{DATE_MAX} (months seen: {months}); "
                            "possible day/month swap")
    if problems:
        return check("semantics", FAIL, "; ".join(problems), **data)
    return check("semantics", PASS, "Amounts and dates within expected ranges", **data)


def _is_num(v):
    try:
        return math.isfinite(float(v))
    except (TypeError, ValueError):
        return False


def _to_date(v):
    try:
        return datetime.strptime(v.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


# Cases whose correct output is identical to the baseline output (the drift is removed by the
# cleaning step), so matching the baseline is expected rather than a sign of stale input.
SAME_AS_BASELINE_EXPECTED = {"04-schema-add-column"}
BASELINE = "00-baseline"


def check_freshness(case_id, out_file):
    """A drift case whose output is identical to the baseline output (or to another case's earlier
    output) probably never read its own input. The baseline is the reference, so it is not checked."""
    if case_id == BASELINE:
        return check("freshness", PASS, "Baseline is the reference output; not checked", identical_to=[])
    mine = md5(out_file)
    base_twins = sorted(f.name for f in OUTPUTS.glob(f"{BASELINE}__run*.csv") if md5(f) == mine)
    my_time = out_file.stat().st_mtime
    other_twins = sorted(f.name for f in OUTPUTS.glob("*__run*.csv")
                         if f.stem.split("__run")[0] not in (case_id, BASELINE)
                         and f.stat().st_mtime < my_time and md5(f) == mine)
    in_cols, _ = read_csv(DATASET_DIR / f"{case_id}.csv")
    _, lost = truth_rows(in_cols)
    if base_twins and (case_id in SAME_AS_BASELINE_EXPECTED or not lost):
        # other outputs identical to it are simply baseline-equivalent too (e.g. a stale run)
        return check("freshness", WARN, "Identical to the baseline output. That is the correct result if the drift was "
                     "handled, but it also matches stale input: confirm from the Rhombus input preview",
                     identical_to=base_twins)
    twins = base_twins or other_twins
    if twins:
        return check("freshness", FAIL, f"Byte-identical to {', '.join(twins[:3])}"
                     + (" …" if len(twins) > 3 else "") + "; the pipeline probably did not read this case's input",
                     identical_to=twins)
    return check("freshness", PASS, "Output differs from the baseline and every other case's output", identical_to=[])


def check_determinism(case_id, files):
    if len(files) < 2:
        return check("determinism", PASS, "Only one run; nothing to compare", runs=len(files))
    hashes = {f.name: md5(f) for f in files}
    identical = len(set(hashes.values())) == 1
    if identical:
        return check("determinism", PASS, f"All {len(files)} runs byte-identical", runs=len(files), md5=hashes)
    _, base = read_csv(files[0])
    diffs = {}
    for f in files[1:]:
        _, other = read_csv(f)
        n = sum(1 for a, b in zip(base, other) for k in a if a.get(k) != b.get(k))
        diffs[f.name] = n + abs(len(base) - len(other))
    return check("determinism", WARN, f"Runs differ from {files[0].name}: {diffs} "
                 "(expected if the pipeline code changed between runs, e.g. after a chatbot fix)",
                 runs=len(files), md5=hashes, cell_differences=diffs)


# ---------------------------------------------------------------- correctness against the truth
# Every drift case carries the same orders as the baseline. So the *correct* cleaned output is the
# baseline's expected output, except for information the case input genuinely no longer has.
RENAMED_FROM = {"amount_usd": ["amount_usd", "total_amount"]}   # where each column's data can come from


def truth_rows(in_cols):
    """Correct cleaned values for this case: the baseline answer, blank where the input lost the data."""
    _, ref = read_csv(REFERENCE)
    lost = [c for c in RULE_COLUMNS if not any(src in in_cols for src in RENAMED_FROM.get(c, [c]))]
    rows = {}
    for r in ref:
        r = dict(r)
        for c in lost:
            r[c] = ""
        rows[r["order_id"]] = r
    return rows, lost


def check_correctness(in_cols, out_cols, out_rows):
    truth, lost = truth_rows(in_cols)
    actual = {r.get("order_id"): r for r in out_rows}
    cols, worst = {}, PASS
    for col in RULE_COLUMNS:
        if col not in out_cols:
            cols[col] = {"skipped": "column missing from output"}
            continue
        ok = fmt = wrong = 0
        examples = []
        for oid, t in truth.items():
            if oid not in actual:
                continue
            e, a = t[col], actual[oid].get(col, "")
            if e == a:
                ok += 1
            elif e and a and same_number(e, a):
                fmt += 1
            else:
                wrong += 1
                if len(examples) < 6:
                    examples.append({"order_id": oid, "correct": e, "actual": a})
        cols[col] = {"correct": ok, "format_only": fmt, "wrong": wrong, "examples": examples}
        if wrong:
            worst = FAIL
        elif fmt and worst == PASS:
            worst = WARN
    bad = [f"{c}: {v['wrong']} wrong" for c, v in cols.items() if v.get("wrong")]
    fmts = [f"{c}: {v['format_only']} format-only" for c, v in cols.items() if v.get("format_only")]
    note = f" (not recoverable from this input: {', '.join(lost)})" if lost else ""
    detail = ("; ".join(bad + fmts) or "Every value matches the correct answer") + note
    return check("correct", worst, detail, columns=cols, not_recoverable=lost)


# ---------------------------------------------------------------- stopped runs
def stopped_runs(case_id, run=None):
    """Runs in runs.csv that produced no output (pipeline stopped, bucket error, aborted...)."""
    if not RUNS_LOG.exists():
        return []
    with open(RUNS_LOG, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r.get("case_id") == case_id]
    rows = [r for r in rows if not r.get("local_copy") and r.get("status") != "started"]
    if run is not None:
        rows = [r for r in rows if str(r.get("run")) == str(run)]
    seen = {}
    for r in rows:                              # older logs can repeat the same run ID
        rid = r.get("run_id") or "legacy"
        seen[rid] = seen.get(rid, 0) + 1
        if seen[rid] > 1:
            r["run_id"] = f"{rid}-{seen[rid]}"
    return rows


def stopped_result(case_id, r):
    status = r.get("status", "")
    rid = r.get("run_id", "") or "legacy"
    if r.get("rhombus_error"):
        cause = f"Rhombus error: {r['rhombus_error']}"
    else:
        cause = "no Rhombus error recorded" + (f" (runner note: {r.get('error') or r.get('notes')})"
                                               if (r.get("error") or r.get("notes")) else "")
    if status in ("bucket_error", "runner_error"):
        detail = f"Test infrastructure problem ({status}): {r.get('error', '')}; not a Rhombus result, rerun the case"
    else:
        detail = f"Pipeline produced no output ({status}); {cause}"
    return {"case_id": case_id, "output_file": f"{case_id}__run{r.get('run')}__{rid}",
            "output_md5": "", "validated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "verdict": STOPPED, "run_status": status, "rhombus_error": r.get("rhombus_error", ""),
            "checks": [check("pipeline", STOPPED, detail, run_id=rid, triggered_at=r.get("triggered_at", ""))]}


# ---------------------------------------------------------------- runner
def run_files(case_id, run=None):
    files = [p for p in OUTPUTS.glob(f"{case_id}__run*.csv") if p.stem.split("__run")[-1].isdigit()]
    files.sort(key=lambda p: int(p.stem.split("__run")[-1]))
    return [f for f in files if run is None or f.stem.endswith(f"__run{run}")]


def validate(case_id, out_file, all_runs):
    in_cols, in_rows = read_csv(DATASET_DIR / f"{case_id}.csv")
    out_cols, out_rows = read_csv(out_file)
    _, ref_rows = read_csv(REFERENCE)
    correct = check_correctness(in_cols, out_cols, out_rows)
    rules = check_rules(in_cols, in_rows, out_cols, out_rows)
    if rules["status"] == FAIL and correct["status"] != FAIL:
        # the values are right but differ from the original rules: the rules were changed (e.g. by a chatbot fix)
        rules["status"] = WARN
        rules["detail"] = "Differs from the original rules, but every value is correct (rules were changed): " + rules["detail"]
    checks = [check_schema(in_cols, out_cols, out_rows), check_freshness(case_id, out_file), check_rows(in_rows, out_rows),
              correct, rules, check_blanks(out_cols, out_rows, ref_rows, correct["not_recoverable"]),
              check_semantics(out_cols, out_rows),
              check_determinism(case_id, all_runs)]
    statuses = [c["status"] for c in checks]
    verdict = FAIL if FAIL in statuses else PASS_WARN if WARN in statuses else PASS
    return {"case_id": case_id, "output_file": out_file.name, "output_md5": md5(out_file),
            "validated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "verdict": verdict, "checks": checks}


def save(result):
    RESULTS.mkdir(parents=True, exist_ok=True)
    stem = Path(result["output_file"]).stem
    (RESULTS / f"{stem}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    summary = RESULTS / "summary.csv"
    cols = ["validated_at", "case_id", "output_file", "verdict", "pipeline", "schema", "freshness",
            "rows", "correct", "rules", "blanks", "semantics", "determinism", "detail"]
    status = {c["check"]: c["status"] for c in result["checks"]}
    status.setdefault("pipeline", "RAN")
    problems = "; ".join(f"{c['check']}: {c['detail']}" for c in result["checks"] if c["status"] != PASS)
    row = {"validated_at": result["validated_at"], "case_id": result["case_id"],
           "output_file": result["output_file"], "verdict": result["verdict"], "detail": problems, **status}
    new = not summary.exists()
    with open(summary, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)


ICON = {PASS: "✔", PASS_WARN: "✔", WARN: "⚠", FAIL: "✘", STOPPED: "⏹"}


def report(result):
    print(f"\n{ICON[result['verdict']]} {result['output_file']}: {result['verdict']}")
    for c in result["checks"]:
        label = "warning" if c["status"] == WARN else ""
        print(f"   {ICON[c['status']]} {c['check']:<12} {('[' + label + '] ') if label else ''}{c['detail']}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("case", nargs="?", help="case ID, e.g. 00-baseline")
    p.add_argument("--run", type=int, help="validate only this run number")
    p.add_argument("--all", action="store_true", help="validate every case that has outputs")
    args = p.parse_args()

    if args.all:
        cases = {f.stem.split("__run")[0] for f in OUTPUTS.glob("*__run*.csv")
                 if f.stem.split("__run")[-1].isdigit()}
        if RUNS_LOG.exists():
            with open(RUNS_LOG, newline="", encoding="utf-8") as f:
                cases |= {r["case_id"] for r in csv.DictReader(f) if r.get("case_id")}
        cases = sorted(cases)
    elif args.case:
        cases = [args.case]
    else:
        p.error("give a case ID or --all")

    if args.all and (RESULTS / "summary.csv").exists():
        (RESULTS / "summary.csv").unlink()          # rebuilt from scratch, so no stale rows remain
    any_fail = False
    tally = {PASS: 0, PASS_WARN: 0, FAIL: 0, STOPPED: 0}
    for case_id in cases:
        if not (DATASET_DIR / f"{case_id}.csv").exists():
            print(f"✘ {case_id}: no input file at {DATASET_DIR / (case_id + '.csv')}")
            any_fail = True
            continue
        all_runs = run_files(case_id)
        targets = run_files(case_id, args.run)
        stopped = stopped_runs(case_id, args.run)
        for r in stopped:                       # runs that never produced an output
            result = stopped_result(case_id, r)
            save(result)
            report(result)
            tally[STOPPED] += 1
        if not targets and not stopped:
            print(f"✘ {case_id}: no outputs in {OUTPUTS} and no runs in {RUNS_LOG.relative_to(ROOT)}")
            any_fail = True
            continue
        for out_file in targets:
            result = validate(case_id, out_file, all_runs)
            save(result)
            report(result)
            tally[result["verdict"]] += 1
            any_fail |= result["verdict"] == FAIL

    passed = tally[PASS] + tally[PASS_WARN]
    print(f"\nPassed: {passed} ({tally[PASS_WARN]} with warnings)   Failed: {tally[FAIL]}   "
          f"Stopped (no output): {tally[STOPPED]}")
    print(f"Results saved in {RESULTS.relative_to(ROOT)}/")
    sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()