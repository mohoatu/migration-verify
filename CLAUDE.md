# CLAUDE.md — working notes for agents on this repo

Read this before changing anything. It is short on purpose.

---

## What this is

A tool that **compares the output of a batch job before and after a migration**
and **classifies** every difference: ignorable, needs sign-off, or blocks
go-live.

It does not translate code. It does not review code. It answers one question:
*do these two systems produce the same result, and where they differ, why.*

---

## Facts an agent will get wrong if it guesses

- **No customers. No revenue. Still a spike, not a product.** All three
  scenarios run on data this repo generates. Do not write anything implying it
  has been used on real data. `spike/RESULTS.md` and `legacy-demo/RESULTS.md`
  state the limits — keep them, do not soften them.

- **The value is in `classify.py`, not in the rest.** `records.py`, `report.py`
  and `verify.py` are plumbing: anyone would write them the same way. The ratio
  of **158 lines of plumbing to 48 of classification** is a number to keep from
  drifting — classification growing means per-customer rules are creeping into
  the code, and at that point this is consulting, not a product.

- **No rule may mention a customer's business.** Classification depends only on
  **data type**: decimal, integer, string, date. The moment the words "interest",
  "insurance" or "account" appear in `classify.py`, the product is dead.
  Customer-specific knowledge belongs in the **schema** (`schema*.json`), not in
  code. `tests/run.py` enforces this with a keyword check.

- **Integers have no tolerance. Ever.** This is the central argument:
  *don't look for the wrong money, look for the wrong reason.* Money is an
  output and has rounding tolerance to hide behind; day counts, status flags and
  loop counters are causes and have nowhere to hide. In scenario 1, two real
  defects moved the money column by only 0.08 and 0.02 — they were caught
  **only** because `accrual_days` was off by 1. Adding tolerance to integer
  fields deletes the reason this tool exists.

- **The test suite must prove it can fail.** This product *is* a test suite. A
  suite that never goes red is worthless, and here it would also be a lie sold
  to a customer. Hence `tests/mutate.py`, which **must pass before every
  commit** — see Commands.

- **Customer data never enters the repo.** Not committed, not pasted into an
  issue, not left in the working directory longer than needed. `.gitignore`
  blocks `customer/` and `*.cust.txt`, but `.gitignore` is not a security
  control — habit is.

- **No product code yet.** The plan says: write no product code until there is a
  signal from outside (a customer asking, or a response to the writing). Fixing
  the spike and improving test infrastructure is fine; building new features is
  not. If you intend to add a feature, **ask first**.

- **Everything in this repo is written in English** — documentation, code
  comments, commit messages. Public repository, international readers.

---

## Layout

```
CLAUDE.md             This file — the repo's SOUL
README.md             Introduction
spike/                Scenarios 1 and 2: the tool, results, sales assets
  classify.py           CLASSIFICATION — the only part with real value
  records.py            plumbing: read files, match records by key
  report.py             plumbing: render the report (English + Vietnamese)
  verify.py             plumbing: wire it together, exit code for CI
  schema*.json          the schema — the only place customer specifics live
  generate*.py          test data for scenarios 1 and 2
  make_gallery.py       marketing images; figures pulled from the tool itself
  RESULTS.md            measurements and known limits
legacy-demo/          Scenario 3: real Perl against real Java, nothing seeded
tests/                The test suite, and the suite that tests the suite
  run.py                132 checks, no pytest
  mutate.py             inverse check: can the suite actually fail?
scripts/
  profile_file.py       unfamiliar customer file -> draft schema.json (+ local model)
  snapshot.sh / .ps1    hourly snapshot onto a `snapshots` branch
  weekly-review.md      Sunday review, 20 minutes
harness/              Repo sub-agents and skills; `install.*` copies into .claude/
customer/             Customer data — NEVER committed, already in .gitignore
```

Boundaries worth respecting:

- `classify.py` **must not import** `records.py` or `report.py`. It receives
  parsed values and returns a verdict. Keeping it isolated is what makes it
  measurable and replaceable.
- `schema*.json` is **the customer-facing interface**. Adding a key to the schema
  is a product decision, not a refactor.
- `make_gallery.py` **pulls its figures from the tool**, never hand-typed. A
  marketing image must never claim something the tool does not do.

---

## Routing: which work goes where

This repo will handle customer files of hundreds of thousands to millions of
rows. Reading one into an expensive model's context is wasteful and pointless —
it does not need line 400,000, it needs the file's **shape**.

| Work | Goes to | Why |
|---|---|---|
| Reading / summarising a large data file | `bulk-reader` sub-agent (cheap model) | compression, not reasoning |
| Inferring columns, types, keys | `scripts/profile_file.py` | **count, don't guess** — no model involved |
| Naming columns in a draft schema | a **locally running** model, optional | customer data must not leave the machine |
| Classification rules, design, tests | the main model | getting this wrong breaks the product |
| Deciding whether a difference blocks | **`classify.py`, no model at all** | the verdict must be deterministic and repeatable |

That last row is the important one. A language model must **never** decide
whether a difference blocks go-live. Customers buy determinism: the same two
files give the same answer today and in six months. Models sit around the
product doing dull work; they are not in the decision path.

Install the sub-agent and skill with `bash harness/install.sh`
(or `harness\install.ps1`).

### Local models

`scripts/profile_file.py --name` calls Ollama (11434), LM Studio (1234) or
llama.cpp (8080) on `localhost`. With no server running it still produces a
schema — the fields are just named `field_00`.

**`localhost` only, and that is a product constraint rather than a setting.**
Not about cost: the sales material promises customer data never leaves their
network. Adding a cloud endpoint to that file breaks the promise being sold. If
a stronger model is needed, run a stronger model on that machine.

---

## Commands

Run from the repo root. No dependencies, standard-library Python.

```bash
python3 tests/run.py              # 132 checks
python3 tests/mutate.py           # inverse check — REQUIRED before every commit
python3 tests/mutate.py -v --only classify.py    # inspect one file
bash scripts/snapshot.sh          # snapshot work in progress
bash harness/install.sh           # install sub-agent + skill into .claude/

# unfamiliar customer file -> draft schema
python3 scripts/profile_file.py <file> [second-run-of-the-OLD-system] [--name] [--out schema.json]
```

**Both must be green before any commit.** The second matters more than the
first: it is the only thing proving the first means anything.

---

## Surviving mutants, reviewed and accepted

`tests/mutate.py` currently kills **60/62**. The two survivors are
**semantically equivalent** — they change how the code runs without changing
what it produces — so writing tests to kill them would only pin down internal
detail. Recorded here rather than left to drift:

- **`verify.py:71` — disabling `if a == b: continue`.** Without the early exit,
  identical lines still reach `classify_field`, which returns `None` for every
  equal field. Same result, just slower.
- **`verify.py:74` — `or` becomes `and` in `if ra is None or rb is None`.**
  `parse_trailer` returns `None` only when the schema has no `trailer_fields`,
  and both sides share one schema. Exactly one side being `None` cannot happen.

If `parse_trailer` ever returns `None` for another reason — a malformed trailer,
say — the second stops being equivalent and needs a test.

---

## Conventions

- **Vanilla everything.** No framework, no pytest, no `node_modules`, no
  `requirements.txt`. This is sold to banks, where a dependency means a meeting
  with the security team. Adding one needs a reason heavier than that.
- **Comments explain *why*, not *what*.** The code already says what. The most
  valuable comments here record **known trade-offs** — see the end of
  `classify.py`.
- **Limits are written down, not hidden.** `RESULTS.md` has a section for what
  the work has **not** proven. Adding a capability means adding its limits too.
- **Commits describe *why*, in the imperative, one concern each.**
- **Never rewrite history, never force-push.**

---

## Traps

- Changing `classify.py` without running `mutate.py` is the quietest way to let
  the suite rot. A new classification rule without a matching mutation is
  untested.
- `generate*.py` use fixed seeds. Changing a seed changes every figure in
  `RESULTS.md`, the posts and the gallery images. Change one, update all three.
- Loosening a tolerance to "reduce noise" always looks reasonable while staring
  at a long report. That is exactly how this tool turns back into `diff`.
