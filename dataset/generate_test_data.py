"""
Generates the v2 test dataset for the Rhombus AI ETL assignment.
500 source rows, visible defects, duplicates placed right after their original,
plus an expected cleaned output for side-by-side comparison.
Deterministic: fixed seed, so anyone can regenerate identical files.

Usage: python generate_test_data.py
"""
import csv, os, random
from collections import Counter
from datetime import date, datetime, timezone

SEED = 2026
N_UNIQUE = 470
N_EXACT_DUPES = 20
N_CONFLICT_DUPES = 10          # 470 + 20 + 10 = 500 source rows
OUT = os.path.dirname(os.path.abspath(__file__))
rng = random.Random(SEED)
defects = Counter()

FIRST = ["James","Olivia","Liam","Emma","Noah","Ava","William","Sophia","Jack","Mia","Lucas","Isla","Henry",
         "Grace","Oscar","Chloe","Leo","Ruby","Thomas","Zoe","Priya","Arjun","Wei","Mei","Hiroshi","Yuki",
         "Mohammed","Fatima","Carlos","Lucia","Ethan","Harper","Daniel","Amelia","Samuel","Ella"]
LAST = ["Smith","Jones","Williams","Brown","Wilson","Taylor","Nguyen","Johnson","Martin","White","Anderson",
        "Walker","Thompson","Patel","Singh","Chen","Wang","Tanaka","Kim","Garcia","Lopez","Ali","Khan","Kelly",
        "Murphy","Rossi","Silva","Cohen","Novak","Larsen"]
# (canonical, [variants]) - first variant is the canonical name
COUNTRIES = {
    "Australia": ["Australia", "AU", "AUS", "aus", "australia", "AUSTRALIA"],
    "United States": ["United States", "US", "USA", "usa", "U.S.", "U.S.A."],
    "United Kingdom": ["United Kingdom", "UK", "GB", "uk", "Great Britain"],
    "New Zealand": ["New Zealand", "NZ", "nz", "NEW ZEALAND"],
    "India": ["India", "IN", "INDIA", "india"],
}
STATUSES = ["shipped", "delivered", "pending", "cancelled"]
WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}

def pick(table):
    """table: list of (probability, label). Returns a label, or None for the remainder."""
    r, acc = rng.random(), 0.0
    for p, label in table:
        acc += p
        if r < acc:
            return label
    return None

def messy_name(first, last):
    full = f"{first} {last}"
    k = pick([(0.25, "upper"), (0.15, "lower"), (0.10, "mixed"), (0.06, "spaces"), (0.03, "missing")])
    if k: defects[f"customer_name: {dict(upper='ALL CAPS', lower='all lower case', mixed='mixed case (PRIYA khan)', spaces='leading/trailing spaces', missing='missing')[k]}"] += 1
    return {"upper": full.upper(), "lower": full.lower(), "mixed": f"{first.upper()} {last.lower()}",
            "spaces": f"   {full}  ", "missing": "", None: full}[k]

def messy_email(first, last, oid):
    clean = f"{first.lower()}.{last.lower()}{oid % 89}@example.com"
    k = pick([(0.06, "missing"), (0.06, "placeholder"), (0.08, "invalid"), (0.15, "upper")])
    if k: defects[f"email: {dict(missing='missing', placeholder='placeholder (n/a, none, -)', invalid='invalid format', upper='UPPER CASE')[k]}"] += 1
    if k == "missing": return ""
    if k == "placeholder": return rng.choice(["n/a", "none", "-", "N/A"])
    if k == "invalid": return rng.choice([clean.split("@")[0] + "@", clean.replace("@", "_at_"),
                                          clean.replace(".com", ""), "@example.com"])
    if k == "upper": return clean.upper()
    return clean

def messy_date(d):
    k = pick([(0.05, "missing"), (0.04, "invalid"), (0.15, "iso"), (0.15, "text"), (0.10, "us_dash")])
    if k == "missing":
        defects["order_date: missing"] += 1; return "", "missing"
    if k == "invalid":
        defects["order_date: invalid (13/45/2026, TBD, 2026-02-30)"] += 1
        return rng.choice(["13/45/2026", "TBD", "00/00/0000", "2026-02-30", "not known"]), "invalid"
    if k == "iso":
        defects["order_date: already ISO (YYYY-MM-DD)"] += 1; return d.isoformat(), "iso"
    if k == "text":
        defects["order_date: text (March 4 2026)"] += 1
        return f"{d.strftime('%B')} {d.day} {d.year}", "text"
    if k == "us_dash":
        defects["order_date: MM-DD-YYYY"] += 1; return d.strftime("%m-%d-%Y"), "us_dash"
    defects["order_date: MM/DD/YYYY"] += 1
    return d.strftime("%m/%d/%Y"), "us"

def fmt_amount(v, style):
    return {"plain": f"{v:.2f}", "short": f"{v:g}", "dollar": f"${v:,.2f}",
            "dollar_space": f"$ {v:.2f}", "usd": f"{v:.2f} USD"}[style]

def messy_amount(v):
    k = pick([(0.04, "missing"), (0.04, "invalid"), (0.04, "negative"), (0.25, "dollar"),
              (0.08, "dollar_space"), (0.08, "usd"), (0.10, "short")])
    if k == "missing":
        defects["amount_usd: missing"] += 1; return "", "missing"
    if k == "invalid":
        defects["amount_usd: non-numeric (abc, N/A, free, TBC)"] += 1
        return rng.choice(["abc", "N/A", "free", "TBC"]), "invalid"
    if k == "negative":
        defects["amount_usd: negative"] += 1; return fmt_amount(-v, "plain"), "plain"
    if k == "dollar":
        defects["amount_usd: $ and commas ($1,540.73)"] += 1; return fmt_amount(v, "dollar"), "dollar"
    if k == "dollar_space":
        defects["amount_usd: '$ ' prefix ($ 403.03)"] += 1; return fmt_amount(v, "dollar_space"), "dollar_space"
    if k == "usd":
        defects["amount_usd: USD suffix (403.03 USD)"] += 1; return fmt_amount(v, "usd"), "usd"
    if k == "short":
        defects["amount_usd: fewer than 2 decimals (403.5, 120)"] += 1; return fmt_amount(v, "short"), "short"
    return fmt_amount(v, "plain"), "plain"

def messy_quantity(q):
    k = pick([(0.04, "missing"), (0.12, "word"), (0.05, "zero_neg"), (0.06, "dot_zero"), (0.02, "fraction")])
    if k: defects[f"quantity: {dict(missing='missing', word='number word (three)', zero_neg='zero or negative', dot_zero='decimal like 2.0', fraction='fraction like 1.5')[k]}"] += 1
    return {"missing": "", "word": WORDS[q], "zero_neg": rng.choice(["0", "-1", "-3"]),
            "dot_zero": f"{q}.0", "fraction": rng.choice(["1.5", "2.5"]), None: str(q)}[k]

def messy_country(c):
    if rng.random() < 0.03:
        defects["country: missing"] += 1; return ""
    v = rng.choice(COUNTRIES[c])
    if v != c: defects["country: abbreviation / variant (AU, USA, GB)"] += 1
    return v

def messy_status(s):
    k = pick([(0.25, "upper"), (0.15, "cap"), (0.05, "spaces"), (0.04, "invalid")])
    if k: defects[f"status: {dict(upper='UPPER CASE', cap='Capitalised', spaces='trailing spaces', invalid='invalid (xyz, ??, 1, unknown)')[k]}"] += 1
    return {"upper": s.upper(), "cap": s.capitalize(), "spaces": s + "   ",
            "invalid": rng.choice(["xyz", "??", "1", "unknown"]), None: s}[k]

# ---------------- build rows ----------------
rows = []
for i in range(N_UNIQUE):
    oid = 10001 + i
    first, last = rng.choice(FIRST), rng.choice(LAST)
    true_date = date(2026, rng.randint(1, 3), rng.randint(1, 12))   # day 1-12 so a day/month swap stays valid
    true_amount = round(rng.uniform(10, 2000), 2)
    true_qty = rng.randint(1, 6)
    country = rng.choices(list(COUNTRIES), weights=[35, 25, 15, 12, 13])[0]
    status = rng.choices(STATUSES, weights=[40, 35, 15, 10])[0]
    d_str, d_style = messy_date(true_date)
    a_str, a_style = messy_amount(true_amount)
    rows.append({"order_id": str(oid), "customer_name": messy_name(first, last),
                 "email": messy_email(first, last, oid), "order_date": d_str, "amount_usd": a_str,
                 "quantity": messy_quantity(true_qty), "country": messy_country(country),
                 "status": messy_status(status),
                 "_date": true_date, "_dstyle": d_style, "_amount": true_amount, "_astyle": a_style,
                 "_discount": rng.choice(["", "", "", "SPRING10", "WELCOME5", "VIP20", "FREESHIP"]),
                 "_dup": ""})

# duplicates go directly after their original, so they're easy to spot
exact_ids = set(rng.sample(range(N_UNIQUE), N_EXACT_DUPES))
conflict_ids = set(rng.sample(sorted(set(range(N_UNIQUE)) - exact_ids), N_CONFLICT_DUPES))
final = []
for i, r in enumerate(rows):
    final.append(r)
    if i in exact_ids:
        final.append(dict(r, _dup="exact"))
    if i in conflict_ids:
        d = dict(r, _dup="conflict")
        d["_amount"] = round(r["_amount"] * rng.uniform(0.5, 0.9), 2)
        d["amount_usd"], d["_astyle"] = fmt_amount(d["_amount"], "plain"), "plain"
        d["status"] = rng.choice([s for s in STATUSES if s != r["status"].strip().lower()])
        final.append(d)
defects["duplicate: exact copy of the previous row"] = N_EXACT_DUPES
defects["duplicate: same order_id as previous row, different amount/status"] = N_CONFLICT_DUPES
assert len(final) == 500

COLS = ["order_id", "customer_name", "email", "order_date", "amount_usd", "quantity", "country", "status"]

def write(name, cols, recs):
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(cols)
        for r in recs: w.writerow([r.get(c, "") for c in cols])

# ---------------- expected clean output (for side-by-side comparison) ----------------
import re
def c_email(s):
    s = s.strip().lower()
    return s if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", s) else ""
def c_date(s):
    for f in ("%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%B %d %Y"):
        try: return datetime.strptime(s.strip(), f).strftime("%Y-%m-%d")
        except ValueError: pass
    return ""
def c_amount(s):
    t = re.sub(r"(?i)usd", "", s).replace("$", "").replace(",", "").strip()
    try: v = float(t)
    except ValueError: return ""
    return "" if v < 0 else f"{v:.2f}"
def c_qty(s):
    s = s.strip().lower()
    inv = {v: k for k, v in WORDS.items()}
    if s in inv: return str(inv[s])
    try: v = float(s)
    except ValueError: return ""
    return str(int(v)) if v > 0 and v == int(v) else ""
CMAP = {v.lower(): k for k, vs in COUNTRIES.items() for v in vs}
def c_status(s):
    s = s.strip().lower(); return s if s in STATUSES else ""
expected = []
for r in final:
    if r["_dup"]: continue
    expected.append({"order_id": r["order_id"], "customer_name": r["customer_name"].strip().title(),
                     "email": c_email(r["email"]), "order_date": c_date(r["order_date"]),
                     "amount_usd": c_amount(r["amount_usd"]), "quantity": c_qty(r["quantity"]),
                     "country": CMAP.get(r["country"].strip().lower(), r["country"].strip()),
                     "status": c_status(r["status"])})
write("00-baseline.expected.csv", COLS, expected)

# ---------------- drift variants ----------------
def epoch(r):
    if r["_dstyle"] in ("missing", "invalid"): return ""
    d = r["_date"]; return str(int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp()))
def cents(r):
    st = r["_astyle"]
    if st in ("missing", "invalid"): return r["amount_usd"]
    neg = r["amount_usd"].strip().startswith("-")
    c = int(round(r["_amount"] * 100)) * (-1 if neg else 1)
    return {"dollar": f"${c:,}", "dollar_space": f"$ {c}", "usd": f"{c} USD"}.get(st, str(c))
def swap(r):
    d, st = r["_date"], r["_dstyle"]
    return d.strftime("%d/%m/%Y") if st == "us" else d.strftime("%d-%m-%Y") if st == "us_dash" else r["order_date"]

write("00-baseline.csv", COLS, final)
write("01-schema-drop-column.csv", [c for c in COLS if c != "email"], final)
write("02-schema-rename-column.csv", [("total_amount" if c == "amount_usd" else c) for c in COLS],
      [dict(r, total_amount=r["amount_usd"]) for r in final])
write("03-schema-type-change.csv", COLS, [dict(r, order_date=epoch(r)) for r in final])
write("04-schema-add-column.csv", COLS + ["discount_code"], [dict(r, discount_code=r["_discount"]) for r in final])
write("05-schema-combined.csv",
      ["order_id", "customer_name", "order_date", "total_amount", "quantity", "country", "status", "discount_code"],
      [dict(r, total_amount=r["amount_usd"], order_date=epoch(r), discount_code=r["_discount"]) for r in final])
write("06-semantic-cents.csv", COLS, [dict(r, amount_usd=cents(r)) for r in final])
write("07-semantic-date-swap.csv", COLS, [dict(r, order_date=swap(r)) for r in final])

# ---------------- answer key ----------------
valid = [r["_amount"] for r in final if r["_astyle"] not in ("missing", "invalid")]
swapped = sum(r["_dstyle"] in ("us", "us_dash") for r in final)
blank_epoch = sum(r["_dstyle"] in ("missing", "invalid") for r in final)
with open(os.path.join(OUT, "answer_key.md"), "w", encoding="utf-8") as f:
    f.write(f"# Answer key (seed {SEED})\n\n")
    f.write(f"- Source rows: **{len(final)}**\n- Unique orders: **{N_UNIQUE}**\n")
    f.write(f"- Expected cleaned rows: **{len(expected)}** (see `00-baseline.expected.csv`)\n")
    f.write("- True order dates: Jan 1 to Mar 12, 2026, day of month always 1-12. Slash and dash dates are month first.\n")
    f.write(f"- Valid amounts: ${min(valid):,.2f} to ${max(valid):,.2f}\n\n")
    f.write("## Planted defects (counted on unique rows, plus duplicates)\n\n| Column | Problem | Rows |\n|---|---|---|\n")
    for k in sorted(defects):
        col, prob = k.split(": ", 1); f.write(f"| {col} | {prob} | {defects[k]} |\n")
    f.write(f"\n## Drift details\n\n- 03-schema-type-change: {blank_epoch} rows with missing/invalid dates are blank (a timestamp column can't hold 'TBD').\n")
    f.write(f"- 06-semantic-cents: valid amounts become {int(min(valid)*100):,} to {int(max(valid)*100):,} (cents).\n")
    f.write(f"- 07-semantic-date-swap: {swapped} slash/dash dates swapped to day first; all still valid dates. Parsed months spread across Jan-Dec instead of Jan-Mar.\n")

print(len(final), len(expected), dict(defects))
