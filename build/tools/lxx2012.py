#!/usr/bin/env python3
"""Second English translation: LXX2012 (Michael Paul Johnson's 2012 American-English update of Brenton; Public Domain,
eBible.org eng-lxx2012). It keeps Brenton's versification, so each LXX2012 verse is attached to the Greek verse that already
shows the matching Brenton verse (same Brenton reference, incl. re-matched verses), and then CHECKED independently:
the LXX2012 text must still resemble that Brenton text (word-sequence similarity >= MIN_SIM); otherwise it is hidden.
Output: site/data/en2/<Book>/<ch>.json  {verse: text}   + tools/lxx2012_log.json"""
import json, os, re, difflib, collections
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, '..', 'site', 'data')
MIN_SIM = 0.5
def vpl(p):
    d = {}
    for l in open(p, encoding='utf-8-sig'):
        m = re.match(r'(\S+) (\d+):(\d+[a-z]?) (.*)', l.strip())
        if m: d[(m.group(1), int(m.group(2)), m.group(3))] = m.group(4)
    return d
BR = vpl('/workspace/brenton/eng-Brenton_vpl.txt'); X = vpl('/workspace/lxx-audit/src/eng-lxx2012/eng-lxx2012_vpl.txt')
CODE = {'ESG': 'EST', 'DNG': 'DAN'}
def clean(t):
    t = re.sub(r'^\(\d+(?: in KJV)?\)\s*', '', t)
    return t.replace('⌃', '').replace('  ', ' ').strip()
bytext = collections.defaultdict(list)
for k, t in BR.items(): bytext[t].append(k)
MOD = {'thee': 'you', 'thou': 'you', 'ye': 'you', 'thy': 'your', 'thine': 'your', 'thyself': 'yourself', 'shalt': 'shall', 'wilt': 'will',
       'hast': 'have', 'hath': 'has', 'art': 'are', 'didst': 'did', 'doth': 'does', 'dost': 'do', 'amongst': 'among', 'wast': 'were'}
def toks(t):
    out = []
    for w in re.findall(r"[a-z]+", t.lower()):
        w = MOD.get(w, w)
        if len(w) > 5 and w.endswith(('eth', 'est')): w = w[:-3]
        out.append(w[:6])
    return out
def sim(a, b):
    ta, tb = toks(a), toks(b)
    if not ta or not tb or not (0.75 <= len(ta) / len(tb) <= 1.33): return 0.0
    na = {w[:4] for w in re.findall(r'(?<=[a-z,;:] )[A-Z][a-z]+', a.replace('æ', 'ae').replace('Æ', 'Ae')) if w not in ('God', 'Lord', 'I')}
    nb = {w[:4] for w in re.findall(r'(?<=[a-z,;:] )[A-Z][a-z]+', b.replace('æ', 'ae').replace('Æ', 'Ae')) if w not in ('God', 'Lord', 'I')}
    if len(na) >= 2 and len(nb) >= 2 and len(na & nb) / len(na | nb) < 0.5: return 0.0   # different names -> different verse
    return difflib.SequenceMatcher(None, ta, tb, autojunk=False).ratio()
MIN_SIM = 0.8
xkeys = collections.defaultdict(list)   # (code, ch) -> ordered list of verse keys
for k in X: xkeys[(k[0], k[1])].append(k)
def candidates(code, c, v):
    """LXX2012 verses near Brenton (code, c, v): same chapter +-4 verses, and edges of the neighbouring chapters."""
    out = []
    for cc in (c - 1, c, c + 1):
        ks = xkeys.get((code, cc), [])
        for k in ks:
            try: n = int(re.match(r'\d+', k[2]).group())
            except Exception: continue
            vn = int(re.match(r'\d+', v).group())
            if cc == c and abs(n - vn) <= 4: out.append(k)
            elif cc != c and (n <= 4 or n >= len(ks) - 3): out.append(k)
    return out
books = json.load(open(D + '/books.json')); log = collections.Counter(); low = []; offs = collections.Counter()
for bk in books:
    for c in bk['chapters']:
        best = {}
        vs = json.load(open(f"{D}/{bk['id']}/{c}.json"))
        sibling = None
        for v in vs:
            if v[2] and bytext.get(v[2]): sibling = bytext[v[2]][0]; break
        for v in vs:
            if not v[2]: continue
            st = v[3] if len(v) > 3 and isinstance(v[3], dict) else {}
            ks = bytext.get(v[2])
            if ks: refs = ks[:1]
            elif st.get('s') == 'm' and sibling:
                refs = [(sibling[0], int(r.split(':')[0]), r.split(':')[1]) for r in st['br'].split()]
            else: log['no_brenton_ref'] += 1; continue
            code = CODE.get(refs[0][0], refs[0][0])
            cands = set()
            for r in refs: cands.update(candidates(code, r[1], r[2]))
            sc = sorted(((sim(v[2], clean(X[k])), k) for k in cands), reverse=True)
            if not sc or sc[0][0] < MIN_SIM:
                log['hidden_no_confident_match'] += 1; low.append([f"{bk['id']} {c}:{v[0]}", round(sc[0][0], 2) if sc else 0, v[2][:80], clean(X[sc[0][1]])[:80] if sc else '']); continue
            if sc[0][0] < 0.9 and len(sc) > 1 and sc[0][0] - sc[1][0] < 0.1:   # formulaic lists: ambiguous neighbour -> hide
                log['hidden_ambiguous'] += 1; continue
            # multi-verse Brenton English (re-matched joins): take consecutive LXX2012 verses after the best one
            s, k = sc[0]
            t = clean(X[k])
            if len(refs) > 1:
                ks2 = xkeys[(k[0], k[1])]; i0 = ks2.index(k); t = ' '.join(clean(X[x]) for x in ks2[i0:i0 + len(refs)]); s = sim(v[2], t)
                if s < MIN_SIM: log['hidden_no_confident_match'] += 1; continue
            if k in best and best[k][0] >= s: log['hidden_duplicate'] += 1; continue
            if k in best: log['hidden_duplicate'] += 1; log['ok'] -= 1
            best[k] = (s, v[0], t); log['ok'] += 1
            r0 = refs[0]; offs[(k[1] - r0[1], int(re.match(r'\d+', k[2]).group()) - int(re.match(r'\d+', r0[2]).group()))] += 1
        out = {vv: t for k, (s, vv, t) in best.items()}
        if out:
            os.makedirs(f"{D}/en2/{bk['id']}", exist_ok=True)
            json.dump(out, open(f"{D}/en2/{bk['id']}/{c}.json", 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
json.dump({'counts': log, 'offsets': {str(k): n for k, n in offs.most_common(20)}, 'low': low}, open(os.path.join(HERE, 'lxx2012_log.json'), 'w'), ensure_ascii=False, indent=0)
print('LXX2012:', dict(log), 'offsets (chapter, verse) vs Brenton:', offs.most_common(6))

# write an empty file for chapters with no confident LXX2012 verses, so the site never requests a missing file
import json as _j, os as _o
_D = _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..', 'site', 'data')
for _b in _j.load(open(_o.path.join(_D, 'books.json'))):
    if not _b.get('en'): continue
    for _c in _b['chapters']:
        _f = _o.path.join(_D, 'en2', _b['id'], f'{_c}.json')
        if not _o.path.exists(_f):
            _o.makedirs(_o.path.dirname(_f), exist_ok=True); open(_f, 'w').write('{}')
