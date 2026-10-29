#!/usr/bin/env python3
"""'Greek differs' badge: flag verses whose English (Brenton) was translated from Greek that differs materially from the Rahlfs
Greek shown. Compares the Rahlfs verse with Brenton's own Greek (eBible grcbrent, PD) at the Brenton reference the English came from.
Material difference = low word overlap (sim < SIM) AND at least MINW content words present in one text but absent in the other.
Writes {'s':'d'} status (or adds 'gd' to an existing status) + tools/greekdiff_log.json."""
import json, os, re, collections, unicodedata
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, '..', 'site', 'data')
SIM, MINW = float(os.environ.get('GD_SIM', 0.7)), int(os.environ.get('GD_MINW', 3))
def vpl(p):
    d = {}
    for l in open(p, encoding='utf-8-sig'):
        m = re.match(r'(\S+) (\d+):(\d+[a-z]?) (.*)', l.strip())
        if m: d[(m.group(1), int(m.group(2)), m.group(3))] = m.group(4)
    return d
BR = vpl('/workspace/brenton/eng-Brenton_vpl.txt'); GB = vpl('/workspace/lxx-audit/src/grcbrent/grcbrent_vpl.txt')
bytext = {}
for k, t in BR.items(): bytext.setdefault(t, k)
STOPG = set('και ο η το του της των τον την τοις ταις τω τη οι αι τα δε εν εις εκ εξ επι προς οτι αυτου αυτων αυτον αυτω αυτη αυτοις μου σου ου ουκ μη γαρ'.split())
HEB = set('αλεφ βηθ γιμελ δελθ η ουαυ ζαι ηθ τηθ ιωθ χαφ λαμεδ μημ νουν σαμχ αιν φη σαδη κωφ χα ρης χσεν σεν θαυ'.split())
def full(s):
    s = ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn').replace('ς', 'σ')
    return re.findall(r'[α-ω]+', s)
def joinpairs(x, other):
    """merge adjacent words that the other edition writes as one word (ἀνὰ μέσον / ἀναμέσον, εἴκοσι τρεῖς / εἰκοσιτρεῖς)"""
    os_ = set(other); out = []; i = 0
    while i < len(x):
        if i + 1 < len(x) and x[i] + x[i + 1] in os_: out.append(x[i] + x[i + 1]); i += 2
        else: out.append(x[i]); i += 1
    return out
def nz(s):
    s = ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn').replace('ς', 'σ')
    return [w[:5] for w in re.findall(r'[α-ω]+', s)]
def sim(a, b):
    if not a or not b: return 0.0
    return sum((collections.Counter(a) & collections.Counter(b)).values()) / max(len(a), len(b))
def run(write=True):
    books = json.load(open(D + '/books.json')); flagged = []; checked = 0
    for bk in books:
        for c in bk['chapters']:
            p = f"{D}/{bk['id']}/{c}.json"; vs = json.load(open(p)); ch = False
            for v in vs:
                if not v[2]: continue
                st = v[3] if len(v) > 3 and isinstance(v[3], dict) else None
                if st and st.get('s') in ('d', 'h', 'j'): continue
                k = bytext.get(v[2])
                if not k or k not in GB: continue
                # proper names are ignored (spelling of names differs widely between editions and is not a 'different text')
                rw = [t[0] for t in v[1] if '᾿' not in t[0] or len(t[0]) > 4]
                rw = [w for w in rw if not (full(w) and full(w)[0] in HEB and len(rw) and w == rw[0])]
                lower_r = {x for w in rw if not w[:1].isupper() for x in full(w)}
                af = [x for w in rw if not w[:1].isupper() for x in full(w)]
                bw = re.findall(r'\S+', GB[k].replace('γἱοὶ', 'υἱοὶ')); bf = []
                for i, w in enumerate(bw):
                    for x in full(w):
                        if w[:1].isupper() and x not in lower_r and not any(x == y + z for y, z in zip(af, af[1:])): continue
                        bf.append(x)
                af = joinpairs(af, bf); bf = joinpairs(bf, af)
                a = [w[:5] for w in af]; b = [w[:5] for w in bf]
                if len(a) < 3: continue
                checked += 1
                s = sim(a, b)
                ca, cb = collections.Counter(w for w in a if w not in STOPG), collections.Counter(w for w in b if w not in STOPG)
                only = sum((ca - cb).values()) + sum((cb - ca).values())
                if s < SIM and only >= MINW:
                    flagged.append([bk['id'], c, v[0], round(s, 2), only, ' '.join(t[0] for t in v[1]), GB[k]])
                    if write and s < 0.3 and not st:   # Brenton's verse is essentially a different passage: hide the English
                        v[2] = None; v.append({'s': 'h'}); ch = True; flagged[-1].append('hidden'); continue
                    if write:
                        if st: st['gd'] = round(s, 2)
                        else: v.append({'s': 'd', 'q': round(s, 2)})
                        ch = True
            if ch and write: json.dump(vs, open(p, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    json.dump({'checked': checked, 'sim': SIM, 'minw': MINW, 'flagged': flagged}, open(os.path.join(HERE, 'greekdiff_log.json'), 'w'), ensure_ascii=False, indent=0)
    print('greekdiff: checked', checked, 'flagged', len(flagged))
    return flagged
if __name__ == '__main__':
    import sys; run(write='--dry' not in sys.argv)
