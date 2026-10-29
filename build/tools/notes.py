#!/usr/bin/env python3
"""Step 5: hand-checked 'Why it matters' notes = New Testament quotations of the LXX. Each note shows the NT Greek
(SBLGNT, CC BY 4.0) and Douay-Rheims English (PD) so the reader can compare wording directly. Comments describe only
wording differences visible in the two Greek texts shown (and, for Ps 39:7, in Brenton's own Greek, eBible grcbrent)."""
import json, os, re, unicodedata
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, '..', 'site', 'data')
SBL = {}
for f in os.listdir('/workspace/src'):
    if f.startswith('sbl_'):
        for l in open('/workspace/src/' + f, encoding='utf-8'):
            if '\t' in l:
                r, t = l.rstrip('\n').split('\t', 1); SBL[r] = re.sub('[⸀⸁⸂⸃⸄⸅]', '', t).strip()
DR = {}
for l in open('/workspace/lxx-audit/src/engDRA/engDRA_vpl.txt', encoding='utf-8-sig'):
    m = re.match(r'(\S+) (\d+:\d+) (.*)', l.strip())
    if m: DR[m.group(1) + ' ' + m.group(2)] = m.group(3)
DRB = {'Matt': 'MAT', 'Mark': 'MAR', 'Luke': 'LUK', 'Acts': 'ACT', 'Rom': 'ROM', 'Heb': 'HEB'}
# (LXX ref, NT ref, kind, key lemmas (highlighted), comment)
T = [
 ('Isa 7:14', 'Matt 1:23', 'quotation', ['παρθένος'], 'Matthew quotes this verse almost word for word in the LXX form: ἡ παρθένος ἐν γαστρὶ ἕξει ("the virgin will conceive / be with child"). The LXX word παρθένος is the one Matthew uses. (Matthew has καλέσουσιν "they will call" where the LXX has καλέσεις "you will call".)'),
 ('Ps 39:7', 'Heb 10:5', 'quotation', ['ὠτίον', 'καταρτίζω'], 'Hebrews 10:5–7 quotes Ps 39(40):7–9 but reads σῶμα δὲ κατηρτίσω μοι, "a body you prepared for me". The Greek printed here (Rahlfs) reads ὠτία, "ears". Brenton\'s own Greek text (Sixtine/Vaticanus tradition) reads σῶμα, which is why the Brenton English beside this verse says "a body". The Latin Vulgate (Gallican Psalter) has aures, "ears".'),
 ('Ps 109:1', 'Matt 22:44', 'quotation', ['κύριος', 'κάθημαι'], 'Jesus quotes this verse (also Mark 12:36, Luke 20:42–43, Acts 2:34–35, Heb 1:13). In Greek both "Lord"s are κύριος: εἶπεν ὁ κύριος τῷ κυρίῳ μου, "the Lord said to my Lord". Matthew has ὑποκάτω ("under") where the LXX has ὑποπόδιον ("footstool").'),
 ('Ps 2:7', 'Acts 13:33', 'quotation', ['υἱός', 'γεννάω'], 'Quoted exactly in Acts 13:33 and Heb 1:5; 5:5: υἱός μου εἶ σύ, ἐγὼ σήμερον γεγέννηκά σε, "You are my son; today I have begotten you" (γεγέννηκα = perfect of γεννάω).'),
 ('Gen 2:24', 'Matt 19:5', 'quotation', ['σάρξ', 'καταλείπω'], 'Jesus quotes this verse on marriage (also Mark 10:7–8; Eph 5:31). Both texts end ἔσονται οἱ δύο εἰς σάρκα μίαν, "the two shall be one flesh" — the words οἱ δύο ("the two") are in the LXX.'),
 ('Gen 1:27', 'Matt 19:4', 'quotation', ['ἄρσην', 'θῆλυς'], 'Jesus quotes the words ἄρσεν καὶ θῆλυ ἐποίησεν αὐτούς, "male and female he made them" (also Mark 10:6).'),
 ('Gen 15:6', 'Rom 4:3', 'quotation', ['πιστεύω', 'λογίζομαι', 'δικαιοσύνη'], 'Paul quotes this verse (also Gal 3:6; James 2:23): ἐπίστευσεν … τῷ θεῷ καὶ ἐλογίσθη αὐτῷ εἰς δικαιοσύνην, "he believed God, and it was counted to him as righteousness". ἐλογίσθη is the aorist passive of λογίζομαι, "reckon, count".'),
 ('Hab 2:4', 'Rom 1:17', 'quotation', ['πίστις', 'δίκαιος', 'ζάω'], 'Paul quotes ὁ δὲ δίκαιος ἐκ πίστεως ζήσεται (also Gal 3:11; Heb 10:38). Note the LXX here has ἐκ πίστεώς μου, "by my faithfulness" (God speaking); Paul\'s wording has no μου.'),
 ('Isa 53:7', 'Acts 8:32', 'quotation', ['πρόβατον', 'ἀμνός', 'σφαγή'], 'This is the passage the Ethiopian official is reading in Acts 8:32–33, quoted in the LXX wording: ὡς πρόβατον ἐπὶ σφαγὴν ἤχθη, "like a sheep he was led to slaughter".'),
 ('Isa 40:3', 'Matt 3:3', 'quotation', ['φωνή', 'βοάω', 'ἔρημος'], 'Applied to John the Baptist in all four Gospels (Matt 3:3; Mark 1:3; Luke 3:4; John 1:23). The Gospels read τὰς τρίβους αὐτοῦ ("his paths") where the LXX has τοῦ θεοῦ ἡμῶν ("of our God").'),
 ('Amos 9:11', 'Acts 15:16', 'quotation', ['σκηνή', 'ἀνοικοδομέω'], 'James quotes Amos 9:11–12 at the Jerusalem council (Acts 15:16–17) in a form close to the LXX: "I will rebuild the tent (σκηνή) of David that has fallen".'),
 ('Joel 3:1', 'Acts 2:17', 'quotation', ['πνεῦμα', 'ἐκχέω'], 'Peter quotes Joel 3:1–5 LXX (= Joel 2:28–32 in English Bibles) at Pentecost, Acts 2:17–21: ἐκχεῶ ἀπὸ τοῦ πνεύματός μου ἐπὶ πᾶσαν σάρκα, "I will pour out of my Spirit on all flesh". Acts begins "in the last days" (ἐν ταῖς ἐσχάταις ἡμέραις) where Joel has μετὰ ταῦτα, "after these things".'),
 ('Ps 117:22', 'Matt 21:42', 'quotation', ['λίθος', 'ἀποδοκιμάζω', 'γωνία'], 'Quoted word for word (also Mark 12:10; Luke 20:17; Acts 4:11; 1 Pet 2:7): "the stone that the builders rejected has become the head of the corner".'),
 ('Deut 6:5', 'Matt 22:37', 'quotation', ['ἀγαπάω', 'καρδία', 'ψυχή'], 'The "greatest commandment" (also Mark 12:30; Luke 10:27). ἀγαπήσεις is future used as a command: "you shall love". Matthew has ἐν ὅλῃ … διανοίᾳ ("with all your mind") where the LXX has ἐξ ὅλης τῆς δυνάμεώς σου ("with all your strength").'),
 ('Lev 19:18', 'Matt 22:39', 'quotation', ['ἀγαπάω', 'πλησίον'], '"You shall love your neighbour as yourself" — ἀγαπήσεις τὸν πλησίον σου ὡς σεαυτόν, quoted identically (also Mark 12:31; Rom 13:9; Gal 5:14; James 2:8).'),
 ('Ps 8:3', 'Matt 21:16', 'quotation', ['αἶνος', 'καταρτίζω', 'νήπιος'], 'Jesus quotes the LXX wording exactly: κατηρτίσω αἶνον, "you have prepared praise" out of the mouths of infants.'),
 ('Isa 61:1', 'Luke 4:18', 'quotation', ['χρίω', 'εὐαγγελίζω', 'πνεῦμα'], 'Jesus reads this passage in the Nazareth synagogue (Luke 4:18–19). ἔχρισέν με, "he anointed me" (χρίω, the verb behind χριστός, "anointed one").'),
 ('Ps 15:10', 'Acts 2:27', 'quotation', ['ᾅδης', 'ὅσιος', 'διαφθορά'], 'Peter quotes Ps 15(16):8–11 at Pentecost (Acts 2:25–28; also Acts 13:35). The LXX διαφθορά, "corruption, decay", is the word the argument in Acts turns on.'),
 ('DanTh 7:13', 'Matt 24:30', 'allusion', ['υἱός', 'ἄνθρωπος', 'νεφέλη'], 'The phrase "coming on/with the clouds of heaven … (one like) a son of man" is echoed in Matt 24:30; 26:64 (and Mark 13:26; 14:62). In the Greek here ὡς υἱὸς ἀνθρώπου has no article: "like a son of man".'),
 ('Exod 3:6', 'Matt 22:32', 'quotation', ['θεός'], 'Jesus quotes "I am the God of Abraham, the God of Isaac and the God of Jacob" in the debate about resurrection (also Mark 12:26; Luke 20:37).'),
]
SHORT = {'Heb 10:5': 'NT reads σῶμα “body” (here ὠτία “ears”)', 'Rom 1:17': 'NT omits μου', 'Matt 3:3': 'NT: τὰς τρίβους αὐτοῦ', 'Acts 2:17': 'NT: ἐν ταῖς ἐσχάταις ἡμέραις', 'Matt 22:37': 'NT: διανοίᾳ for δυνάμεως', 'Matt 22:44': 'NT: ὑποκάτω for ὑποπόδιον'}
notes = {}
def norm(s): return unicodedata.normalize('NFC', s)
for lxx, nt, kind, keys, text in T:
    assert nt in SBL, nt
    b, cv = lxx.split(' '); c, v = cv.split(':')
    vs = {x[0]: x for x in json.load(open(f'{D}/{b}/{c}.json'))}; assert v in vs, lxx
    nb, ncv = nt.split(' ')
    notes.setdefault(f'{b}|{c}|{v}', []).append({'nt': nt, 'kind': kind, 'keys': [norm(k) for k in keys], 'text': text, 'short': SHORT.get(nt, ''),
        'ntg': SBL[nt], 'nte': DR.get(DRB[nb] + ' ' + ncv, ''), 'src': 'NT Greek: SBLGNT (CC BY 4.0); English: Douay-Rheims (PD); note: hand-checked comparison of the two Greek texts'})
json.dump(notes, open(D + '/notes.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('notes', sum(len(x) for x in notes.values()))
