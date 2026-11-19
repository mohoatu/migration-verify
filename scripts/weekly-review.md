# Sunday review — 20 minutes, no more

The quality loop has three beats: **hourly snapshots** (automatic) → **Sunday
review** (this file) → **the suite that tests the suite** (`tests/mutate.py`).

This is the middle beat. It exists because a week of agent-assisted edits drifts
in ways no individual commit shows.

---

## Run first, read after

```bash
python3 tests/run.py          # must be green
python3 tests/mutate.py       # must be >= 80%, and ought to be 100%
git log --oneline -20
git diff --stat HEAD~20       # what the week actually touched
wc -l spike/*.py
```

---

## Six questions

**1. Has the plumbing-to-classification ratio drifted?**

How many lines is `classify.py` now? The marker is **48**. Growth means
per-customer rules are creeping into code — the line between product and
consulting. If it grew, check whether the addition belongs in `schema.json`
instead.

**2. Has any business vocabulary reached `classify.py`?**

`tests/run.py` guards a keyword list, but that list is not exhaustive. Read the
file once with your eyes. Finding "interest", "claim" or "policy" means fix it
now and add the word to the test.

**3. Which mutants survived this week?**

Every survivor is a behaviour nothing guards. Either write a test that kills it,
or record in `CLAUDE.md` why it is acceptable. **Do not carry it into next
week** — two weeks and the hole becomes normal.

**4. Do the published figures still match?**

`RESULTS.md`, the posts, the images in `spike/gallery/` and the Upwork listing
all contain numbers. Re-run the scenarios and compare. If they differ, fix the
documents, not the expectations.

```bash
cd spike && python3 generate.py && python3 verify.py legacy_output.txt modern_output.txt schema.json --lang=en | head -3
```

**5. Has any customer data reached the repo?**

```bash
git log --all --name-only --format= | sort -u | grep -iE 'customer|cust|prod' || echo "clean"
```

If something did, `git rm` is not enough — it remains in history. Deal with it
that same week.

**6. Did a feature appear that nobody asked for?**

The plan says: no product code until there is a signal from outside. If
something new grew this week, ask **did anyone request it?** If not, consider
removing it. Code nobody needs still has to be fed.

---

## Tidy up

- Delete merged branches, temporary files, `__pycache__`
- Snapshots older than two weeks: `git update-ref -d refs/heads/snapshots`, then snapshot again
- Add one line to the log below: what changed, what is still open

---

## Log

<!-- One line per week. Keep it short. -->

- **2026-11-12** — Built the harness: 115 checks, 48/48 mutants killed, schema
  profiler and a bulk-reader sub-agent. No customers. Open: publish the Upwork
  listing, post the LinkedIn follow-up.
- **2026-11-13** — Scenario 3 (real Perl vs real Java, nothing seeded): 354
  blocking differences, all from one missing sentence in the spec. Two tool
  defects found and fixed: the `TRAILER` line was nearly counted as a record,
  and trailer differences were reported without detail. 132 checks, 60/62.
- **2026-11-19** — Repo public on GitHub. All documentation switched to English.
