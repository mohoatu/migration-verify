# migration-verify

Prove a migration did not change the business logic — by comparing the output of
a batch job before and after, and classifying every single difference.

> **Status: a spike. No customers, no revenue.** Every number below was measured
> on data this repository generates. The limitations are written down in
> [`spike/RESULTS.md`](spike/RESULTS.md) and
> [`legacy-demo/RESULTS.md`](legacy-demo/RESULTS.md), not hidden.

---

## The problem

You rewrote a batch job — COBOL to Java, Perl to Python, a monolith into
services, Oracle to PostgreSQL. The new code runs. The question nobody can
answer is whether it still produces the same numbers.

So you run both systems in parallel and diff the output. And `diff` gives you
two thousand changed lines, because the new system rounds where the old one
truncated, writes records in a different order, and stamps a different run
timestamp. Somewhere in those two thousand lines there may be three records
where the money is genuinely wrong. Nobody can find them, and nobody wants to be
the person who signed off saying "those differences are fine".

## What this does

```
                     diff        this tool
scenario 1     3,874 lines   →   4 accounts, named
scenario 2     2,992 lines   →   25 records, named
scenario 3     2,402 lines   →   354 records, named
```

No misses and no false positives on any of the three. A non-zero exit code when
something blocks, so it works as a gate in CI.

Every difference lands in one of five classes:

| | | |
|---|---|---|
| `RUN-VARIABLE` | timestamps, batch sequence numbers | ignored |
| `FORMATTING` | same value, written differently | reported, not blocking |
| `ROUNDING` | within one representable unit of the field | needs sign-off |
| `BUSINESS` | the logic changed — money or meaning moved | **blocks** |
| `MISSING` / `EXTRA` | records that vanished or appeared | **blocks** |

Records are matched **by business key, not by line number**, so a reordered file
does not turn into thousands of phantom differences.

---

## The idea worth stealing

> **Don't look for the wrong money. Look for the wrong reason.**

In scenario 1, two of the four real bugs were off by **0.08 and 0.02** in the
money column — well inside the one-cent rounding tolerance that was necessary to
suppress 2,026 benign differences. By money, they were invisible.

They were caught by `accrual_days`: an **integer** off by exactly 1.

Money is an output, and outputs have natural tolerance to hide behind. Day
counts, status flags, loop counters and tier codes are the *causes*, and they
have no tolerance at all. So in this tool **integer fields get no tolerance,
ever**.

---

## The three scenarios

**1 — interest accrual, bug in the money.** 2,000 accounts. A `PERFORM UNTIL`
translated as a `while`, giving four accounts one extra day of interest. Hidden
among 2,026 truncate-versus-round differences and a fully reordered file.

**2 — insurance adjudication, bug in a status code.** Pipe-delimited instead of
fixed-width, a two-field join key, records missing entirely, and the real defect
in a *status code* rather than an amount: 15 rows written `DN` (denied) where the
legacy system wrote `PD` (partially denied). The money was correct to the cent.
Only the *reason* was wrong.

**3 — Perl vs Java, nothing seeded.** The honest one. A 2004-style Perl batch
job, a business specification written from it, then an independent Java 21
implementation written from that specification alone. 354 records disagreed —
and **every one of them came from a single sentence missing in the spec**. Both
programs read the document correctly. Details in
[`legacy-demo/RESULTS.md`](legacy-demo/RESULTS.md).

---

## Running it

No dependencies. Standard-library Python 3.10+.

```bash
# scenario 1 — interest accrual
cd spike
python3 generate.py
python3 verify.py legacy_output.txt modern_output.txt schema.json --lang=en

# scenario 2 — insurance adjudication
python3 generate2.py
python3 verify.py legacy2.txt modern2.txt schema2.json --lang=en

# scenario 3 — real Perl against real Java
cd ../legacy-demo
python3 gen_policies.py
perl legacy/premcalc.pl policies.dat legacy_out.txt
javac -d build modern/PremCalc.java && java -cp build PremCalc policies.dat modern_out.txt
python3 ../spike/verify.py legacy_out.txt modern_out.txt schema.json --lang=en

echo $?   # 1 = something blocks
```

Reports print in English (`--lang=en`) or Vietnamese (default).

### Onboarding an unfamiliar file

```bash
python3 scripts/profile_file.py <file> [second-run-of-the-OLD-system] [--name]
```

Infers column boundaries, types, decimal scale and candidate keys by counting,
not guessing. `--name` asks a **locally running** model (Ollama, LM Studio) to
name the columns — and only to name them. Customer data never leaves the
machine; that is a product constraint, not a configuration option.

---

## Development

```bash
python3 tests/run.py       # 132 checks
python3 tests/mutate.py    # 60/62 mutants killed
```

The second matters more than the first. **This product *is* a test suite**: it
sells the sentence "nothing is wrong". A suite that can never go red makes that
sentence meaningless, so `mutate.py` deliberately breaks the source and requires
the tests to catch it. The two surviving mutants are semantically equivalent and
the reasoning is recorded in [`CLAUDE.md`](CLAUDE.md).

CI runs both on **Windows and Linux**, Python 3.10 and 3.13. Windows is not
optional: on 12 November 2026 the whole suite was green on Linux and died
instantly on Windows, where the console defaults to cp1252 and could not print
the report at all.

---

## What this is not

- **Not tested on real customer data.** Every scenario runs on generated input.
- **No packed decimal (`COMP-3`), no EBCDIC, no multi-record-type files.** Real
  mainframe extracts will need more parsing than this has.
- **Not tested beyond a few million rows.** Both files are loaded into memory.
- **Date formats must be declared, not guessed.** `03/06/2026` matches both
  `dd/mm` and `mm/dd`; guessing wrong would silently pass a real bug, which is
  worse than a false positive. The schema accepts per-field formats.

Read [`CLAUDE.md`](CLAUDE.md) before changing anything.
