#!/bin/sh
# Rebuild all data (sources: see README). Needs /workspace/brenton, /workspace/lxx-audit/src and /workspace/src inputs.
set -e
cd "$(dirname "$0")"
python3 build.py
python3 tools/realign.py
python3 tools/greekdiff.py            # '≠ Greek differs' badges (Brenton's own Greek vs Rahlfs)
python3 tools/fix_data.py
python3 tools/enrich.py
python3 tools/regloss.py --apply      # hand-reviewed glosses for frequent lemmas (tools/regloss_review.tsv)
python3 tools/lxx2012.py              # second English translation (LXX2012, PD)
python3 tools/vulgate.py
python3 tools/latmorph.py             # needs /workspace/src/lat_kaikki.jsonl (Wiktionary Latin, CC BY-SA 4.0)
python3 tools/latalign.py --retrain --eval --export
python3 tools/notes.py
MC_N=4400 python3 tools/morphcheck.py # independent parsing check report (Wiktionary tables)
