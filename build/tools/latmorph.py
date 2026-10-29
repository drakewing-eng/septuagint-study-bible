#!/usr/bin/env python3
"""Build a Latin form -> (lemma, pos, tags, gloss) index for every word in the Clementine Vulgate,
from Wiktionary (kaikki.org Wiktextract dump, CC BY-SA 4.0). Output: /workspace/src/latmorph.json (build input only)."""
import json, re, sys, unicodedata
sys.path.insert(0, '/workspace/lxx-reader-v2/tools')
def lnorm(w):
    w = unicodedata.normalize('NFD', w.lower()); w = ''.join(c for c in w if unicodedata.category(c) != 'Mn')
    return w.replace('æ', 'ae').replace('œ', 'oe').replace('j', 'i').replace('v', 'u')
VU = set()
for l in open('/workspace/lxx-audit/src/latVUC/latVUC_vpl.txt', encoding='utf-8-sig'):
    for w in re.findall(r"[A-Za-zÆæŒœëÉéÈè]+", l.split(' ', 2)[-1]): VU.add(lnorm(w))
for w in list(VU):
    for enc in ('que', 'ne', 've'):
        if w.endswith(enc) and len(w) > len(enc) + 1: VU.add(w[:-len(enc)])
KEEP = {'nominative','genitive','dative','accusative','ablative','vocative','locative','singular','plural','masculine','feminine','neuter',
 'first-person','second-person','third-person','present','imperfect','future','perfect','pluperfect','future-perfect','indicative','subjunctive',
 'imperative','infinitive','participle','active','passive','gerund','gerundive','supine','comparative','superlative'}
idx = {}
POS = {'noun','verb','adj','adv','prep','pron','conj','num','name','det','particle','intj','participle'}
for line in open('/workspace/src/lat_kaikki.jsonl'):
    e = json.loads(line)
    if e.get('lang_code') != 'la' or e.get('pos') not in POS: continue
    senses = [s for s in e.get('senses', []) if s.get('glosses') and 'form-of' not in s.get('tags', []) and not s.get('form_of')]
    if not senses: continue
    gl = senses[0]['glosses'][0]
    gl = re.sub(r'\s*\([^)]*\)', '', gl).split(';')[0].strip()[:60]
    lem = e['word']; cands = [(lem, ['canonical'])] + [(f['form'], f.get('tags', [])) for f in e.get('forms', []) if f.get('source') in ('declension', 'conjugation', 'inflection')]
    disp = unicodedata.normalize('NFC', ''.join(ch for ch in unicodedata.normalize('NFD', lem) if unicodedata.category(ch) != 'Mn'))
    gen = next((g for f in e.get('forms', []) if 'canonical' in f.get('tags', []) for g in ('masculine', 'feminine', 'neuter') if g in f['tags']), '')
    seen = set()
    for f, tags in cands:
        if ' ' in f or not f: continue
        k = lnorm(f)
        if k not in VU: continue
        t = tuple(x for x in tags if x in KEEP)
        if (k, t) in seen: continue
        seen.add((k, t))
        idx.setdefault(k, []).append([lnorm(lem), e['pos'], list(t), gl, disp, gen])
json.dump(idx, open('/workspace/src/latmorph.json', 'w'), ensure_ascii=False)
print(len(VU), 'vulgate forms;', sum(1 for w in VU if w in idx), 'analysed')
