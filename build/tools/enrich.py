#!/usr/bin/env python3
"""Step 3: word-panel data. (a) attested forms per lemma (from the site's own morphology) -> data/forms/<bucket>.json
(b) STEPBible TBESG (CC BY 4.0) definitions -> data/dict/<bucket>.json   (c) per-book/chapter frequency is computed client-side."""
import json, os, re, collections, unicodedata, html
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, '..', 'site', 'data')
lex = json.load(open(D + '/lexicon.json')); morph = json.load(open(D + '/morph.json')); books = json.load(open(D + '/books.json'))
def acute(s):  # grave -> acute so θεὸς / θεός are one form
    return unicodedata.normalize('NFC', unicodedata.normalize('NFD', s).replace('\u0300', '\u0301'))
forms = collections.defaultdict(collections.Counter); bookcnt = collections.defaultdict(collections.Counter)
first = {}
for b in books:
    for c in b['chapters']:
        for v in json.load(open(f"{D}/{b['id']}/{c}.json")):
            for t in v[1]:
                k = (acute(t[0]), t[2]); forms[t[1]][k] += 1; bookcnt[t[1]][b['id']] += 1
                first.setdefault((t[1],) + k, f"{b['id']}|{c}|{v[0]}")
out = collections.defaultdict(dict)
for l, cnt in forms.items():
    out[l // 100][l] = {'f': [[f, m, n, first[(l, f, m)]] for (f, m), n in sorted(cnt.items(), key=lambda x: -x[1])],
                        'b': dict(bookcnt[l])}
os.makedirs(D + '/forms', exist_ok=True)
for bk, d in out.items(): json.dump(d, open(f'{D}/forms/{bk}.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('forms buckets', len(out))
# ---- TBESG
def nl(s): return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn').replace('ς', 'σ').strip()
tb = collections.defaultdict(list)
for line in open('/workspace/lxx-audit/src/tbesg.txt', encoding='utf-8'):
    r = line.rstrip('\n').split('\t')
    if len(r) < 8 or not re.match(r'G\d', r[0]): continue
    estrong, lemma, translit, morphc, gloss, defin = r[0], r[3], r[4], r[5], r[6], r[7]
    for lm in re.split(r'[,;]\s*', lemma):
        tb[nl(lm)].append((estrong, lemma, gloss, defin, morphc))
def clean(d):
    d = re.sub(r"<ref='[^']*'>([^<]*)</ref>", r'\1', d)
    d = d.replace('<BR />', '\n').replace('<br />', '\n')
    d = re.sub(r'</?(?!b>|/b>|i>|/i>)[^>]+>', '', d)
    return html.unescape(d).strip()
def senses(d):
    s = [html.unescape(re.sub('<[^>]+>', '', x)).strip(' ,.;:') for x in re.findall(r'<b>(.*?)</b>', d)]
    s = [x for x in s[1:] if x and not re.search(r'[\u0370-\u03ff\u1f00-\u1fff]', x) and len(x) < 80]
    seen = []; [seen.append(x) for x in s if x.lower() not in [y.lower() for y in seen]]
    return seen[:6]
dic = collections.defaultdict(dict); hit = 0
for k, L in lex.items():
    c = tb.get(nl(L[0]))
    if not c: continue
    st = L[5]; pick = None
    if st:
        n = int(st[1:]); pick = next((x for x in c if re.match(r'G0*%d[A-Z]?$' % n, x[0])), None)
    if not pick:
        if len(c) == 1: pick = c[0]
        else:
            g = set(re.findall(r'[a-z]+', L[1].lower()))
            sc = [(len(g & set(re.findall(r'[a-z]+', x[2].lower()))), -i, x) for i, x in enumerate(c)]
            sc.sort(reverse=True); pick = sc[0][2] if sc[0][0] > 0 else None
    if not pick: continue
    hit += 1
    lxx = re.search(r'\[in LXX([^\]]*)\]', pick[3])
    dic[int(k) // 100][k] = {'id': pick[0], 'g': pick[2], 's': senses(pick[3]),
                             'lxx': html.unescape(re.sub('<[^>]+>', '', 'in LXX' + lxx.group(1))).strip(' ;') if lxx else '',
                             'full': clean(pick[3])[:6000]}
os.makedirs(D + '/dict', exist_ok=True)
for bk, d in dic.items(): json.dump(d, open(f'{D}/dict/{bk}.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('TBESG matched', hit, 'of', len(lex))
# ---- (c) second meaning source: STEPBible TFLSJ (LSJ edited by Tyndale House, CC BY 4.0)
tl = collections.defaultdict(list)
for f in ('/workspace/src/tflsj1.txt', '/workspace/src/tflsj2.txt'):
    for line in open(f, encoding='utf-8'):
        r = line.rstrip('\n').split('\t')
        if len(r) < 8 or not re.match(r'G\d', r[0]): continue
        tl[nl(r[3])].append((r[0], r[3], r[6], r[7]))
GENRE = r'\s+(Epicus|Tragicus|Historicus|Orator|Philosophus|Medicus|Elegiacus|Lyricus|Comicus|Epigrammaticus|Rhetor|Iambographus|Grammaticus|Lexicographus|Geographus|Scriptor Ecclesiasticus|Legal icographus|Poeta)\b'
def lsj_senses(d):
    s = [html.unescape(re.sub('<[^>]+>', '', x)).strip(' ,.;:') for x in re.findall(r'<b>(.*?)</b>', d)]
    s = [x for x in s[1:] if x and not x.startswith('__') and not re.search(r'[\u0370-\u03ff\u1f00-\u1fff]', x) and len(x) < 60]
    s = [x for x in s if len(x) >= 4 and "'" not in x]
    out = []; [out.append(x) for x in s if x.lower() not in [y.lower() for y in out]]
    return out[:4]
def lit(d):
    m = re.search(r'title="\s*([^"]*?)"', d)
    if not m: return ''
    first = re.split(r';|, compare|\bcompare\b', m.group(1))[0].strip(' ,')
    mm = re.match(r'([\d\-]+(?:st|nd|rd|th) c\.(?:BC|AD)(?:\(\?\))?):\s*(.*)', first)
    if not mm: return ''
    who = re.sub(GENRE, '', mm.group(2)).strip(' ,')
    who = re.sub(r'^Ilias Homerus “Illiad”', 'Homer, Iliad', who); who = re.sub(r'^Odyssea Homerus “Odyssey”', 'Homer, Odyssey', who)
    return f'{who} ({mm.group(1).replace("c.", "c. ")})'
lsj = collections.defaultdict(dict); lhit = 0
for k, L in lex.items():
    c = tl.get(nl(L[0]))
    if not c: continue
    pick = None
    if L[5]:
        n = int(L[5][1:]); pick = next((x for x in c if re.match(r'G0*%d[A-Z]?$' % n, x[0])), None)
    if not pick and len(c) == 1: pick = c[0]
    if not pick: continue
    s = lsj_senses(pick[3])
    if not s: continue
    lhit += 1; lsj[int(k) // 100][k] = {'id': pick[0], 's': s, 'lit': lit(pick[3])}
os.makedirs(D + '/lsj', exist_ok=True)
for bk, d in lsj.items(): json.dump(d, open(f'{D}/lsj/{bk}.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('TFLSJ matched', lhit)
# ---- (d) etymology layer: Wiktionary via kaikki.org/Wiktextract (CC BY-SA 4.0) -- kept in a SEPARATE folder data/etym/
def nw(s): return unicodedata.normalize('NFC', ''.join(c for c in unicodedata.normalize('NFD', s) if c not in '\u0304\u0306'))
want = {nw(L[0]): k for k, L in lex.items() if L[2] != 'Proper Noun'}
ety = collections.defaultdict(dict); ehit = 0
def gk(t):  # drop vowel-length marks on Greek letters only (keep Latin transliteration as Wiktionary has it)
    t = unicodedata.normalize('NFD', t)
    t = re.sub(r'(?<=[\u0370-\u03ff\u1f00-\u1fff])([\u0300-\u036f]*)[\u0304\u0306]', r'\1', t)
    t = re.sub(r'([\u0370-\u03ff][\u0300-\u036f]*)[\u0304\u0306]', r'\1', t)
    return unicodedata.normalize('NFC', t)
def short(t):
    t = re.sub(r'\s+', ' ', t).strip()
    sents = re.split(r'(?<=\.)\s+(?=[A-Z])', t)
    out = sents[0]
    if len(sents) > 1 and len(out) + len(sents[1]) < 230: out += ' ' + sents[1]
    return out if len(out) <= 260 else out[:257].rsplit(' ', 1)[0] + '…'
for line in open('/workspace/src/grc_kaikki.jsonl', encoding='utf-8'):
    d = json.loads(line); w = nw(d.get('word', ''))
    if w not in want or not d.get('etymology_text'): continue
    k = want[w]
    if k in ety[int(k) // 100]: continue
    der = [nw(x['word']) for x in d.get('derived', []) if x.get('word') and not x['word'].startswith('-')][:4]
    ety[int(k) // 100][k] = {'t': gk(short(d['etymology_text'])), 'd': der}; ehit += 1
os.makedirs(D + '/etym', exist_ok=True)
for bk, d in ety.items(): json.dump(d, open(f'{D}/etym/{bk}.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('Wiktionary etymologies', ehit)
