# Septuagint Study Bible

**Live site:** https://drakewing-eng.github.io/septuagint-study-bible/

This is a free, non-commercial study reader for the Greek Septuagint (Rahlfs 1935). You can tap any Greek word to open a study card. It is a static site with no server, no tracking and no dependencies. It works on phones (the card opens as a bottom sheet) and on desktops.

## Features
- The full Rahlfs LXX text. Every word is tappable.
- **Compact word card:** the lemma with its LXX frequency, a short gloss and a one-line parse. **More ▾** opens:
  - two dictionaries: Abbott-Smith (STEPBible TBESG) and LSJ (STEPBible TFLSJ);
  - grammar chips with plain-English explanations;
  - a forms table and references;
  - the Wiktionary etymology (a separate CC BY-SA layer);
  - the Latin Vulgate word aligned to this Greek word, with its parse and meaning (a separate CC BY-SA layer).
- **Two English translations:** Brenton (1844/1851) and LXX2012, the 2012 American-English update of Brenton. Use the **EN** button to switch: Brenton → LXX2012 → both → off. Each translation is matched to the Greek verse on its own, and is hidden where the match is unsure.
- **≠ badge:** marks verses where Brenton translated noticeably different Greek, so the English may not match the Rahlfs text shown.
- Notes on New Testament quotations, search, dark mode and font sizes.

## How accurate is it? (honest numbers)
All of these are automatic processes checked by sampling, not a line-by-line human edition.

| Area | Method | Result |
|---|---|---|
| Brenton English ↔ Greek verse match | Re-matched with Brenton's own Greek (grcbrent); hidden where no reliable match | see About page; unmatched verses are hidden, not guessed |
| LXX2012 ↔ verse match | Text similarity within ±4 verses, length and proper-name checks, ambiguity margin | 26,561 verses shown, 1,609 hidden; hand check 40/40 correct |
| "≠ Greek differs" badge | Word overlap between Brenton's Greek and Rahlfs, names ignored | 511 verses flagged (28 English hidden); hand check 38/40 correct (≈95%). About a quarter are wording differences, the rest verse-division differences |
| Short glosses | Top 1,000 lemmas screened against TBESG/TFLSJ; changes hand-decided | 122 changes, all in `data/regloss_log.csv`. All 122 re-read by hand: 0 wrong, 1 sense reordered (ἀναιρέω → "kill; take away") and fixed |
| Morphology (CATSS) | Independent check of 4,400 random noun/adjective/verb tokens against Wiktionary inflection tables (no offline analyser such as Morpheus could be installed) | 3,060 covered. Agreement 98.6% before fixes, 99.1% after 13 confirmed overrides. The remaining 28 disagreements are mostly Wiktionary gaps or ambiguous forms (see `build/tools/morphcheck_disagreements.csv`) |
| Morphology overrides | Form-based rules plus hand cases | 212 tags corrected, listed in `data/parse_overrides.json` |
| Latin word for a Greek word | IBM Model 1, both directions, competitive linking | On a 112-word hand-made gold set: 103/105 shown links correct (≈98%). The set is small, so read this as roughly 95%+ |

Tagging errors that the word ending cannot reveal will remain. Always check the dictionary senses.

## Report an error
Please open a GitHub issue: https://github.com/drakewing-eng/septuagint-study-bible/issues
Include the book, chapter and verse, the word, and what looks wrong.

## Sources and licences
- **Greek text, lemmas and morphology:** Rahlfs 1935 via CCAT (University of Pennsylvania) and eliranwong/LXX-Rahlfs-1935, **CC BY-NC-SA 4.0**. Because of this source, the whole site is **CC BY-NC-SA 4.0 and non-commercial** (see `LICENSE`).
- **English:**
  - Brenton (1844/1851), public domain;
  - LXX2012 by Michael Paul Johnson (2012), dedicated to the public domain.
  - Both texts, and Brenton's Greek (grcbrent), are from eBible.org.
  - Thomson's 1808 translation was not included because no clean digital text was available.
- **Dictionaries:** STEPBible.org TBESG (Abbott-Smith) and TFLSJ (LSJ), Tyndale House, **CC BY 4.0**.
- **Latin:** Clementine Vulgate and Douay-Rheims, public domain (eBible.org).
- **NT Greek:** SBLGNT, **CC BY 4.0**.
- **Font:** Gentium Plus, SIL OFL 1.1.
- **Separate CC BY-SA 4.0 layers:**
  - The Wiktionary etymologies and the Latin word layer (Latin parses and meanings from Wiktionary via kaikki.org) are kept in separate files and labelled. They stay under **CC BY-SA 4.0** and are not relicensed as NC.
  - Wiktionary's Ancient Greek tables were used only to check the morphology; no table text is copied.

Full attributions are in `NOTICE` and on the site's About page.

## Rebuild
The scripts are in `build/`. They expect this repository checked out as `site/` with `build.py`, `run_all.sh` and `tools/` next to it, plus the downloaded sources described at the top of each script (eBible VPL zips, CCAT/eliranwong data, STEPBible files, kaikki.org Wiktionary dumps).

```
cp -r site/build/* .         # build.py, run_all.sh, test_site.py, tools/
sh run_all.sh                # build -> realign -> greekdiff -> fix_data -> enrich -> regloss -> lxx2012 -> vulgate -> latin -> notes -> morphcheck
(cd site && python3 -m http.server 8766) & python3 test_site.py   # Playwright tests
```
Never run `realign.py` or `fix_data.py` on their own: they change the data in place.

## Archive
A zip of the complete site is attached to each GitHub release.
