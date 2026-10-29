#!/usr/bin/env python3
"""Word-level Greek -> Latin (Vulgate) alignment for verse pairs already matched by tools/vulgate.py.
Approaches (evaluated against tools/gold_latin.py):
  A  Dice co-occurrence (Greek lemma x Latin lemma) + diagonal position prior
  B  IBM Model 1, Latin->Greek direction, + diagonal prior
  C  IBM Model 1 in both directions + diagonal prior, combined posterior (product), competitive by verse
Latin lemmas/parses: Wiktionary (kaikki.org Wiktextract, CC BY-SA 4.0) via tools/latmorph.py."""
import json, os, re, sys, math, collections, unicodedata
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, '..', 'site', 'data'); sys.path.insert(0, HERE)
MORPH = json.load(open('/workspace/src/latmorph.json')); GM = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'site', 'data', 'morph.json'))); books = json.load(open(D + '/books.json'))
LEX = json.load(open(D + '/lexicon.json')); MT = json.load(open(D + '/morph.json')) if os.path.exists(D + '/morph.json') else None
def lnorm(w):
    w = unicodedata.normalize('NFD', w.lower()); w = ''.join(c for c in w if unicodedata.category(c) != 'Mn')
    return w.replace('æ', 'ae').replace('œ', 'oe').replace('j', 'i').replace('v', 'u')
nforms = collections.Counter()
for f, an in MORPH.items():
    for a in an: nforms[a[0]] += 1
def analyse(w):
    """-> (lemma, enclitic, analyses)"""
    k = lnorm(w); enc = ''
    if k not in MORPH:
        for e in ('que', 'ne', 've'):
            if k.endswith(e) and k[:-len(e)] in MORPH: k, enc = k[:-len(e)], e; break
    an = MORPH.get(k)
    if not an: return k, enc, []
    lem = max({a[0] for a in an}, key=lambda l: (nforms[l], l))
    return lem, enc, [a for a in an if a[0] == lem]
def ltok(text): return re.findall(r"[A-Za-zÆæŒœëÉéÈè]+", text)
# ---- corpus
pairs = []  # (book, ch, v, greek tokens, latin surface list, latin lemma list)
for bk in books:
    for c in bk['chapters']:
        try: vu = json.load(open(f"{D}/vul/{bk['id']}/{c}.json"))
        except FileNotFoundError: continue
        for v in json.load(open(f"{D}/{bk['id']}/{c}.json")):
            vd = vu.get(v[0])
            if not vd: continue
            ls = ltok(vd[0]); an = [analyse(w) for w in ls]
            pairs.append((bk['id'], c, v[0], v[1], ls, [x[0] for x in an], [(x[2][0][1] if x[2] else '?') for x in an]))
print(len(pairs), 'verse pairs', file=sys.stderr)
GAPMAX = int(os.environ.get('GAPMAX', 1))
def diag(i, m, j, n, lam=4.0): return math.exp(-lam * abs((i + .5) / m - (j + .5) / n))
def ibm1(src_of, tgt_of, iters=6):
    """t[(s, t)] = p(t | s); src includes NULL."""
    t = collections.defaultdict(lambda: 1e-3); tot_init = True
    for it in range(iters):
        cnt = collections.Counter(); tot = collections.Counter()
        for p in pairs:
            S = ['<NULL>'] + src_of(p); T = tgt_of(p); n = len(S)
            for x in T:
                ws = [t[(s, x)] if not tot_init else 1.0 for s in S]; z = sum(ws)
                for s, w in zip(S, ws): cnt[(s, x)] += w / z; tot[s] += w / z
        t = collections.defaultdict(lambda: 1e-7, {k: v / tot[k[0]] for k, v in cnt.items() if v / tot[k[0]] > 1e-4}); tot_init = False
        print('ibm1 iter', it, len(t), file=sys.stderr)
    return t
G = lambda p: [str(x[1]) for x in p[3]]; L = lambda p: p[5]
def dice_model():
    gd = collections.Counter(); ld = collections.Counter(); co = collections.Counter()
    for p in pairs:
        gs, ls = set(G(p)), set(L(p)); gd.update(gs); ld.update(ls)
        for g in gs:
            for l in ls: co[(g, l)] += 1
    return {k: 2 * n / (gd[k[0]] + ld[k[1]]) for k, n in co.items() if n >= 2}
def align_verse(p, method, M):
    """-> list per Greek token: (latin index or None, confidence)."""
    gs, ls = G(p), L(p); m, n = len(gs), len(ls); out = []
    if not n: return [(None, 0)] * m
    if method == 'A':
        for i, g in enumerate(gs):
            sc = [M['dice'].get((g, l), 0) * (.5 + .5 * diag(i, m, j, n)) for j, l in enumerate(ls)]
            j = max(range(n), key=sc.__getitem__); out.append((j, sc[j]))
        return out
    tg = M['t_lg']  # p(greek | latin)
    P = [[tg[(l, g)] * diag(i, m, j, n) for j, l in enumerate(ls)] for i, g in enumerate(gs)]
    if method == 'B':
        for i, g in enumerate(gs):
            z = sum(P[i]) + tg[('<NULL>', g)] * .2; j = max(range(n), key=P[i].__getitem__); out.append((j, P[i][j] / z))
        return out
    tl = M['t_gl']  # p(latin | greek)
    Q = [[tl[(g, l)] * diag(i, m, j, n) for i, g in enumerate(gs)] for j, l in enumerate(ls)]
    qz = [sum(Q[j]) + tl[('<NULL>', ls[j])] * .2 for j in range(n)]
    S = []
    for i, g in enumerate(gs):
        z = sum(P[i]) + tg[('<NULL>', g)] * .2
        S.append([math.sqrt((P[i][j] / z) * (Q[j][i] / qz[j])) for j in range(n)])
    if method == 'C':
        for i in range(m): j = max(range(n), key=S[i].__getitem__); out.append((j, S[i][j]))
        return out
    art = [LEX.get(g, ['', '', ''])[0] == 'ὁ' for g in gs] if method == 'E' else [False] * m
    # D: competitive linking - strongest links first, each Latin token used once
    out = [(None, 0)] * m; usedg, usedl = set(), set()
    for s, i, j in sorted(((S[i][j], i, j) for i in range(m) for j in range(n)), reverse=True):
        if s < 1e-3: break
        if i in usedg or j in usedl or art[i]: continue
        out[i] = (j, s); usedg.add(i); usedl.add(j)
    if method == 'E':
        for i in range(m):
            if out[i][0] is not None and out[i][1] < 0.05: usedl.discard(out[i][0]); out[i] = (None, 0)
    if method == 'E':  # gap fill: one unlinked Greek content word between two links <-> one unlinked Latin content word between them
        CONT = ('Noun', 'Verb', 'Adjective', 'Adverb', 'Proper')
        gcode = lambda i: GM[p[3][i][2]][0] if isinstance(p[3][i][2], int) and p[3][i][2] < len(GM) else ''
        isc = lambda i: not art[i] and gcode(i)[:1] in ('N', 'V', 'A', 'M') and not gcode(i).startswith('RA')
        LC = ('noun', 'verb', 'adj', 'adv', 'name', 'num', 'participle', '?')
        for i in range(m):
            if out[i][0] is not None or not isc(i): continue
            l = next((k for k in range(i - 1, -1, -1) if out[k][0] is not None and out[k][1] > .3), None)
            r = next((k for k in range(i + 1, m) if out[k][0] is not None and out[k][1] > .3), None)
            if l is None or r is None: continue
            jl, jr = out[l][0], out[r][0]
            if not jl < jr: continue
            gfree = [k for k in range(l + 1, r) if out[k][0] is None and isc(k)]
            lfree = [j for j in range(jl + 1, jr) if j not in usedl and p[6][j] in LC]
            gc = gcode(i)[:1]
            ok_pos = lambda lp: lp == '?' or (gc == 'V' and lp in ('verb', 'participle')) or (gc == 'N' and lp in ('noun', 'name')) or \
                (gc == 'A' and lp in ('adj', 'participle', 'num', 'noun')) or (gc == 'M' and lp in ('num', 'adj'))
            if len(lfree) == 1 and (not ok_pos(p[6][lfree[0]]) or p[5][lfree[0]] == 'sum' or S[i][lfree[0]] < float(os.environ.get('GAPMIN', 1e-4))): continue
            if len(gfree) == len(lfree) and 1 <= len(gfree) <= GAPMAX:
                for gk, lj in zip(gfree, lfree): out[gk] = (lj, -1.0); usedl.add(lj)   # -1 marks a structural (gap) link
    return out
def gold_eval(method, M, verbose=False):
    from gold_latin import GOLD
    idx = {(p[0], p[1], p[2]): p for p in pairs}; res = []
    for b, c, v, form, occ, gold in GOLD:
        p = idx.get((b, c, str(v)))
        if not p: res.append((None, 0, gold, '?')); continue
        al = align_verse(p, method, M); nf = lambda s: re.sub(r'\W', '', unicodedata.normalize('NFC', s).replace('\u1fbd', ''))
        ks = [i for i, t in enumerate(p[3]) if nf(t[0]) == nf(form)]
        if len(ks) < occ: print('NOT FOUND', b, c, v, form, [t[0] for t in p[3]]); continue
        k = ks[occ - 1]
        j, conf = al[k]; pred = p[4][j] if j is not None else None
        res.append((pred, conf, gold, form))
        if verbose: print(f'{b} {c}:{v} {form:14} -> {pred!s:14} {conf:.3f}  gold {gold}  {"OK" if pred == gold else "XX"}')
    return res
def report(name, res):
    print(f'== {name}: raw accuracy {sum(r[0] == r[2] for r in res)}/{len(res)}')
    for th in (0, .05, .1, .2, .3, .4, .5, .6):
        shown = [r for r in res if (r[1] >= th or r[1] == -1) and r[0] is not None]
        ok = sum(r[0] == r[2] for r in shown)
        print(f'   threshold {th:.2f}: shown {len(shown):3}/{len(res)}  precision {ok}/{len(shown)} = {ok / max(1, len(shown)):.2f}')
if __name__ == '__main__':
    import pickle
    cache = '/workspace/src/latalign_models.pkl'
    if os.path.exists(cache) and '--retrain' not in sys.argv: M = pickle.load(open(cache, 'rb'))
    else:
        M = {'dice': dice_model(), 't_lg': dict(ibm1(L, G)), 't_gl': dict(ibm1(G, L))}
        pickle.dump(M, open(cache, 'wb'))
    M['t_lg'] = collections.defaultdict(lambda: 1e-7, M['t_lg']); M['t_gl'] = collections.defaultdict(lambda: 1e-7, M['t_gl'])
    if '--eval' in sys.argv:
        for meth in 'CDE': report(meth, gold_eval(meth, M, verbose='-v' in sys.argv and meth == sys.argv[-1]))
def debug(b, c, v, M):
    p = [p for p in pairs if (p[0], p[1], p[2]) == (b, c, str(v))][0]
    for meth in 'DE':
        al = align_verse(p, meth, M)
        print(meth, ' '.join(f'{t[0]}={p[4][j] if j is not None else "-"}:{s:.2f}' for t, (j, s) in zip(p[3], al)))
if __name__ == '__main__' and '--debug' in sys.argv:
    a = sys.argv[sys.argv.index('--debug') + 1].split(); debug(a[0], int(a[1]), a[2], M)
# ---------------- export for the site ----------------
GAPMAX = int(os.environ.get('GAPMAX', 1))
THRESH = 0.05   # set from the gold sample: precision 0.98 at >= 0.05 (gap links included)
CASES = ['nominative', 'genitive', 'dative', 'accusative', 'ablative', 'vocative', 'locative']
PREP = {'in': {'ablative', 'accusative'}, 'sub': {'ablative', 'accusative'}, 'super': {'ablative', 'accusative'}, 'ad': {'accusative'},
        'per': {'accusative'}, 'propter': {'accusative'}, 'ante': {'accusative'}, 'post': {'accusative'}, 'inter': {'accusative'}, 'contra': {'accusative'},
        'apud': {'accusative'}, 'secundum': {'accusative'}, 'circa': {'accusative'}, 'usque': {'accusative'}, 'iuxta': {'accusative'}, 'trans': {'accusative'},
        'de': {'ablative'}, 'ex': {'ablative'}, 'e': {'ablative'}, 'a': {'ablative'}, 'ab': {'ablative'}, 'abs': {'ablative'}, 'cum': {'ablative'},
        'sine': {'ablative'}, 'pro': {'ablative'}, 'prae': {'ablative'}, 'coram': {'ablative'}}
GMAP = {'nominative': {'nominative'}, 'genitive': {'genitive'}, 'dative': {'dative', 'ablative'}, 'accusative': {'accusative'}, 'vocative': {'vocative', 'nominative'}}
def describe(an, gtext, prev):
    """Pick the analyses compatible with the Latin context and the Greek case; return plain-English parse."""
    if not an: return ''
    full = [a for a in an if a[2]] or an
    keep = full
    if prev in PREP and any(c in a[2] for a in keep for c in CASES):
        k2 = [a for a in keep if set(a[2]) & PREP[prev]]; keep = k2 or keep
    gc = next((c for c in GMAP if c in gtext.lower()), None)
    if gc:
        k2 = [a for a in keep if not any(c in a[2] for c in CASES) or set(a[2]) & GMAP[gc]]; keep = k2 or keep
    gl = gtext.lower()
    for moods in (('indicative',), ('subjunctive',), ('imperative',), ('infinitive',), ('participle',), ('optative', 'subjunctive')):
        if moods[0] in gl:
            k2 = [a for a in keep if any(md in a[2] for md in moods)]; keep = k2 or keep; break
    TM = {'future': 'future', 'present': 'present', 'imperfect': 'imperfect', 'aorist': 'perfect', 'perfect': 'perfect', 'pluperfect': 'pluperfect'}
    gt = next((TM[x] for x in ('pluperfect', 'imperfect', 'future', 'present', 'aorist', 'perfect') if x in gl), None)
    if gt:
        k2 = [a for a in keep if gt in a[2] and not (gt == 'perfect' and ('pluperfect' in a[2] or 'future-perfect' in a[2]))]; keep = k2 or keep
    if all(a[1] == 'name' for a in keep): return ''
    def one(a):
        t = a[2]; pos = a[1]
        if pos == 'verb' or 'participle' in t or 'infinitive' in t:
            tense = next((x for x in ('present', 'imperfect', 'future-perfect', 'future', 'pluperfect', 'perfect') if x in t), '')
            voice = 'passive' if 'passive' in t else ('active' if 'active' in t else '')
            mood = next((x for x in ('indicative', 'subjunctive', 'imperative', 'infinitive', 'participle', 'gerundive', 'gerund', 'supine') if x in t), '')
            per = next((x.replace('first-person', '1st person').replace('second-person', '2nd person').replace('third-person', '3rd person') for x in t if x.endswith('-person')), '')
            num = next((x for x in ('singular', 'plural') if x in t), '')
            head = ' '.join(x for x in (tense.replace('-', ' '), voice, mood) if x)
            if mood == 'participle' or mood == 'gerundive':
                cs = ' '.join(x for x in [next((c for c in CASES if c in t), ''), num, next((g for g in ('masculine', 'feminine', 'neuter') if g in t), '')] if x)
                return head + (', ' + cs if cs else '')
            tail = ' '.join(x for x in (per, num) if x)
            return head + (', ' + tail if tail else '')
        c = next((c for c in CASES if c in t), ''); num = next((x for x in ('singular', 'plural') if x in t), '')
        g = next((g for g in ('masculine', 'feminine', 'neuter') if g in t), '') or (a[5] if pos == 'noun' else '')
        deg = next((x for x in ('comparative', 'superlative') if x in t), '')
        return ' '.join(x for x in (deg, c, num, g) if x)
    ds = []
    for a in keep:
        d = one(a)
        if d and d not in ds: ds.append(d)
    ds = [d for d in ds if not any(o != d and o.startswith(d) for o in ds)]
    if len(ds) > 1:   # merge "dative singular neuter" / "ablative singular neuter" -> "dative or ablative singular neuter"
        tails = {d.split(' ', 1)[1] if ' ' in d else '' for d in ds}
        heads = [d.split(' ', 1)[0] for d in ds]
        if len(tails) == 1 and all(h in CASES for h in heads): return ' or '.join(heads) + ' ' + tails.pop()
        return ' / '.join(ds[:2])
    return ds[0] if ds else ''
def export(M):
    gm = json.load(open(D + '/morph.json')); latlex = {}; n_tok = n_shown = 0
    by = collections.defaultdict(dict)
    for p in pairs:
        al = align_verse(p, 'E', M); row = []
        for k, (tok, (j, s)) in enumerate(zip(p[3], al)):
            n_tok += 1
            if LEX.get(str(tok[1]), [''])[0] == 'ὁ': row.append(0); continue
            if j is None or not (s >= THRESH or s == -1): row.append(None); continue
            w = p[4][j]; lem, enc, an = analyse(w)
            prev = lnorm(p[4][j - 1]) if j else ''
            gtext = gm[tok[2]][1] if isinstance(tok[2], int) and tok[2] < len(gm) else ''
            if an:
                a0 = an[0]; key = a0[4]; latlex.setdefault(key, [a0[1], a0[3], a0[5]])
            else: key = ''
            row.append([w[:-len(enc)] if enc else w, key, describe(an, gtext, prev), -1 if s == -1 else int(round(min(s, 1) * 100)), j])
            n_shown += 1
        by[(p[0], p[1])][p[2]] = row
    for (b, c), d in by.items():
        os.makedirs(f'{D}/latw/{b}', exist_ok=True); json.dump(d, open(f'{D}/latw/{b}/{c}.json', 'w'), ensure_ascii=False, separators=(',', ':'))
    json.dump(latlex, open(D + '/latlex.json', 'w'), ensure_ascii=False, separators=(',', ':'))
    json.dump({'threshold': THRESH, 'tokens': n_tok, 'shown': n_shown, 'lemmas': len(latlex)}, open(D + '/latw_summary.json', 'w'))
    print('export: tokens', n_tok, 'with a Latin word', n_shown, 'latin lemmas', len(latlex))
if __name__ == '__main__' and '--export' in sys.argv: export(M)

GAPSAMPLE = [('Isa',50,'2','ὑπακούων','audiret',1),('Jer',10,'23','οὐχὶ','est',0),('Isa',14,'9','βασιλεῖς','principes',1),('Isa',50,'1','ποῖον','est',0),('Isa',22,'23','στήσω','figam',1),
('Jer',8,'16','φωνὴν','est',0),('Exod',6,'6','ἀπὸ','de',1),('Exod',28,'38','ἁγίων','donariis',0),('Isa',46,'13','βραδυνῶ','morabitur',1),('Isa',36,'5','ἀπειθεῖς','recessisti',1),
('Deut',28,'53','θλίψει','vastitate',1),('Deut',10,'18','ἄρτον','victum',1),('Exod',23,'5','συνεγερεῖς','sublevabis',1),('Gen',43,'5','οὐκ','Non',1),('Isa',60,'7','ἥξουσίν','ministrabunt',0),
('Ps',79,'9','μετῆρας','transtulisti',1),('Gen',19,'29','περιοίκου','regionis',1),('Gen',36,'17','ἡγεμόνες','duces',1),('Isa',19,'20','αἰῶνα','testimonium',0),('Deut',32,'7','αἰῶνος','antiquorum',1)]
if __name__ == '__main__' and '--gapeval' in sys.argv:
    idx = {(p[0], p[1], p[2]): p for p in pairs}; kept = good = 0
    for b, c, v, gf, lw, ok in GAPSAMPLE:
        p = idx[(b, c, v)]; al = align_verse(p, 'E', M); k = [i for i, t in enumerate(p[3]) if t[0] == gf][0]; j, s = al[k]
        still = j is not None and p[4][j] == lw
        kept += still; good += still and ok
        print(gf, lw, 'kept' if still else 'dropped', 'correct' if ok else 'WRONG')
    print('gap sample: kept', kept, 'correct among kept', good)
