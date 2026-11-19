# Scenario 3 — real Perl against real Java

Run **13 November 2026**. The first scenario where **nobody seeded a single
difference**.

---

## How it differs from the first two

[`spike/RESULTS.md`](../spike/RESULTS.md) states the biggest limitation of
scenarios 1 and 2 plainly: one script generated **both** output files and then
injected the defects into the "after" side. Knowing the answer in advance makes
the test much easier than reality.

This time:

| | Scenarios 1 & 2 | Scenario 3 |
|---|---|---|
| Output files | one script produced both | **two independent programs computed them** |
| Differences | injected deliberately | **nobody knew where they would be** |
| Legacy language | none | **Perl 5.34** |
| Target language | none | **Java 21** |

Method: write [`SPEC.md`](SPEC.md) **first** — a language-neutral business
specification describing *what must be computed*, not *how the old program
computes it*. Write `legacy/premcalc.pl` in the style of a 2004 batch script.
Then write `modern/PremCalc.java` **from the specification alone**, without
reopening the Perl.

### Why Perl and not COBOL

The market gap identified earlier is *a fifteen-year-old system with no
mainframe*. COBOL is covered: IBM ships watsonx Code Assistant for Z and
published an ASE '24 paper on validating exactly this kind of translation.
Choosing COBOL as the example means standing next to IBM.

Perl is the largest "nobody wants to touch it" batch language **outside** the
mainframe: ETL and report generation in banks, telcos and insurers written
between 1998 and 2010, now being rewritten in Java. IBM, Google and Atos are
not there.

It is also the better technical fit. Perl uses IEEE doubles and `sprintf`
rounds half-to-even; Java `BigDecimal` is exact. Those two **will** disagree at
the cent level, in ways that are hard to predict.

*(`cobol-demo/PREMCALC.cbl` is kept as reference. GnuCOBOL cannot run on the
development machine: Smart App Control blocks unsigned binaries.)*

---

## Result

1,200 policies. Plain `diff`: **2,402 changed lines**. 578 records byte-identical.

```
DO NOT SHIP — 354 differences need a decision, across 354 records

  BUSINESS LOGIC CHANGED        354  <- blocks
  Rounding / representation     275

  field `instalment`: 354 records

Acceptable, but needs explicit sign-off
  field `instalment`: 266 · `total_due`: 5 · `interest`: 3 · `sum_due`: 1
```

### All 354 came from **one missing sentence**

Rule 5 says *"the instalment amount is the total divided by the number of
instalments"*. Rule 6 says *"any remainder goes onto the last instalment"*. The
report has **one** instalment column — and the specification never says which
one to print.

- Perl prints the **last** instalment (the odd one, the one support gets asked about)
- Java prints the **standard** instalment from rule 5

**Both read the document correctly.** Nobody made a mistake; the document is
missing a sentence. That is the real shape of a migration defect, and it does
not show up in the 578 records that matched.

### The control total is off by one cent

```
Perl : TRAILER   001200 59629808.34
Java : TRAILER   001200 59629808.35
```

Floating-point accumulation over 1,200 records. One cent — and the first number
an auditor reconciles.

---

## Two defects in the tool that this scenario exposed

The most valuable part of the day was not the result. It was two faults that
only appear when a real program writes a real file.

**1. The `TRAILER` line was nearly counted as a record.** The string
`"RUNSTAMP"` was hard-coded in `records.py` as the marker for non-record lines.
This file ends with `TRAILER`, and practically every batch job has a control
total line. Left alone it would have produced a phantom "missing record" on
**every** run — and worse, masked a real missing record. Now declared in the
schema as `non_record_prefixes`.

**2. The tool said "header line changed" without saying what changed.** For a
trailer that is a serious omission: a control total difference was demoted to a
vague note the reader would skip. Fixed — declare `trailer_fields` and the
trailer is compared **field by field** like any record, with the record count,
being an integer, getting no tolerance.

The second fix needed care in one place: **it must not block when the schema
declares no `trailer_fields`**, because header lines usually contain a run
timestamp and change every night. The report now says
`changed (not checked — declare trailer_fields)` rather than lumping that in
with a checked result.

Neither fault could surface in a generated scenario, because the person writing
the generator never thinks to seed a trailer.

---

## Limitations

- **One person wrote both implementations.** Mitigated by writing the spec first
  and the Java only from the spec, but weaker than two real engineers.
- **No real COBOL**, so no packed decimal, no EBCDIC, no multi-record-type files.
- **The input is still generated.** But only the *input* — the outputs were
  computed independently, and that is the difference from scenarios 1 and 2.

---

## Reproducing

```bash
cd legacy-demo
python3 gen_policies.py
perl legacy/premcalc.pl policies.dat legacy_out.txt
javac -d build modern/PremCalc.java && java -cp build PremCalc policies.dat modern_out.txt
python3 ../spike/verify.py legacy_out.txt modern_out.txt schema.json --lang=en
```
