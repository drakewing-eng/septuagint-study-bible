#!/usr/bin/env python3
"""Build LXX reader data from eliranwong/LXX-Rahlfs-1935 (CCAT-derived, CC BY-NC-SA 4.0) + Brenton (PD, ebible.org)."""
import csv, json, re, os, sys, collections
SRC = sys.argv[1] if len(sys.argv) > 1 else '/workspace/LXX-Rahlfs-1935'
BR = sys.argv[2] if len(sys.argv) > 2 else '/workspace/brenton/eng-Brenton_vpl.txt'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'site', 'data')
def tsv(p):
    with open(os.path.join(SRC, p), encoding='utf-8-sig') as f:
        return [l.rstrip('\n').split('\t') for l in f if l.strip()]
words = {int(r[0]): r[-1].replace('σ—','ς').replace('—','') for r in tsv('01_wordlist_unicode/text_accented.csv')}
lexno = {int(r[0]): int(r[1]) for r in tsv('02_lexemes/Lex_LXXno.csv')}
morph = {int(r[0]): (r[1], r[2], r[3] if len(r) > 3 else '') for r in tsv('03b_descriptions_on_morphology_codes/morphology_623693_with_description.csv')}
verses = [(r[0], int(r[1])) for r in tsv('08_versification/001_verse_c_modified_KEEP.csv')]
# --- plain-English morphology
AB = {'Pres':'present','Imperf':'imperfect','Fut':'future','Aor':'aorist','Perf':'perfect','Pluperf':'pluperfect',
 'Act':'active','Mid':'middle','Pass':'passive','Ind':'indicative','Subj':'subjunctive','Opt':'optative',
 'Imperative':'imperative','Infin':'infinitive','Part':'participle','1st':'1st person','2nd':'2nd person','3rd':'3rd person',
 'Sing':'singular','Plur':'plural','Dual':'dual','Nom':'nominative','Gen':'genitive','Dat':'dative','Acc':'accusative',
 'Voc':'vocative','Masc':'masculine','Fem':'feminine','Neut':'neuter','Compar':'comparative','Superlative':'superlative','Gen/Dat':'genitive/dative'}
def plain(pos, desc):
    t = desc.split()
    tense = [AB.get(x, x) for x in t if x in ('Pres','Imperf','Fut','Aor','Perf','Pluperf','Act','Mid','Pass','Ind','Subj','Opt','Imperative','Infin','Part')]
    rest = [AB.get(x, x) for x in t if x not in ('Pres','Imperf','Fut','Aor','Perf','Pluperf','Act','Mid','Pass','Ind','Subj','Opt','Imperative','Infin','Part')]
    # "3rd person singular" reads better than "3rd person, singular"
    parts = [' '.join(tense)] if tense else []
    if rest: parts.append(' '.join(rest))
    return pos + (': ' + ', '.join(parts) if parts else '')
mcodes, midx = [], {}
def mi(code, pos, desc):
    if code not in midx:
        midx[code] = len(mcodes); mcodes.append([code, plain(pos, desc)])
    return midx[code]
# --- lexicon
lex = {}
for r in tsv('09a_LXX_lexicon/01-04.csv'):
    h = r[1]
    m = re.search(r"href='S:([^']+)'", h); lemma = m.group(1) if m else ''
    g = re.search(r"<font color='1'><b>(.*?)</b>", h); gloss = re.sub('<[^>]+>', '', g.group(1)) if g else ''
    p = re.search(r"<i>(.*?)</i>", h); pos = p.group(1) if p else ''
    tr = re.search(r"<font color='5'>(.*?)</font>", h); tr = tr.group(1) if tr else ''
    lsj = re.search(r"LSJ: </i><a href='S:([^']+)'", h); lsj = lsj.group(1) if lsj else ''
    st = re.search(r"href='S:(G\d+)'><grk>", h); st = st.group(1) if st else ''
    lex[int(r[0])] = [lemma, gloss, pos, tr, lsj, st]
# --- Brenton
BMAP = {'Gen':'GEN','Exod':'EXO','Lev':'LEV','Num':'NUM','Deut':'DEU','JoshB':'JOS','JudgB':'JDG','Ruth':'RUT','1Sam':'1SA','2Sam':'2SA',
 '1Kgs':'1KI','2Kgs':'2KI','1Chr':'1CH','2Chr':'2CH','1Esdr':'1ES','Esth':'ESG','Jdt':'JDT','TobBA':'TOB','1Macc':'1MA','2Macc':'2MA',
 '3Macc':'3MA','4Macc':'4MA','Ps':'PSA','Prov':'PRO','Eccl':'ECC','Song':'SOL','Job':'JOB','Wis':'WIS','Sir':'SIR','Hos':'HOS','Mic':'MIC',
 'Amos':'AMO','Joel':'JOE','Jonah':'JON','Obad':'OBA','Nah':'NAH','Hab':'HAB','Zeph':'ZEP','Hag':'HAG','Zech':'ZEC','Mal':'MAL','Isa':'ISA',
 'Jer':'JER','Bar':'BAR','EpJer':'EPJ','Lam':'LAM','Ezek':'EZE','BelTh':'BEL','DanTh':'DNG','SusTh':'SUS'}
br = {}
if os.path.exists(BR):
    for l in open(BR, encoding='utf-8-sig'):
        m = re.match(r'(\S+) (\d+):(\d+) (.*)', l.strip())
        if m: br[(m.group(1), int(m.group(2)), int(m.group(3)))] = m.group(4)
def brenton(book, c, v):
    if book == '2Esdr':  # Rahlfs 2 Esdras 1-10 = Ezra, 11-23 = Nehemiah
        # Brenton (eBible) also carries 2 Esdras 11-23 under EZR in LXX numbering (audit: 0 unmatched); NEH uses MT numbering.
        return br.get(('EZR', c, v))
    b = BMAP.get(book)
    return br.get((b, c, v)) if b else None
NAMES = {'JoshA':'Joshua (A text, fragments)','JoshB':'Joshua (B text)','JudgA':'Judges (A text)','JudgB':'Judges (B text)','1Macc':'1 Maccabees','2Macc':'2 Maccabees','3Macc':'3 Maccabees','4Macc':'4 Maccabees','Odes':'Odes','Eccl':'Ecclesiastes','Song':'Song of Songs','Gen':'Genesis','Exod':'Exodus','Lev':'Leviticus','Num':'Numbers','Deut':'Deuteronomy','Josh':'Joshua','Judg':'Judges','Ruth':'Ruth',
 '1Sam':'1 Kingdoms (1 Samuel)','2Sam':'2 Kingdoms (2 Samuel)','1Kgs':'3 Kingdoms (1 Kings)','2Kgs':'4 Kingdoms (2 Kings)','1Chr':'1 Chronicles',
 '2Chr':'2 Chronicles','1Esdr':'1 Esdras','2Esdr':'2 Esdras (Ezra–Nehemiah)','Esth':'Esther','Jdt':'Judith','TobBA':'Tobit (BA text)',
 'TobS':'Tobit (Sinaiticus text)','1Mac':'1 Maccabees','2Mac':'2 Maccabees','3Mac':'3 Maccabees','4Mac':'4 Maccabees','Ps':'Psalms',
 'Od':'Odes','Prov':'Proverbs','Qoh':'Ecclesiastes','Cant':'Song of Songs','Job':'Job','Wis':'Wisdom of Solomon','Sir':'Sirach',
 'PsSol':'Psalms of Solomon','Hos':'Hosea','Mic':'Micah','Amos':'Amos','Joel':'Joel','Jonah':'Jonah','Obad':'Obadiah','Nah':'Nahum',
 'Hab':'Habakkuk','Zeph':'Zephaniah','Hag':'Haggai','Zech':'Zechariah','Mal':'Malachi','Isa':'Isaiah','Jer':'Jeremiah','Bar':'Baruch',
 'EpJer':'Epistle of Jeremiah','Lam':'Lamentations','Ezek':'Ezekiel','Bel':'Bel and the Dragon (Old Greek)','BelTh':'Bel and the Dragon (Theodotion)',
 'Dan':'Daniel (Old Greek)','DanOG':'Daniel (Old Greek)','SusOG':'Susanna (Old Greek)','BelOG':'Bel and the Dragon (Old Greek)','DanTh':'Daniel (Theodotion)','Sus':'Susanna (Old Greek)','SusTh':'Susanna (Theodotion)'}
# --- assemble
N = max(words)
books = collections.OrderedDict()
for i, (ref, start) in enumerate(verses):
    end = verses[i + 1][1] if i + 1 < len(verses) else N + 1
    b, c, v = ref.rsplit('.', 2); c = int(c) if c.isdigit() else c
    toks = []
    for w in range(start, end):
        code, pos, desc = morph[w]
        toks.append([words[w], lexno[w], mi(code, pos, desc)])
    vn = int(re.match(r'\d+', v).group()) if re.match(r'\d+', v) else 0
    books.setdefault(b, collections.OrderedDict()).setdefault(c, []).append([v, toks, brenton(b, c, vn) if (v.isdigit() and isinstance(c, int)) else None])
used = set()
index, stats = [], {'brenton_verses': 0, 'verses': 0}
for b, chs in books.items():
    os.makedirs(os.path.join(OUT, b), exist_ok=True)
    for c, vs in chs.items():
        for v in vs:
            stats['verses'] += 1; stats['brenton_verses'] += v[2] is not None
            for t in v[1]: used.add(t[1])
        json.dump(vs, open(os.path.join(OUT, b, f'{c}.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    index.append({'id': b, 'name': NAMES.get(b, b), 'chapters': list(chs.keys()), 'en': b in BMAP or b == '2Esdr'})
json.dump(index, open(os.path.join(OUT, 'books.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
json.dump(mcodes, open(os.path.join(OUT, 'morph.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
missing = [k for k in used if k not in lex]
json.dump({k: lex[k] for k in used if k in lex}, open(os.path.join(OUT, 'lexicon.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
nogloss = sum(1 for k in used if k in lex and not lex[k][1])
print(len(index), 'books', stats, 'lexemes', len(used), 'missing', len(missing), 'no gloss', nogloss, 'morph codes', len(mcodes))
# --- occurrence index for lemma search: occ/<id//100>.json  {lexId: [count, "Book|ch|v", ...]}
occ = collections.defaultdict(list); cnt = collections.Counter()
for b, chs in books.items():
    for c, vs in chs.items():
        for v in vs:
            seen = set()
            for t in v[1]:
                cnt[t[1]] += 1
                if t[1] not in seen:
                    seen.add(t[1]); occ[t[1]].append(f'{b}|{c}|{v[0]}')
od = os.path.join(OUT, 'occ'); os.makedirs(od, exist_ok=True)
buckets = collections.defaultdict(dict)
for k, refs in occ.items(): buckets[k // 100][k] = [cnt[k]] + refs
for bk, d in buckets.items():
    json.dump(d, open(os.path.join(od, f'{bk}.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
json.dump({k: cnt[k] for k in cnt}, open(os.path.join(OUT, 'counts.json'), 'w'), separators=(',', ':'))
print('occ buckets', len(buckets))
