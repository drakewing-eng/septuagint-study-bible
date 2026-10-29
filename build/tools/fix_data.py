#!/usr/bin/env python3
"""Step 2: gloss corrections (bad_glosses.csv, checked against STEPBible TBESG CC BY 4.0) and parsing overrides.
Parsing overrides are produced by explicit, form-based rules applied only to tokens whose tag CONTRADICTS the
form (audit rule tests). Each override is listed in site/data/parse_overrides.json (ref, form, old, new, reason)."""
import json, csv, re, os, collections, unicodedata
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, '..', 'site', 'data')
lex = json.load(open(D + '/lexicon.json')); morph = json.load(open(D + '/morph.json')); books = json.load(open(D + '/books.json'))
# ---- glosses
fixes = []
for r in csv.DictReader(open('/workspace/lxx-audit/bad_glosses.csv', encoding='utf-8')):
    k = r['lex_id']
    if k in lex and lex[k][0] == r['lemma']:
        fixes.append({'lex': k, 'lemma': r['lemma'], 'old': lex[k][1], 'new': r['proposed_gloss'], 'tbesg': r['tbesg_gloss'],
                      'verified_in_tbesg': r['keyword_found_in_TBESG'].startswith('yes')})
        lex[k][1] = r['proposed_gloss']
    else: print('gloss: lemma/id mismatch, skipped', r['lemma'], k)
json.dump(lex, open(D + '/lexicon.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
json.dump({f['lex']: f for f in fixes}, open(D + '/gloss_fixes.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('gloss fixes applied', len(fixes))
# ---- parsing
def nz(s): return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn').replace('ς', 'σ').replace('᾿', '')
def nzi(s):  # keep iota subscript as ι
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn' or c == '\u0345').replace('\u0345', 'ι').replace('ς', 'σ')
ART = {}
for cs, tab in {'N': {'SM':'ο','SF':'η','SN':'το','PM':'οι','PF':'αι','PN':'τα'}, 'G': {'SM':'του','SF':'τησ','SN':'του','PM':'των','PF':'των','PN':'των'},
                'D': {'SM':'τωι','SF':'τηι','SN':'τωι','PM':'τοισ','PF':'ταισ','PN':'τοισ'}, 'A': {'SM':'τον','SF':'την','SN':'το','PM':'τουσ','PF':'τασ','PN':'τα'}}.items():
    for k, f in tab.items(): ART.setdefault(f, []).append(cs + k)
codes = {m[0]: i for i, m in enumerate(morph)}
HAND = {  # (form, old code) -> (new code, reason); hand-checked individual cases
    # round 5: confirmed by the independent Wiktionary inflection-table check (tools/morphcheck.py) AND by the form itself
    ('θώρακα', 'N.APM'): ('N.ASM', 'θώρακα is accusative singular (Wiktionary + form)'),
    ('πᾶν', 'A.ASM'): ('A.ASN', 'πᾶν is neuter (masc. acc. would be πάντα) (Wiktionary + form)'),
    ('πούς', 'N.ASM'): ('N.NSM', 'πούς is nominative (acc. πόδα) (Wiktionary + form)'),
    ('ἐδίδουν', 'V.IMI1S'): ('V.IAI1S', 'ἐδίδουν is active (middle ἐδιδόμην) (Wiktionary + form)'),
    ('ὑπέθεντο', 'V.AMI3S'): ('V.AMI3P', '-θεντο is 3rd plural (Wiktionary + form)'),
    ('τρία', 'A.ASN'): ('A.APN', 'τρία is plural (Wiktionary + form)'),
    ('ἁλμυρίδα', 'N.APN'): ('N.ASF', 'ἁλμυρίδα is accusative singular feminine (Wiktionary + form)'),
    ('ἠκόντιζεν', 'V.AAI3S'): ('V.IAI3S', 'ἠκόντιζεν is imperfect (aorist ἠκόντισεν) (Wiktionary + form)'),
    ('τακῇ', 'V.PAS3S'): ('V.APS3S', 'τακῇ is aorist passive subjunctive (Wiktionary + form)'),
    ('υἱὸς', 'N.GSM'): ('N.NSM', 'υἱός is nominative (gen. υἱοῦ) (Wiktionary + form)'),
    ('ᾔδεισαν', 'V.XAI3P'): ('V.YAI3P', 'ᾔδεισαν is pluperfect (Wiktionary + form)'),
    ('εἰσακούσαι', 'V.AAS3S'): ('V.AAO3S', '-σαι with this accent is aorist optative 3rd sg (subjunctive -σῃ) (Wiktionary + form)'),
    ('μακαρίσαι', 'V.AMD2S'): ('V.AAO3S', 'μακαρίσαι is aorist optative 3rd sg (middle imperative μακάρισαι) (Wiktionary + form)'),
    ('καταντησάτωσαν', 'V.AAS3P'): ('V.AAD3P', '-σάτωσαν is the aorist imperative 3rd plural ending'),
    ('ἱλάσθητι', 'V.APS2S'): ('V.APD2S', '-θητι is the aorist passive imperative 2nd singular ending'),
    ('ἅψασθε', 'V.AMS2P'): ('V.AMD2P', 'unaugmented aorist middle -σασθε = imperative 2nd plural'),
    ('θανατώσουσιν', 'V.AAS3P'): ('V.FAI3P', '-σουσιν is future indicative, not aorist subjunctive (-σωσιν)'),
    ('βασιλεύσεις', 'V.AAS2S'): ('V.FAI2S', '-σεις is future indicative, not aorist subjunctive (-σῃς)'),
    ('φάγετε', 'V.FAI2P'): ('V.AAD2P', 'φάγετε is aorist imperative (the future is φάγεσθε)'),
    ('παρεστῶτες', 'V.AAPNPM'): ('V.XAPNPM', '-εστῶτες is the perfect participle of ἵστημι compounds'),
    ('σαλευθῇς', 'V.APP2S'): ('V.APS2S', 'finite -θῇς = aorist passive subjunctive 2nd singular'),
    ('μεγαλυνθείη', 'V.APPNSF'): ('V.APO3S', '-θείη = aorist passive optative 3rd singular'),
    ('οἰκοδομήσωμεν', 'V.AAS2P'): ('V.AAS1P', '-ωμεν is 1st person plural'),
    ('λικμήσεις', 'V.FAI2P'): ('V.FAI2S', '-σεις is 2nd person singular'),
    ('ἐπιστολαὶ', 'N.APF'): ('N.NPF', '-αι is nominative plural (accusative is -ας)'),
    ('διηγήσεως', 'N.DSF'): ('N.GSF', '-εως is genitive singular'),
    ('διατάξεως', 'N.GPF'): ('N.GSF', '-εως is genitive singular'),
    ('μίσους', 'N.GPN'): ('N.GSN', '-ους is genitive singular of a neuter -ος noun'),
    ('παροργισμῷ', 'N.GPM'): ('N.DSM', '-ῳ is dative singular'),
    ('μέσῳ', 'A.GPN'): ('A.DSN', '-ῳ is dative singular'),
    ('θελήματι', 'N.DPN'): ('N.DSN', '-ματι is dative singular'),
    ('πυρώσει', 'N.DPF'): ('N.DSF', '-σει is dative singular'),
    ('Ῥωμαίους', 'N.DPM'): ('N.APM', '-ους is accusative plural'),
    ('Ιουδαῖοι', 'N.DPM'): ('N.NPM', '-οι is nominative plural'),
    ('ἀνθρωπαρέσκων', 'N.DPM'): ('N.GPM', '-ων is genitive plural'),
    ('ἀκατάγνωστοι', 'A.DPM'): ('A.NPM', '-οι is nominative plural'),
}
def rule_fix(form, code):
    f = nzi(form); fn = nz(form)
    if (form, code) in HAND: return HAND[(form, code)]
    m = re.match(r'^RA\.([NGDA])([SP])([MFN])$', code)
    if m:
        cells = ART.get(f)
        if not cells or m.group(1) + m.group(2) + m.group(3) in cells: return None
        old = m.group(1) + m.group(2) + m.group(3)
        dist = sorted((sum(a != b for a, b in zip(c, old)), c) for c in cells)
        if len(dist) == 1 or dist[0][0] < dist[1][0]: return ('RA.' + dist[0][1], f'the article form {form} is {dist[0][1]} (case-number-gender)')
        return None
    m = re.match(r'^(N|A)\.D(P)([MFN])$', code)
    if m and fn.endswith('ων'): return (f'{m.group(1)}.GP{m.group(3)}', '-ων is genitive plural, not dative')
    m = re.match(r'^(N|A)\.AP([MF])$', code)
    if m and re.search(r'ματα$', fn): return (f'{m.group(1)}.APN', 'nouns in -μα(τος) are neuter')
    if m and re.search(r'(οτητα|ητα|αδα|ιδα)$', fn) and m.group(1) == 'N': return ('N.ASF', '-τητα/-αδα/-ιδα is accusative singular')
    m = re.match(r'^V\.([PIFAXY][AMPEDON])([IS])([123])([SP])$', code)
    if m:
        tv, mood, pe, nu = m.groups(); new = None
        if nu == 'P':  # tagged plural: the ending decides the person (audit: these failures were real)
            if re.search(r'(μεν|μεθα)$', fn): new = '1P'
            elif re.search(r'(τε|σθε)$', fn): new = '2P'
            elif re.search(r'(νται|ντο|σαν|ουσιν?|ασιν?)$', fn): new = '3P'
            elif re.search(r'(ται|το)$', fn): new = '3S'
            elif re.search(r'(ον|ουν|αν)$', fn): new = '3P'
        else:          # tagged singular: switch only on endings that cannot be singular
            if tv[0] != 'X' and re.search(r'(σαν|οντο|ουντο|ουσιν?|ονται|ουνται|ωνται)$', fn): new = '3P'
            elif re.search(r'(ωμεν|ωμεθα)$', fn) and mood == 'S': new = '1P'
            elif re.search(r'(σαμεν|ουμεν|ομεν|ομεθα|αμεθα)$', fn) and mood == 'I': new = '1P'
        if new and new != pe + nu: return (f'V.{tv}{mood}{new}', 'person/number follows from the ending')
    return None
over = []; mcount = len(morph)
def code_idx(c):
    if c in codes: return codes[c]
    return None
for b in books:
    for c in b['chapters']:
        p = f"{D}/{b['id']}/{c}.json"; vs = json.load(open(p)); ch = False
        for v in vs:
            for i, t in enumerate(v[1]):
                old = morph[t[2]][0]; r = rule_fix(t[0], old)
                if not r: continue
                ni = code_idx(r[0])
                if ni is None: print('no label for', r[0], t[0]); continue
                over.append({'ref': f"{b['id']} {c}:{v[0]}", 'i': i, 'form': t[0], 'old': old, 'new': r[0], 'why': r[1]})
                t.append(t[2]); t[2] = ni; ch = True   # token = [form, lex, morph, original_morph]
        if ch: json.dump(vs, open(p, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
json.dump(over, open(D + '/parse_overrides.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print('parse overrides', len(over), collections.Counter(o['why'].split(' ')[0] for o in over).most_common(8))
