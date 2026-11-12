# LinkedIn post — draft, 10/11/2026

## Version A — the one I'd post (≈270 words)

**Don't look for the wrong money. Look for the wrong reason.**

I spent this week building a small tool that compares the output of a legacy batch
job against its migrated replacement, and one result surprised me enough to change
how I think about migration testing.

Setup: a daily interest accrual job, 2,000 accounts. I injected four differences
into the "after" file — three harmless (COBOL truncates where Java rounds, the new
system writes records sorted, a run timestamp in the header) and one real: a
`PERFORM UNTIL` translated as a `while`, giving four accounts one extra day of
interest.

`diff` reported 3,874 changed lines. Sorting both files first still left 2,036.
Four real bugs, buried in two thousand lines of noise. This is exactly why parallel
runs drag on for years: nobody can read all of it, and nobody wants to be the
person who said "that difference is fine."

The classifier found all four. No false positives, no misses.

Here's the part I didn't plan. Two of those four accounts were off by **0.08 and
0.02** in the money column — well inside the one-cent rounding tolerance that was
necessary to suppress the other 2,026 benign differences. By money, they were
invisible.

They were caught by `accrual_days`: an **integer** off by exactly 1.

Money is an output, and outputs have natural tolerance to hide behind. Day counts,
status flags, loop counters, tier codes — those are the *causes*, and they have no
tolerance at all. An integer off by one is never fine.

So the rule I'd now put first in any migration test plan: give your money columns a
tolerance if you must, but give your integers none.

---

## Version B — shorter, for a comment or repost (≈120 words)

A migration bug I almost missed this week, and what it taught me.

Legacy batch job vs. its Java rewrite, 2,000 accounts. `diff` gave me 3,874 changed
lines — 2,036 even after sorting both files. Four of those were real money bugs: a
COBOL `PERFORM UNTIL` translated as a `while`, giving four accounts an extra day of
interest.

Two of the four were off by 0.08 and 0.02. That is inside any sane rounding
tolerance, and I needed that tolerance to suppress 2,026 genuinely benign
differences. By the money column, those bugs did not exist.

What caught them: `accrual_days`, an integer off by exactly 1.

Money is an output. Day counts and status flags are causes. Give outputs a
tolerance; give causes none.

---

## Follow-up post, if version A lands (hold 3–4 days)

**The second test is the one that matters.**

Last week I posted about a comparator that found four real bugs where `diff`
produced two thousand lines of noise. One scenario proves nothing, so I tried to
break it.

New shape, deliberately: pipe-delimited instead of fixed-width, a two-field
join key, records missing entirely, and the real bug in a **status code** instead
of an amount — 15 rows written as `DN` (denied) where the legacy system wrote `PD`
(partially denied). The money was correct to the cent. Only the *reason* was wrong.
No tool that reconciles amount columns catches that.

First run: **3,000 false positives.** My rules classified every string difference as
a business error, so a date reformatted from `2026-06-03` to `03/06/2026` and a
provider name upper-cased both looked like money was wrong. Useless — exactly as
useless as `diff`.

The question was never "do the rules need changing." It was *do they need changing
per customer.* Two fixes, both generic: parse dates into dates regardless of
notation (two spellings of one date are not two values), and add a FORMATTING class
for strings equal after trimming and case-folding — reported, not blocking.

Second run: exactly 25 findings for 25 injected bugs. Cost: 21 lines of code, 4 of
them in the classification logic. Customer-specific rules: zero.

And a new risk I'd rather name than hide: my date parser tries formats in order, so
`03/06/2026` resolves as 3 June. If the new system writes US-style, that's 6 March,
and the tool would **silently pass a real bug**. Worse than a false positive — a
false positive gets seen. Any real version has to refuse to run when a date field
matches more than one plausible format, instead of guessing.
