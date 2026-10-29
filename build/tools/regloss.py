#!/usr/bin/env python3
"""Step: re-gloss review for the ~1,000 most frequent LXX lemmas.
Candidate = current short gloss shares no content word (or stem) with the STEPBible TBESG brief gloss, its Abbott-Smith senses,
or the TFLSJ (LSJ) senses. Proposed gloss = TBESG brief gloss (STEPBible, CC BY 4.0), lightly normalised ('to ' dropped, '/' -> '; ').
Every proposal is written to tools/regloss_candidates.csv; decisions (accept / reject / manual text) live in tools/regloss_review.csv
(hand review); accepted changes are applied by fix_data-style patching of lexicon.json and logged to data/regloss_log.csv."""
import json, glob, re, csv, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, '..', 'site', 'data')
L = json.load(open(D + '/lexicon.json')); C = json.load(open(D + '/counts.json'))
dic, lsj = {}, {}
for f in glob.glob(D + '/dict/*.json'): dic.update(json.load(open(f)))
for f in glob.glob(D + '/lsj/*.json'): lsj.update(json.load(open(f)))
STOP = set('a an the of to in on for and or be is one s by with from at as it its into up out off away'.split())
def words(s): return {w[:5] for w in re.findall(r'[a-z]+', (s or '').lower()) if w not in STOP and len(w) > 1}
def norm(g):
    g = re.sub(r'\bto ', '', g).replace('/', '; ').strip(' ;:')
    g = re.sub(r':\s*', ': ', g)
    return g
top = sorted(C, key=lambda k: -C[k])[:1000]
if '--candidates' in sys.argv:
    out = csv.writer(open(os.path.join(HERE, 'regloss_candidates.csv'), 'w', newline=''))
    out.writerow(['lex', 'count', 'lemma', 'pos', 'old', 'proposed', 'tbesg_senses', 'lsj_senses'])
    n = 0
    for k in top:
        lem, old, pos = L[k][0], L[k][1], L[k][2]
        if 'Proper' in pos: continue
        d = dic.get(k, {}); g = d.get('g'); ls = lsj.get(k, {}).get('s', [])
        if not g: continue
        ref = words(g) | words(' '.join(d.get('s', []))) | words(' '.join(ls))
        if words(old) & ref:
            parts = [p.strip() for p in re.split(r'[;,]', old) if p.strip()]
            bad = [p for p in parts if words(p) and not (words(p) & ref)]
            if not bad or len(parts) < 2: continue
            keep = [p for p in parts if p not in bad]
            n += 1; out.writerow([k, C[k], lem, pos, old, '; '.join(keep), ' | '.join(d.get('s', [])[:4]), ' | '.join(ls[:3]), 'drop: ' + '; '.join(bad)]); continue
        n += 1; out.writerow([k, C[k], lem, pos, old, norm(g), ' | '.join(d.get('s', [])[:4]), ' | '.join(ls[:3])])
    print(n, 'candidates')

if '--apply' in sys.argv:
    """Apply the hand-reviewed decisions (tools/regloss_review.tsv: lemma <TAB> new gloss) to the top-1000 lemmas; log every change."""
    import unicodedata as _u
    want = dict(_u.normalize('NFC', l.rstrip('\n')).split('\t') for l in open(os.path.join(HERE, 'regloss_review.tsv'), encoding='utf-8') if '\t' in l)
    topset = set(top); fixes = json.load(open(D + '/gloss_fixes.json')) if os.path.exists(D + '/gloss_fixes.json') else {}
    log = csv.writer(open(D + '/regloss_log.csv', 'w', newline='', encoding='utf-8')); log.writerow(['lex', 'lemma', 'count', 'old', 'new', 'source', 'tbesg_brief_gloss'])
    done = set()
    for k in top:
        lem = _u.normalize('NFC', L[k][0])
        if lem in want and lem not in done and 'Proper' not in L[k][2]:
            old = L[k][1]; new = want[lem]; done.add(lem)
            if old == new: continue
            L[k][1] = new; g = dic.get(k, {}).get('g', '')
            log.writerow([k, lem, C[k], old, new, 'hand review of STEPBible TBESG (Abbott-Smith) + TFLSJ (LSJ) senses', g])
            fixes[k] = {'lex': k, 'lemma': lem, 'old': old, 'new': new, 'tbesg': g, 'verified_in_tbesg': True, 'round': 'regloss'}
    missing = set(want) - done
    json.dump(L, open(D + '/lexicon.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    json.dump(fixes, open(D + '/gloss_fixes.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('regloss applied', len(done), 'missing', missing)
