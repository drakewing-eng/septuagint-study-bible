#!/usr/bin/env python3
"""Step 4: Clementine Vulgate (PD, eBible latVUC) + Douay-Rheims (PD, eBible engDRA) per LXX verse, with an honest
verse-level confidence check, and an APPROXIMATE 'the Vulgate often renders this word as ...' table.
Method: a Greek-lemma -> Latin-stem association model (Dice coefficient over verse pairs) is trained on books whose
LXX and Vulgate verse numbers agree well; every candidate verse pair is then scored by the share of the Greek verse's
content words whose usual Latin equivalents appear in the Latin verse. Pairs below a threshold calibrated on
deliberately WRONG pairs (99th percentile) are not shown."""
import json, os, re, collections, unicodedata, random
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, '..', 'site', 'data'); SRC = '/workspace/lxx-audit/src'
books = json.load(open(D + '/books.json')); lex = json.load(open(D + '/lexicon.json'))
def vpl(p):
    d = {}
    for l in open(p, encoding='utf-8-sig'):
        m = re.match(r'(\S+) (\d+):(\d+) (.*)', l.strip())
        if m: d[(m.group(1), int(m.group(2)), int(m.group(3)))] = m.group(4)
    return d
VU = vpl(SRC + '/latVUC/latVUC_vpl.txt'); DR = vpl(SRC + '/engDRA/engDRA_vpl.txt')
VB = {'Gen':'GEN','Exod':'EXO','Lev':'LEV','Num':'NUM','Deut':'DEU','JoshB':'JOS','JudgB':'JDG','Ruth':'RUT','1Sam':'1SA','2Sam':'2SA',
 '1Kgs':'1KI','2Kgs':'2KI','1Chr':'1CH','2Chr':'2CH','Esth':'EST','Jdt':'JDT','TobBA':'TOB','1Macc':'1MA','2Macc':'2MA','Ps':'PSA',
 'Prov':'PRO','Eccl':'ECC','Song':'SOL','Job':'JOB','Wis':'WIS','Sir':'SIR','Hos':'HOS','Mic':'MIC','Amos':'AMO','Joel':'JOE','Jonah':'JON',
 'Obad':'OBA','Nah':'NAH','Hab':'HAB','Zeph':'ZEP','Hag':'HAG','Zech':'ZEC','Mal':'MAL','Isa':'ISA','Jer':'JER','Bar':'BAR','Lam':'LAM',
 'Ezek':'EZE','DanTh':'DAN','EpJer':'BAR','SusTh':'DAN','BelTh':'DAN','2Esdr':'EZR', 'JoshA':'JOS', 'JudgA':'JDG', 'TobS':'TOB', 'DanOG':'DAN', 'SusOG':'DAN', 'BelOG':'DAN'}
def base(b, c, v):
    """LXX (Rahlfs) reference -> Vulgate reference before local offset search."""
    code = VB.get(b)
    if not code or not isinstance(c, int): return None
    if b == 'EpJer': c = 6
    if b in ('SusTh', 'SusOG'): c = 13
    if b in ('BelTh', 'BelOG'): c = 14
    if b == '2Esdr' and c > 10: code, c = 'NEH', c - 10
    if b == 'Joel' and c == 3: c, v = 2, v + 27
    elif b == 'Joel' and c == 4: c = 3
    if b == 'Mal' and c == 3 and v >= 19: c, v = 4, v - 18
    return (code, c, v)
TRAIN = {'Gen','Exod','Lev','Num','Deut','JoshB','JudgB','Ruth','2Sam','2Kgs','1Chr','2Chr','1Macc','2Macc','Ps','Isa','Ezek','Hos','Amos','Mic','Zech','Lam'}
def lnorm(w):
    w = unicodedata.normalize('NFD', w.lower()); w = ''.join(c for c in w if unicodedata.category(c) != 'Mn')
    return w.replace('æ', 'ae').replace('œ', 'oe').replace('j', 'i')
def lstems(t):
    ws = [lnorm(w) for w in re.findall(r"[A-Za-zÆæŒœëÉéÈè]+", t)]
    return ws, set(w[:5] for w in ws)
STOPG = set()
for k, L in lex.items():
    if L[2] in ('Article', 'Conjunction', 'Particle') or L[0] in ('ὁ', 'καί', 'αὐτός', 'δέ', 'ἐν', 'εἰς', 'ὅτι', 'ἐγώ', 'σύ', 'οὗτος', 'εἰμί'): STOPG.add(int(k))
verses = []  # (b,c,v,lemmas set)
for bk in books:
    for c in bk['chapters']:
        for v in json.load(open(f"{D}/{bk['id']}/{c}.json")):
            vn = re.match(r'\d+$', v[0])
            verses.append((bk['id'], c, int(v[0]) if vn else v[0], set(t[1] for t in v[1]) - STOPG))
def train(pairs):
    ldf = collections.Counter(); wdf = collections.Counter(); co = collections.Counter()
    for ls, ws in pairs:
        ldf.update(ls); wdf.update(ws)
        for l in ls:
            for w in ws: co[(l, w)] += 1
    model = collections.defaultdict(list)
    for (l, w), n in co.items():
        if n >= 3:
            d = 2 * n / (ldf[l] + wdf[w])
            if d >= 0.2: model[l].append((round(d, 3), w, n))
    return {l: sorted(x, reverse=True)[:4] for l, x in model.items()}, ldf, co
import math
IDF = {}
def score(ls, ws, model):  # IDF-weighted share of the Greek verse's known content lemmas whose usual Latin stems occur
    ks = [l for l in ls if l in model]
    if len(ks) < 3: return None
    W = sum(IDF.get(l, 1) for l in ks)
    return sum(IDF.get(l, 1) for l in ks if any(w in ws for _, w, _ in model[l][:3])) / W
pairs = []
for b, c, v, ls in verses:
    if b in TRAIN and isinstance(v, int):
        k = base(b, c, v)
        if k in VU: pairs.append((ls, lstems(VU[k])[1]))
_df = collections.Counter(l for _, _, _, ls in verses for l in ls); IDF.update({l: math.log(len(verses) / n) for l, n in _df.items()})
model, _, _ = train(pairs); print('model lemmas', len(model), 'training pairs', len(pairs))
# calibrate on wrong pairs (same book, verse shifted by +7)
random.seed(1); wrong = []
for b, c, v, ls in random.sample(verses, 6000):
    if isinstance(v, int):
        k = base(b, c, v)
        if k and (k[0], k[1], k[2] + 7) in VU:
            s = score(ls, lstems(VU[(k[0], k[1], k[2] + 7)])[1], model)
            if s is not None: wrong.append(s)
wrong.sort(); TH = wrong[int(len(wrong) * 0.99)]; print('wrong-pair scores n', len(wrong), 'median', wrong[len(wrong)//2], '99th pct threshold', TH)
# assign: same ref, else best of offsets -2..+2 in the same Vulgate chapter (needs a clear margin)
res = {}; stat = collections.defaultdict(collections.Counter)
for b, c, v, ls in verses:
    if not isinstance(v, int): stat[b]['lettered'] += 1; continue
    k = base(b, c, v)
    if not k: stat[b]['nobook'] += 1; continue
    cands = []
    for off in (0, -1, 1, -2, 2):
        kk = (k[0], k[1], k[2] + off)
        if kk in VU:
            s = score(ls, lstems(VU[kk])[1], model)
            cands.append((s if s is not None else -1, off, kk))
    if not cands: stat[b]['novulg'] += 1; continue
    s0 = next((x for x in cands if x[1] == 0), (-1, 0, None))
    bestc = max(cands, key=lambda x: (x[0], -abs(x[1])))
    pick = None
    if s0[2] and s0[0] == -1:  # too few known words to judge: accept same reference only in well-aligned books
        stat[b]['unscored'] += 1
        if b in TRAIN: res[(b, c, v)] = (s0[2], None)
        continue
    if b in TRAIN and s0[2] and s0[0] >= 0.3 and bestc[0] < s0[0] + 0.25: pick = s0
    elif bestc[0] >= TH and bestc[0] >= s0[0] + (0 if bestc[1] == 0 else 0.15): pick = bestc
    if pick: res[(b, c, v)] = (pick[2], round(pick[0], 2)); stat[b]['shown' if pick[1] == 0 else 'shifted'] += 1
    else: stat[b]['rejected'] += 1
# retrain the word model on accepted pairs, compute 'often rendered as'
pairs2 = []; vlook = {(b, c, v): ls for b, c, v, ls in verses}
for key, (vk, s) in res.items(): pairs2.append((vlook[key], lstems(VU[vk])[1]))
surf = collections.defaultdict(collections.Counter)
for key, (vk, s) in res.items():
    for w in lstems(VU[vk])[0]: surf[w[:5]][w] += 1
ldf = collections.Counter(); wdf = collections.Counter(); co = collections.Counter()
for ls, ws in pairs2:
    ldf.update(ls); wdf.update(ws)
    for l in ls:
        for w in ws: co[(l, w)] += 1
render = {}; NP = len(pairs2)
for (l, w), n in co.items():
    if ldf[l] >= 10 and n >= 5:
        cov = n / ldf[l]; d = 2 * n / (ldf[l] + wdf[w]); lift = cov / (wdf[w] / NP)
        if cov >= 0.3 and d >= 0.25 and lift >= 3: render.setdefault(l, []).append((round(cov, 2), w, n))
sel = {l: set(w for _, w, _ in sorted(x, reverse=True)[:3]) for l, x in render.items()}
lsurf = collections.defaultdict(collections.Counter)  # surface forms actually seen with this Greek lemma
for key, (vk, s_) in res.items():
    ls = vlook[key]; ws = lstems(VU[vk])[0]
    for l in ls & sel.keys():
        for w in ws:
            if w[:5] in sel[l]: lsurf[(l, w[:5])][w] += 1
out = {}
for l, x in render.items():
    x.sort(reverse=True)
    out[l] = {'n': ldf[l], 'r': [[[f for f, _ in lsurf[(l, w)].most_common(3)], cov, n] for cov, w, n in x[:3]]}
json.dump(out, open(D + '/vulg_words.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('lemmas with an approximate Vulgate rendering', len(out))
# write per-chapter Latin files
byc = collections.defaultdict(dict)
for (b, c, v), (vk, s) in res.items():
    byc[(b, c)][str(v)] = [VU[vk], DR.get(vk, ''), f'{vk[0]} {vk[1]}:{vk[2]}', s]
os.makedirs(D + '/vul', exist_ok=True)
for (b, c), d in byc.items():
    os.makedirs(f'{D}/vul/{b}', exist_ok=True)
    json.dump(d, open(f'{D}/vul/{b}/{c}.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
summary = {}
for b, s in stat.items():
    tot = sum(s.values()); summary[b] = dict(s, total=tot, shown_pct=round(100 * (s['shown'] + s['shifted'] + (s['unscored'] if b in TRAIN else 0)) / tot))
json.dump(summary, open(D + '/vul_summary.json', 'w'), separators=(',', ':'))
for b in summary: print(b, summary[b])
