# Scenarios 1 and 2 — product or consulting?

Run **10 and 13 November 2026**. These two scenarios exist to answer **one**
question, and they answered it.

> See also [`legacy-demo/RESULTS.md`](../legacy-demo/RESULTS.md) — scenario 3,
> where two independent programs produced the outputs and nobody seeded any
> differences. That one is stronger evidence than either of these.

---

## The question

> When comparing batch output before and after a migration, how much of the work
> is **plumbing** (reading files, matching records, printing a report) and how
> much is **classifying** differences?
>
> If classification dominates and needs different rules per customer, this is
> **consulting**. If it is small and reusable, it is a **product**.

---

## Scenario 1 — the bug is in the money

A daily interest accrual job, **2,000 accounts**, fixed-width report — the most
common shape of batch job still running in the wild.

Four differences injected into the "after" file, all taken from real migration
failures:

| # | Difference | Scale | Nature |
|---|---|---|---|
| 1 | COBOL **truncates**, Java **rounds** | 2,026 fields | harmless, but needs sign-off |
| 2 | The new system writes records sorted | all 2,000 lines | harmless |
| 3 | Run timestamp in the header | 1 line | harmless |
| 4 | **`UNTIL` translated as `while`** → one extra day of interest | **4 accounts** | **money is wrong, blocks go-live** |

Defect 4 only touches accounts maturing exactly on the boundary. That is the
real shape of a migration bug: not wrong everywhere, wrong in a small group,
quietly.

### Result

```
diff legacy modern              → 3,874 changed lines
sort both first, then diff      → 2,036 changed lines
```

Four genuinely wrong accounts buried in two thousand lines of noise. This is
precisely why parallel runs drag on for years: nobody can read all of it, and
nobody dares say which differences are fine.

```
DO NOT SHIP — 12 differences need a decision, across 4 records

  BUSINESS LOGIC CHANGED         12  ← blocks
  Rounding / representation    2026

  field `accrual_days`: 4 records
  ACC0000901  accrual_days: 365 -> 366   (integer off by 1)
```

**All four found. No misses, no false positives.** Exit code 1 — usable as a CI
gate. From 2,036 lines to read down to 4 accounts to decide on.

### The finding that was not planned

The rounding tolerance **should have hidden** two of the real defects: they move
the money column by only `0.08` and `0.02` — one extra day of interest on a small
balance. Looking at money alone, they are indistinguishable from the 2,026 benign
rounding differences.

They were caught by `accrual_days` — **an integer off by exactly 1**.

> **Don't look for the wrong money. Look for the wrong reason.**
>
> Money is an output, and outputs have natural tolerance to hide behind. Day
> counts, status flags, loop counters and tier codes are *causes*, and they have
> **no tolerance at all**. An integer off by one is always something.

This argument was not designed in advance; it fell out of the data. It is also
the thesis the whole product rests on.

---

## Scenario 2 — breaking the conclusion on purpose

One scenario proves nothing, so the second was built to break the first.
Deliberately different in four ways:

| | Scenario 1 | Scenario 2 |
|---|---|---|
| File format | fixed width | **pipe-delimited** |
| Join key | one field | **two fields** |
| Real defect in | an amount | **a status code (string)** |
| Missing records | no | **yes** |

An insurance adjudication job, 1,500 rows. Two real defects: **15 rows** written
`DN` (denied) instead of `PD` (partially denied) — *the money is correct to the
cent, only the reason is wrong*, which no amount-reconciliation tool catches —
plus **10 rows dropped** because a filter condition `>` was translated as `>=`.

### First run — a failure, and the useful part

```
DO NOT SHIP — 4500 differences, across 1500 records
  field `service_date`: 1500 records      ← false positive
  field `provider`:     1500 records      ← false positive
  field `adjudication`:   15 records      ← correct
```

**3,000 false positives.** Scenario 1's rules classified every string difference
as a business error, so a date reformatted from `2026-06-03` to `03/06/2026` and
a provider name upper-cased both looked like money was wrong. As useless as
`diff`.

The decisive question was never "do the rules need changing" but **"do they need
changing *per customer*"**. Two fixes, both generic:

1. **Dates** parse into `date` regardless of notation — a *plumbing* concern.
   Two spellings of one date are not two values.
2. **Strings** equal after trimming and case-folding get a new `FORMATTING`
   class — reported, not blocking.

Neither rule mentions insurance, providers or adjudication codes.

### Second run

```
DO NOT SHIP — 25 differences, across 25 records
  BUSINESS LOGIC CHANGED   15  ← blocks
  RECORDS MISSING          10  ← blocks
```

**15 + 10 = exactly 25, matching the injected defects.** No misses, no false
positives. Scenario 1 still returns the same 4 records — the new rules did not
break the old ones. `diff` on the same pair: 2,992 lines.

---

## The answer: **product**

Lines of code, excluding blanks and comments:

| | Scenario 1 | After scenario 2 | Added |
|---|---|---|---|
| Plumbing | 141 | 158 | **+17** |
| Classification | 44 | 48 | **+4** |

Supporting a different file format, a two-field key, reformatted dates,
case-folded strings and **an entirely new class of defect** cost **21 lines, 4 of
them in classification. Customer-specific rules: zero.**

The classification rules are about **data types**, not business meaning:

- declared run-variable → ignore
- decimal within one representable unit → rounding
- decimal beyond that → business
- **any integer difference → business, no tolerance**
- string difference → business, unless equal after trim and case-fold

Nothing there mentions interest, insurance or banking. The only customer-specific
artefact is the **schema** — which they already have, because the legacy system
needed it to write the file.

---

## A risk this exposed

Date parsing tries formats in order, so `03/06/2026` resolves as 3 June. If the
new system writes US-style, that is 6 March, and the tool would **silently pass
a real defect**.

That is worse than a false positive: a false positive gets seen. Per-field
`formats` can be declared in the schema (done), and a production version must
**refuse to run** when a date field matches more than one plausible format
rather than guessing.

---

## Reproducing

```bash
cd spike
python3 generate.py  && python3 verify.py legacy_output.txt modern_output.txt schema.json  --lang=en
python3 generate2.py && python3 verify.py legacy2.txt       modern2.txt       schema2.json --lang=en
echo $?   # 1 = something blocks
```

No dependencies. Standard-library Python.
