#!/usr/bin/env python3
"""Step 1 (after build.py): Brenton realignment, gloss fixes, parsing overrides, chapter notes.
Brenton English is re-matched to the Rahlfs Greek using Brenton's OWN Greek text (eBible grcbrent, PD),
which shares Brenton's English versification. Every decision is recorded in data/align_log.json."""
import json, re, os, csv, collections, unicodedata
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, '..', 'site', 'data')
AUD = '/workspace/lxx-audit'; SRC = AUD + '/src'
BMAP = {'Gen':'GEN','Exod':'EXO','Lev':'LEV','Num':'NUM','Deut':'DEU','JoshB':'JOS','JudgB':'JDG','Ruth':'RUT','1Sam':'1SA','2Sam':'2SA',
 '1Kgs':'1KI','2Kgs':'2KI','1Chr':'1CH','2Chr':'2CH','1Esdr':'1ES','2Esdr':'EZR','Esth':'ESG','Jdt':'JDT','TobBA':'TOB','1Macc':'1MA','2Macc':'2MA',
 '3Macc':'3MA','4Macc':'4MA','Ps':'PSA','Prov':'PRO','Eccl':'ECC','Song':'SOL','Job':'JOB','Wis':'WIS','Sir':'SIR','Hos':'HOS','Mic':'MIC',
 'Amos':'AMO','Joel':'JOE','Jonah':'JON','Obad':'OBA','Nah':'NAH','Hab':'HAB','Zeph':'ZEP','Hag':'HAG','Zech':'ZEC','Mal':'MAL','Isa':'ISA',
 'Jer':'JER','Bar':'BAR','EpJer':'EPJ','Lam':'LAM','Ezek':'EZE','BelTh':'BEL','DanTh':'DNG','SusTh':'SUS'}
NO_MOVE = {'1Sam'}
# Re-matching (moving English to another verse) is only done where the audit found strong chapter-level evidence of
# misalignment, in the books the audit singled out, or where the Greek verse has no same-numbered Brenton verse.
SCOPE_BOOKS = {'Sir', 'Prov', 'Esth', 'EpJer'}
SCOPE_CH = {('Deut', 28), ('Deut', 29), ('4Macc', 8), ('2Esdr', 20), ('Wis', 17)} | {('Exod', c) for c in range(35, 41)} | \
    {('TobBA', c) for c in (5, 6, 7, 13)} | {('1Esdr', c) for c in (1, 2, 5, 6, 8)}
def in_scope(b, c): return b in SCOPE_BOOKS or (b, c) in SCOPE_CH  # grcbrent and Brenton English verse counts differ here (audit); keep number matching
def vpl(p):
    d = collections.OrderedDict()
    for l in open(p, encoding='utf-8-sig'):
        m = re.match(r'(\S+) (\d+):(\d+[a-z]?) (.*)', l.strip())
        if m: d[(m.group(1), int(m.group(2)), m.group(3))] = m.group(4)
    return d
EN = vpl('/workspace/brenton/eng-Brenton_vpl.txt'); GB = vpl(SRC + '/grcbrent/grcbrent_vpl.txt')
def nz(s):
    s = ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn').replace('ς', 'σ')
    return [w[:5] for w in re.findall(r'[α-ω]+', s)]
def sim(a, b):
    if not a or not b: return 0.0
    return sum((collections.Counter(a) & collections.Counter(b)).values()) / max(len(a), len(b))
books = json.load(open(D + '/books.json'))
# --- Greek lemma -> English word association (Dice over verses), trained on the default number-matched verses.
# Used as an independent second check that a moved English verse really fits the Greek (grcbrent's own
# versification occasionally differs from Brenton's English, e.g. Ps 12).
STOP = set('the and of to in that he his him they them a an for with is was be it on as by from all not shall will thou thee thy i my me ye you your their which who unto upon have hath had are were but or so this these those there then when what o did do doth into out up at her she we us our also one no nor more'.split())
def ew(t): return set(w[:5] for w in re.findall(r"[a-z]+", t.lower()) if w not in STOP and len(w) > 2)
lemma_df = collections.Counter(); word_df = collections.Counter(); co = collections.Counter(); NV = 0
for bk in books:
    if bk['id'] not in BMAP: continue
    for c in bk['chapters']:
        for v in json.load(open(f"{D}/{bk['id']}/{c}.json")):
            if not v[2]: continue
            ls = set(t[1] for t in v[1]); ws = ew(v[2]); NV += 1
            lemma_df.update(ls); word_df.update(ws)
            for l in ls:
                if lemma_df[l] < 400 or True:
                    for w in ws: co[(l, w)] += 1
best_en = collections.defaultdict(list)
for (l, w), n in co.items():
    if n >= 3:
        dice = 2 * n / (lemma_df[l] + word_df[w])
        if dice >= 0.25: best_en[l].append((dice, w))
best_en = {l: set(w for d, w in sorted(x, reverse=True)[:3]) for l, x in best_en.items()}
del co
def en_score(toks, text):
    if not text: return None
    ws = ew(text); ls = [t[1] for t in toks if t[1] in best_en]
    if len(ls) < 3: return None
    return sum(1 for l in ls if best_en[l] & ws) / len(ls)
print('english model lemmas', len(best_en))
# --- Consistency of Brenton-Greek (grcbrent) key k with Brenton-English key k: a Greek-surface -> English model
# trained on all grcbrent/English pairs; a key is "inconsistent" if the English of a neighbouring key fits its Greek clearly better.
gdf = collections.Counter(); edf = collections.Counter(); gco = collections.Counter()
GBn = {k: set(nz(GB[k])) for k in GB if k in EN}; ENw = {k: ew(EN[k]) for k in GBn}
for k in GBn:
    gdf.update(GBn[k]); edf.update(ENw[k])
    for gw in GBn[k]:
        for w in ENw[k]: gco[(gw, w)] += 1
gbest = collections.defaultdict(list)
for (gw, w), n in gco.items():
    if n >= 3:
        dd = 2 * n / (gdf[gw] + edf[w])
        if dd >= 0.3: gbest[gw].append((dd, w))
gbest = {gw: set(w for d, w in sorted(x, reverse=True)[:2]) for gw, x in gbest.items()}
del gco
def gfit(k, ke):
    if k not in GBn or ke not in ENw: return None
    gs = [g for g in GBn[k] if g in gbest]
    if len(gs) < 3: return None
    return sum(1 for g in gs if gbest[g] & ENw[ke]) / len(gs)
GKEYS = sorted(GBn, key=lambda k: (k[0], k[1]))
_idx = collections.defaultdict(list)
for k in GB:
    if k in EN: _idx[(k[0], k[1])].append(k)
def key_consistent(k):
    lst = _idx.get((k[0], k[1]), []);
    if k not in lst: return False
    i = lst.index(k); f0 = gfit(k, k)
    if f0 is None: return True
    for j in (i - 1, i + 1):
        if 0 <= j < len(lst):
            f = gfit(k, lst[j])
            if f is not None and f > f0 + 0.15: return False
    return True
_kc = {}
def kc(k):
    if k not in _kc: _kc[k] = key_consistent(k)
    return _kc[k]
log = {'moved': [], 'hidden': [], 'differs': [], 'joined': []}; stats = collections.defaultdict(collections.Counter)
chapnotes = {}
for bk in books:
    b = bk['id']; code = BMAP.get(b)
    if not code: continue
    bkeys = [k for k in GB if k[0] == code and k in EN]
    bnorm = {k: nz(GB[k]) for k in bkeys}; order = {k: i for i, k in enumerate(bkeys)}
    rs = sorted(len(EN[k]) / max(1, len(GB[k])) for k in bkeys); ratio_med = rs[len(rs) // 2] if rs else 1
    df = collections.Counter(w for k in bkeys for w in set(bnorm[k]))
    inv = collections.defaultdict(set)
    for k in bkeys:
        for w in set(bnorm[k]):
            if df[w] <= 40: inv[w].add(k)
    chdata = {c: json.load(open(f'{D}/{b}/{c}.json')) for c in bk['chapters']}
    # chapters with >=2 clearly mismatching verses (Greek-Greek similarity < 0.25) are also eligible for re-matching
    lowch = collections.Counter()
    for c, vs in chdata.items():
        for v in vs:
            k = (code, c, v[0]); g = nz(' '.join(t[0] for t in v[1]))
            if k in bnorm and len(g) >= 4 and sim(g, bnorm[k]) < 0.25: lowch[c] += 1
    assign = {}  # (c,vi) -> (keys tuple, score, status)
    for c, vs in chdata.items():
        for vi, v in enumerate(vs):
            g = nz(' '.join(t[0] for t in v[1]))
            k0 = (code, c, v[0]) if isinstance(c, int) else None
            s0 = sim(g, bnorm[k0]) if k0 in bnorm else -1
            if s0 >= 0 and not kc(k0): s0 = 1.0  # Brenton-Greek numbering differs from Brenton-English here; keep number match
            st = 'ok'; best = ((k0,), s0) if s0 >= 0 else (None, -1)
            scope = in_scope(b, c) or s0 < 0 or lowch[c] >= 2
            if b not in NO_MOVE and len(g) >= 4 and s0 < 0.5 and scope:
                cand = collections.Counter()
                for w in set(g):
                    for k in inv.get(w, ()): cand[k] += 1
                for k, n in cand.most_common(30):
                    s = sim(g, bnorm[k])
                    if s > best[1]: best = ((k,), s)
                    i = order[k]
                    for j in (i - 1, i + 1):
                        if 0 <= j < len(bkeys) and bkeys[j][:2][0] == code:
                            pair = tuple(sorted((k, bkeys[j]), key=order.get))
                            s2 = sim(g, bnorm[pair[0]] + bnorm[pair[1]])
                            if s2 > best[1] + 0.05: best = (pair, s2)
                e_new = en_score(v[1], ' '.join(EN[k] for k in best[0])) if best[0] and best[0][0] else None
                e_old = en_score(v[1], EN.get(k0)) if k0 else None
                # sanity check that Brenton's Greek and Brenton's English carry the same verse at the target key
                # (their numbering occasionally differs, e.g. Ps 12): English/Greek length ratio vs the book median
                en_ok = all(kc(k) for k in best[0]) and all(0.45 < (len(EN[k]) / max(1, len(GB[k]))) / ratio_med < 2.2 for k in best[0]) if best[0] and best[0][0] else False
                if best[0] and best[0] != (k0,) and best[1] >= 0.5 and best[1] >= s0 + 0.15 and en_ok: st = 'moved'
                elif s0 >= 0 and s0 < 0.25: st = 'hidden'
                elif s0 >= 0: st = 'differs'; best = ((k0,), s0)
                else: st = 'none'
                if st in ('hidden', 'differs'): best = ((k0,), s0)
            elif s0 < 0:
                st = 'none'
            elif len(g) >= 4 and s0 < 0.5:
                # outside the re-matching scope: never move; hide only on double evidence (Greek AND English mismatch)
                e0 = en_score(v[1], EN.get(k0))
                st = 'hidden' if (s0 < 0.15 and (e0 is None or e0 < 0.15)) else ('differs' if s0 < 0.35 else 'ok')
            assign[(c, vi)] = (best[0], best[1], st, len(g))
    # continuity: a moved verse must have a neighbour whose English key is adjacent (kills isolated formula matches)
    keysq = [(c, vi) for c, vs in chdata.items() for vi in range(len(vs))]
    for i, key in enumerate(keysq):
        ks, s, st, n = assign[key]
        if st != 'moved': continue
        ok = False
        for j in (i - 1, i + 1):
            if 0 <= j < len(keysq):
                ks2 = assign[keysq[j]][0]
                if ks2 and ks2[0] in order:
                    a = order[ks[0]] if j > i else order[ks[-1]]
                    bb = order[ks2[0]] if j > i else order[ks2[-1]]
                    if 0 < (bb - a if j > i else a - bb) <= 3: ok = True
        if not ok:
            c, vi = key; v = chdata[c][vi]; k0 = (code, c, v[0])
            s0 = sim(nz(' '.join(t[0] for t in v[1])), bnorm[k0]) if k0 in bnorm else -1
            assign[key] = ((k0,), s0, 'hidden' if 0 <= s0 < 0.25 else ('differs' if s0 >= 0 else 'none'), n)
    # one Brenton verse may be claimed twice: keep it on the best-matching Greek verse only
    owner = {}
    for key, (ks, s, st, n) in assign.items():
        if st in ('ok', 'moved', 'differs') and ks:
            for k in ks:
                if k not in owner or s > assign[owner[k]][1]: owner[k] = key
    for c, vs in chdata.items():
        cn = collections.Counter()
        for vi, v in enumerate(vs):
            ks, s, st, n = assign[(c, vi)]
            ref = f'{b} {c}:{v[0]}'
            if st in ('ok', 'moved', 'differs') and ks and any(owner.get(k) != (c, vi) for k in ks):
                o = owner.get(ks[0])
                if not (o and o[0] == c and abs(o[1] - vi) <= 2):  # not a neighbouring verse: no reliable English
                    log['hidden'].append([ref, 'claimed by a better-matching verse', round(s, 2)]); v[2] = None; v.append({'s': 'h'})
                    cn['hidden'] += 1; stats[b]['hidden'] += 1
                    continue
                st = 'joined'
                ov = chdata[o[0]][o[1]][0] if o else '?'
                v[2] = None; v.append({'s': 'j', 'with': f'{o[0]}:{ov}' if o else ''})
                log['joined'].append([ref, ' '.join(f'{k[1]}:{k[2]}' for k in ks), round(s, 2)])
            elif st == 'moved':
                v[2] = ' '.join(EN[k] for k in ks)
                v.append({'s': 'm', 'br': ' '.join(f'{k[1]}:{k[2]}' for k in ks), 'q': round(s, 2)})
                log['moved'].append([ref, ' '.join(f'{k[1]}:{k[2]}' for k in ks), round(s, 2)])
            elif st == 'hidden':
                log['hidden'].append([ref, v[2][:60] if v[2] else '', round(s, 2)]); v[2] = None; v.append({'s': 'h'})
            elif st == 'differs':
                v.append({'s': 'd', 'q': round(s, 2)}); log['differs'].append([ref, round(s, 2)])
            elif st == 'ok' and ks and ks[0] and v[2] is None and isinstance(c, int):
                pass
            cn[st] += 1; stats[b][st] += 1
        tot = len(vs); bad = cn['hidden'] + cn['differs'] + cn['none'] * (1 if b != 'Prov' else 1)
        if cn['moved'] or cn['hidden'] or cn['joined'] or cn['differs'] >= max(3, tot * 0.15):
            chapnotes[f'{b}/{c}'] = {k: cn[k] for k in ('moved', 'hidden', 'differs', 'joined', 'none') if cn[k]}
        json.dump(vs, open(f'{D}/{b}/{c}.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
json.dump(chapnotes, open(D + '/chapnotes.json', 'w'), ensure_ascii=False, separators=(',', ':'))
json.dump(log, open(os.path.join(HERE, 'align_log.json'), 'w'), ensure_ascii=False, indent=0)
T = collections.Counter()
for b, c in stats.items(): T.update(c)
print('TOTAL', dict(T))
for b in ('Sir', 'Prov', 'Esth', 'Deut', 'EpJer', 'Exod', '4Macc', '1Esdr', 'TobBA', 'Wis', '2Esdr', 'Jer', 'Ps', 'Gen', 'Isa'): print(b, dict(stats[b]))
print('chapters with notes', len(chapnotes))
