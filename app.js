/* Septuagint Study Bible — vanilla JS, no dependencies. */
(function () {
  'use strict';
  var $ = function (s) { return document.querySelector(s); };
  var BOOKS = null, BYID = {}, LEX = null, MORPH = null, COUNTS = null, cache = {}, occCache = {};
  var GFIX = null, VULW = null, LATLEX = null, NOTES = null, CHN = {}, ENSTAT = {};
  var cur = { book: null, ch: null }, selLex = null;
  /* Books Rahlfs prints in two Greek versions: one list entry each, with a Version picker in the chapter. */
  var VERS = {
    Josh: { name: 'Joshua', v: [['JoshB', 'B text', 'Codex Vaticanus text — Rahlfs’ main text for the whole book (Brenton translated this).'], ['JoshA', 'A text', 'Codex Alexandrinus text, printed separately only where it differs a lot (chapters 15, 18, 19).']] },
    Judg: { name: 'Judges', v: [['JudgB', 'B text', 'Codex Vaticanus family — the text Brenton translated.'], ['JudgA', 'A text', 'Codex Alexandrinus family; it differs throughout, so Rahlfs prints both in full.']] },
    Tob: { name: 'Tobit', v: [['TobBA', 'Short (BA)', 'Shorter text of Codices Vaticanus and Alexandrinus — the one Brenton translated.'], ['TobS', 'Long (S)', 'Longer text of Codex Sinaiticus, often thought closer to the original.']] },
    Sus: { name: 'Susanna', v: [['SusTh', 'Theodotion', 'Later Greek version (2nd c. AD), the one the Church read and Brenton translated.'], ['SusOG', 'Old Greek', 'The original Septuagint translation; freer and quite different in places.']] },
    Dan: { name: 'Daniel', v: [['DanTh', 'Theodotion', 'Later Greek version (2nd c. AD), closer to the Hebrew/Aramaic; the Daniel the Church read and Brenton translated.'], ['DanOG', 'Old Greek', 'The original Septuagint translation (mainly Papyrus 967 and Codex 88); freer and different in places.']] },
    Bel: { name: 'Bel and the Dragon', v: [['BelTh', 'Theodotion', 'Later Greek version (2nd c. AD), the one the Church read and Brenton translated.'], ['BelOG', 'Old Greek', 'The original Septuagint translation; different wording and details.']] }
  }, VBASE = {}, VIS = [];
  Object.keys(VERS).forEach(function (k) { VERS[k].v.forEach(function (x) { VBASE[x[0]] = k; }); });
  function prefOf(base) { var p = load('lxx-ver-' + base); return VERS[base].v.some(function (x) { return x[0] === p; }) ? p : VERS[base].v[0][0]; }
  function computeVis() {   /* visible book order: one entry per book, Susanna–Daniel–Bel in Rahlfs order */
    var seen = {}, out = [];
    BOOKS.forEach(function (b) {
      var base = VBASE[b.id];
      if (base === 'Bel' || base === 'Dan' || base === 'Sus') { if (!seen.SDB) { seen.SDB = 1; ['Sus', 'Dan', 'Bel'].forEach(function (k) { out.push(BYID[prefOf(k)]); }); } return; }
      if (!base) { out.push(b); return; }
      if (!seen[base]) { seen[base] = 1; out.push(BYID[prefOf(base)]); }
    });
    VIS = out; VIS.forEach(function (b, i) { b.vi = i; });
  }
  function bookName(b) { var base = VBASE[b.id]; return base ? VERS[base].name : b.name; }
  var GROUPS = [['Law (Pentateuch)', 'Gen'], ['Historical books', 'Josh'], ['Poetry & Wisdom', 'Ps'], ['Prophets', 'Hos']];

  function get(url) {
    if (cache[url]) return cache[url];
    return (cache[url] = fetch(url).then(function (r) { if (!r.ok) throw new Error(r.status + ' ' + url); return r.json(); }));
  }
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function norm(s) { return s.normalize('NFD').replace(/[\u0300-\u036f\u1fbd\u1fbf\u1ffe\u02bc\u2019]/g, '').toLowerCase().replace(/ς/g, 'σ'); }
  function store(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function load(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }

  function init() {
    Promise.all([get('data/books.json'), get('data/morph.json'), get('data/chapnotes.json').catch(function () { return {}; })]).then(function (r) {
      BOOKS = r[0]; MORPH = r[1]; CHN = r[2] || {};
      BOOKS.forEach(function (b, i) { b.i = i; BYID[b.id] = b; }); computeVis();
      buildBookList();
      window.addEventListener('hashchange', route);
      route();
      get('data/lexicon.json').then(function (l) { LEX = l; }); get('data/counts.json').then(function (c) { COUNTS = c; });
      get('data/gloss_fixes.json').then(function (g) { GFIX = g; }).catch(function () {});
    }).catch(fail);
    $('#menuBtn').onclick = function () { toggleDrawer(true); };
    $('#locBtn').onclick = function () { toggleDrawer(true, true); };
    document.querySelectorAll('[data-close]').forEach(function (b) { b.onclick = function () { toggleDrawer(false); }; });
    $('#scrim').onclick = function () { toggleDrawer(false); closePanel(); };
    $('#panelClose').onclick = closePanel;
    var pfs = +(load('lxx-pfs') || 1);
    function applyPfs() { $('#panel').style.setProperty('--pfs', pfs + 'rem'); }
    applyPfs();
    $('#pSmaller').onclick = function () { pfs = Math.max(0.85, +(pfs - 0.1).toFixed(2)); store('lxx-pfs', pfs); applyPfs(); };
    $('#pLarger').onclick = function () { pfs = Math.min(1.4, +(pfs + 0.1).toFixed(2)); store('lxx-pfs', pfs); applyPfs(); };
    $('#prevBtn').onclick = function () { step(-1); };
    $('#nextBtn').onclick = function () { step(1); };
    $('#searchBtn').onclick = function () { location.hash = '#/search'; };
    $('#themeBtn').onclick = function () {
      var d = document.documentElement, dark = d.dataset.theme ? d.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
      d.dataset.theme = dark ? 'light' : 'dark'; store('lxx-theme', d.dataset.theme);
    };
    var sizes = ['1.1rem', '1.3rem', '1.55rem', '1.85rem'], si = +(load('lxx-size') || 1);
    function applySize() { document.documentElement.style.setProperty('--fs', sizes[si]); }
    applySize();
    $('#sizeBtn').onclick = function () { si = (si + 1) % sizes.length; store('lxx-size', si); applySize(); };
    /* English: Brenton -> LXX2012 -> both -> off */
    var EMODES = ['b', 'x', 'bx', '0'], ELAB = { b: 'Brenton', x: '2012', bx: 'Both', '0': 'EN' };
    function applyEn(m) {
      document.body.classList.remove('noen', 'en-b', 'en-x', 'en-bx');
      document.body.classList.add(m === '0' ? 'noen' : 'en-' + m);
      var bt = $('#enBtn'); bt.classList.toggle('on', m !== '0'); bt.textContent = m === '0' ? 'EN' : ELAB[m];
      bt.title = 'English: ' + { b: 'Brenton (1844)', x: 'LXX2012 (2012 update of Brenton)', bx: 'Brenton + LXX2012', '0': 'hidden' }[m] + ' — tap to switch';
    }
    var em = load('lxx-en'); if (em === '1' || !em) em = 'b'; applyEn(em);
    $('#enBtn').onclick = function () { em = EMODES[(EMODES.indexOf(em) + 1) % 4]; store('lxx-en', em); applyEn(em); };
    document.addEventListener('keydown', function (e) {
      if (/INPUT|TEXTAREA/.test(e.target.tagName)) return;
      if (e.key === 'Escape') { closePanel(); toggleDrawer(false); }
      if (e.key === 'ArrowLeft' && cur.book) step(-1);
      if (e.key === 'ArrowRight' && cur.book) step(1);
    });
  }
  function fail(e) { $('#main').innerHTML = '<p>Could not load data: ' + esc(e.message) + '. If you opened the file directly, serve the folder over http (see README).</p>'; }

  function buildBookList() {
    var h = '', g = 0;
    VIS.forEach(function (b) {
      if (g < GROUPS.length && (GROUPS[g][1] === b.id || GROUPS[g][1] === VBASE[b.id])) { h += '<div class="grp">' + GROUPS[g][0] + '</div>'; g++; }
      h += '<button class="bk" data-b="' + b.id + '">' + esc(bookName(b)) + '</button><div class="chs" data-for="' + b.id + '" hidden></div>';
    });
    $('#bookList').innerHTML = h;
    $('#bookList').onclick = function (e) {
      var bt = e.target.closest('.bk'); if (bt) {
        var box = $('.chs[data-for="' + bt.dataset.b + '"]'), b = BYID[bt.dataset.b];
        if (b.chapters.length === 1) { location.hash = '#/' + b.id + '/' + b.chapters[0]; return; }
        if (!box.innerHTML) box.innerHTML = b.chapters.map(function (c) { return '<a href="#/' + b.id + '/' + c + '">' + (c === 'Prolog' ? 'Prol.' : c) + '</a>'; }).join('');
        box.hidden = !box.hidden;
      }
      if (e.target.closest('.chs a')) toggleDrawer(false);
    };
  }
  function toggleDrawer(open, showCur) {
    $('#books').hidden = !open; $('#scrim').hidden = !open && $('#panel').hidden;
    if (open && cur.book) {
      document.querySelectorAll('.bk').forEach(function (x) { x.classList.toggle('cur', x.dataset.b === cur.book); });
      if (showCur) { var bt = $('.bk[data-b="' + cur.book + '"]'); var box = bt.nextElementSibling; if (box.hidden) bt.click(); bt.scrollIntoView({ block: 'center' }); }
    }
  }

  function route() {
    var h = decodeURIComponent(location.hash.replace(/^#\/?/, '')), q = '';
    var qi = h.indexOf('?'); if (qi >= 0) { q = h.slice(qi + 1); h = h.slice(0, qi); }
    var p = h.split('/').filter(Boolean);
    closePanel();
    if (p[0] === 'about') return about();
    if (p[0] === 'search') return search(new URLSearchParams(q).get('q') || '', new URLSearchParams(q).get('lex'));
    if (p[0] && VERS[p[0]]) { var vb = BYID[prefOf(p[0])]; location.replace('#/' + vb.id + '/' + (p[1] && vb.chapters.map(String).indexOf(p[1]) >= 0 ? p[1] : vb.chapters[0]) + (p[2] ? '/' + p[2] : '') + (q ? '?' + q : '')); return; }
    if (!p[0] || !BYID[p[0]]) {
      var last = load('lxx-last'); location.replace('#/' + (last && BYID[last.split('/')[0]] ? last : 'Gen/1')); return;
    }
    var b = BYID[p[0]], ch = p[1] && b.chapters.map(String).indexOf(p[1]) >= 0 ? p[1] : String(b.chapters[0]);
    var params = new URLSearchParams(q);
    chapter(b, ch, p[2], params.get('lex'));
  }
  function step(d) {
    if (!cur.book) return;
    var b = BYID[cur.book], i = b.chapters.map(String).indexOf(cur.ch) + d;
    if (i < 0) { b = VIS[b.vi - 1]; if (!b) return; i = b.chapters.length - 1; }
    else if (i >= b.chapters.length) { b = VIS[b.vi + 1]; if (!b) return; i = 0; }
    location.hash = '#/' + b.id + '/' + b.chapters[i];
  }
  function chName(b, ch) { return ch === 'Prolog' ? 'Prologue' : ch; }

  function chapter(b, ch, verse, lex) {
    cur = { book: b.id, ch: ch }; store('lxx-last', b.id + '/' + ch);
    var vbase = VBASE[b.id];
    if (vbase && prefOf(vbase) !== b.id) { store('lxx-ver-' + vbase, b.id); computeVis(); buildBookList(); }
    $('#locBtn').textContent = bookName(b) + ' ' + chName(b, ch);
    document.title = b.name + ' ' + chName(b, ch) + ' — Septuagint Study Bible';
    $('#main').innerHTML = '<p class="loading">Loading…</p>';
    get('data/' + b.id + '/' + ch + '.json').then(function (vs) {
      ENSTAT = {};
      if (NOTES === null) onceGet('data/notes.json').then(function (n) { NOTES = n || {}; markNotes(b.id, ch); });
      var h = '<h1>' + esc(bookName(b)) + ' ' + esc(chName(b, ch)) + (b.id === 'Ps' ? '<small>Greek (LXX) psalm numbering — e.g. LXX Ps 22 = Hebrew/English Ps 23.</small>' : '') + '</h1>';
      if (vbase) {
        var vcur = VERS[vbase].v.filter(function (x) { return x[0] === b.id; })[0];
        h += '<div class="verpick"><span class="vlab">Version</span><span class="vseg" role="group" aria-label="Greek version">' + VERS[vbase].v.map(function (x) {
          var t = BYID[x[0]], has = t.chapters.map(String).indexOf(String(ch)) >= 0;
          if (x[0] === b.id) return '<span class="vopt on" aria-current="true" title="' + esc(x[2]) + '">' + esc(x[1]) + '</span>';
          if (!has) return '<span class="vopt off" title="' + esc(x[1] + ': not extant for this chapter (' + (t.chapters.length < 6 ? 'only chapters ' + t.chapters.join(', ') : 'different chapters') + '). ' + x[2]) + '">' + esc(x[1]) + '</span>';
          return '<a class="vopt" data-v="' + x[0] + '" href="#/' + x[0] + '/' + ch + '" title="' + esc(x[2]) + '">' + esc(x[1]) + '</a>';
        }).join('') + '</span><span class="vexp">' + esc(vcur[2]) + '</span></div>';
      }
      var cn = CHN[b.id + '/' + ch];
      if (cn) h += '<div class="badge">⚠ <b>English alignment note for this chapter.</b> ' + [cn.moved ? cn.moved + ' verse' + (cn.moved > 1 ? 's' : '') + ' re-matched to Brenton’s numbering (marked [Br. …])' : '', cn.hidden ? cn.hidden + ' verse' + (cn.hidden > 1 ? 's' : '') + ' with English hidden (no reliable match)' : '', cn.joined ? cn.joined + ' verse' + (cn.joined > 1 ? 's' : '') + ' whose English is included with a neighbouring verse' : '', cn.differs ? cn.differs + ' verse' + (cn.differs > 1 ? 's' : '') + ' where Brenton translated a different Greek wording (≠)' : ''].filter(Boolean).join('; ') + '. <a href="#/about">Why?</a></div>';
      vs.forEach(function (v) {
        h += '<p class="verse" id="v' + esc(v[0]) + '"><span class="vn">' + esc(v[0]) + '</span>';
        v[1].forEach(function (t, i) { h += '<span class="w" data-l="' + t[1] + '" data-m="' + t[2] + '"' + (t.length > 3 ? ' data-o="' + t[3] + '"' : '') + '>' + esc(t[0]) + '</span> '; });
        var es = v[3]; if (es) ENSTAT[v[0]] = es;
        if (v[2]) h += '<span class="en en1" title="Brenton 1844">' + esc(v[2]) + (es && es.s === 'm' ? ' <span class="enm" title="Brenton numbers this ' + esc(es.br) + '">[Br. ' + esc(es.br) + ']</span>' : '') + (es && (es.s === 'd' || es.gd) ? ' <span class="enm warn" title="Brenton translated slightly different Greek here: his Greek text has different wording or divides the verses differently, so the English may include or omit words.">≠ Greek differs</span>' : '') + '</span>';
        else if (es && (es.s === 'h' || es.s === 'j') && b.en) h += '<span class="en none">' + (es.s === 'h' ? 'English hidden — Brenton’s verse does not match this Greek (no reliable match found).' : 'English for this verse is included with v. ' + esc(es['with']) + '.') + '</span>';
        h += '</p>';
      });
      var bi = b.chapters.map(String).indexOf(ch);
      var prev = bi > 0 ? [b, b.chapters[bi - 1]] : (VIS[b.vi - 1] ? [VIS[b.vi - 1], VIS[b.vi - 1].chapters.slice(-1)[0]] : null);
      var next = bi < b.chapters.length - 1 ? [b, b.chapters[bi + 1]] : (VIS[b.vi + 1] ? [VIS[b.vi + 1], VIS[b.vi + 1].chapters[0]] : null);
      h += '<nav class="chnav">' + (prev ? '<a href="#/' + prev[0].id + '/' + prev[1] + '">‹ ' + esc(bookName(prev[0])) + ' ' + prev[1] + '</a>' : '<span></span>') +
        (next ? '<a href="#/' + next[0].id + '/' + next[1] + '">' + esc(bookName(next[0])) + ' ' + next[1] + ' ›</a>' : '') + '</nav>';
      if (!b.en) h += '<p class="small">' + (vbase ? 'No English is shown for this version: Brenton translated the ' + esc(VERS[vbase].v[0][1]) + ' version.' : 'No Brenton English is available for this book.') + '</p>';
      h += '<p class="small">Greek: Rahlfs 1935 via CCAT/eliranwong (CC BY-NC-SA 4.0). English: Brenton 1844/1851 (public domain; translated from the Vatican-based Greek printed by Bagster) and LXX2012 (Michael Paul Johnson’s 2012 American-English update of Brenton, public domain; same Greek) — archaic 19th-century English, translated from a different Greek edition, so wording and verse division sometimes differ from the Greek shown. <a href="#/about">Sources &amp; caveats</a></p>';
      var m = $('#main'); m.innerHTML = h; m.onclick = onWord;
      if (b.en) onceGet('data/en2/' + b.id + '/' + ch + '.json').then(function (e2) {
        if (!e2 || cur.book !== b.id || String(cur.ch) !== String(ch)) return;
        Object.keys(e2).forEach(function (vn) {
          var p = document.getElementById('v' + vn); if (!p) return;
          var s = document.createElement('span'); s.className = 'en en2'; s.title = 'LXX2012 — 2012 American-English update of Brenton (same Greek)'; s.textContent = e2[vn];
          var b1 = p.querySelector('.en1'); if (b1) b1.after(s); else p.appendChild(s);
        });
      });
      if (verse) { var el = document.getElementById('v' + verse); if (el) { el.scrollIntoView({ block: 'center' }); el.classList.add('flash'); } }
      else window.scrollTo(0, 0);
      if (lex) highlight(lex);
      if (NOTES) markNotes(b.id, ch);
    }).catch(fail);
  }
  function markNotes(bid, ch) {
    Object.keys(NOTES || {}).forEach(function (k) {
      var p = k.split('|'); if (p[0] !== bid || p[1] !== String(ch)) return;
      var el = document.getElementById('v' + p[2]); if (!el || el.querySelector('.ntm')) return;
      var m = document.createElement('span'); m.className = 'ntm'; m.title = 'Quoted in the New Testament — tap a word for details';
      m.textContent = 'NT ' + NOTES[k].map(function (x) { return x.nt; }).join(', ');
      el.querySelector('.vn').after(m);
    });
  }
  function highlight(lex) {
    selLex = lex;
    document.querySelectorAll('.w.same').forEach(function (x) { x.classList.remove('same'); });
    if (lex) document.querySelectorAll('.w[data-l="' + lex + '"]').forEach(function (x) { x.classList.add('same'); });
  }
  function onWord(e) {
    var w = e.target.closest('.w'); if (!w) return;
    document.querySelectorAll('.w.sel').forEach(function (x) { x.classList.remove('sel'); });
    w.classList.add('sel'); highlight(w.dataset.l);
    var ref = w.parentNode.id.slice(1);
    (LEX ? Promise.resolve(LEX) : get('data/lexicon.json').then(function (l) { return (LEX = l); })).then(function () { showWord(w.textContent, w.dataset.l, +w.dataset.m, ref, w.dataset.o != null ? +w.dataset.o : null, Array.prototype.indexOf.call(w.parentNode.querySelectorAll('.w'), w)); });
  }
  /* ---------- grammar help (written for this site) ---------- */
  var GRAM = {
    present: 'Present: action viewed as ongoing or repeated, usually in present time ("is doing", "does").',
    imperfect: 'Imperfect: ongoing or repeated action in the PAST ("was doing", "used to do"). Has the augment ἐ- at the front.',
    future: 'Future: action in the future ("will do"). Often marked by -σ- before the ending.',
    aorist: 'Aorist: action viewed as a simple whole event, without focusing on duration — in the indicative usually a simple past ("did", "made"). Very common in narrative.',
    perfect: 'Perfect: a completed action whose result still stands ("has done", "stands written"). Often doubled first letter (reduplication), e.g. γέ-γραπται.',
    pluperfect: 'Pluperfect: a completed past action with a past result ("had done").',
    active: 'Active voice: the subject does the action ("he made").',
    middle: 'Middle voice: the subject acts for or on itself, or is involved in the action. Many verbs are middle in form but active in meaning ("deponent").',
    passive: 'Passive voice: the subject receives the action ("it was made").',
    indicative: 'Indicative mood: a statement or question about what is/was/will be.',
    subjunctive: 'Subjunctive mood: what may/might happen — purpose (ἵνα…), conditions (ἐάν…), "let us…", prohibitions with μή.',
    optative: 'Optative mood: a wish or remote possibility ("may it be…", μὴ γένοιτο "may it not be").',
    imperative: 'Imperative mood: a command or request ("do!", "let him do!").',
    infinitive: 'Infinitive: the verb as a noun — "to do", "doing". Often after verbs like "want", "be able", or with the article (τοῦ ποιῆσαι "in order to do").',
    participle: 'Participle: a verbal adjective — "doing", "having done", "the one who does". It has case, number and gender like an adjective.',
    nominative: 'Nominative case: usually the SUBJECT of the sentence (who/what does the action), or after "is".',
    genitive: 'Genitive case: "of" — possession, source, part ("the word OF God"). Also after some prepositions (ἐκ, ἀπό, διά "through").',
    dative: 'Dative case: "to/for" (indirect object), "in/with/by" (location, means). Also after ἐν and σύν.',
    accusative: 'Accusative case: usually the DIRECT OBJECT (who/what receives the action). Also after εἰς, πρός and others.',
    vocative: 'Vocative case: direct address ("O Lord!").',
    singular: 'Singular: one person or thing.', plural: 'Plural: more than one.', dual: 'Dual: exactly two (rare in the LXX).',
    masculine: 'Masculine grammatical gender.', feminine: 'Feminine grammatical gender.', neuter: 'Neuter grammatical gender.',
    '1st person': '1st person: I / we.', '2nd person': '2nd person: you.', '3rd person': '3rd person: he / she / it / they.',
    article: 'The article ὁ, ἡ, τό = "the". Greek has no word for "a"; an English "a" usually means no article in Greek. The article agrees with its noun in case, number and gender — useful for working out a noun\'s case.',
    lemma: 'Lemma: the dictionary form you look a word up under (for verbs, the 1st person singular present: "I do").'
  };
  var TENSE = { P: 'present', I: 'imperfect', F: 'future', A: 'aorist', X: 'perfect', Y: 'pluperfect' };
  var VOICE = { A: 'active', M: 'middle', P: 'passive', E: 'middle/passive', D: 'middle', O: 'passive', N: 'middle/passive' };
  var MOOD = { I: 'indicative', S: 'subjunctive', O: 'optative', D: 'imperative', N: 'infinitive', P: 'participle' };
  var CASE = { N: 'nominative', G: 'genitive', D: 'dative', A: 'accusative', V: 'vocative' };
  var NUM = { S: 'singular', P: 'plural', D: 'dual' }, GEN = { M: 'masculine', F: 'feminine', N: 'neuter' };
  var PN = { '1S': 'I', '2S': 'you (sg.)', '3S': 'he/she/it', '1P': 'we', '2P': 'you (pl.)', '3P': 'they' };
  function pcode(code) {   // CCAT code -> structured parse
    var p = { code: code, pos: code.split('.')[0] }, rest = code.split('.')[1] || '';
    var v = /^V\.([PIFAXY])([AMPEDON])([ISODNP])(.*)$/.exec(code);
    if (v) {
      p.verb = true; p.t = v[1]; p.v = v[2]; p.m = v[3];
      var r = v[4], q;
      if (p.m === 'P' && (q = /^([NGDAV])([SPD])([MFN])/.exec(r))) { p.c = q[1]; p.n = q[2]; p.g = q[3]; }
      else if ((q = /^([123])([SPD])/.exec(r))) { p.pe = q[1]; p.n = q[2]; }
      return p;
    }
    var q2 = /([NGDAV])([SPD])([MFN])?/.exec(rest);
    if (q2) { p.c = q2[1]; p.n = q2[2]; p.g = q2[3] || ''; }
    return p;
  }
  function chip(term, label) { return '<button class="chip" data-g="' + esc(term) + '">' + esc(label || term) + '</button>'; }
  function parseChips(p) {
    var h = '';
    if (p.verb) {
      h += chip(TENSE[p.t]) + chip(VOICE[p.v].split('/')[0], VOICE[p.v]) + chip(MOOD[p.m]);
      if (p.pe) h += chip(p.pe + (p.pe === '1' ? 'st' : p.pe === '2' ? 'nd' : 'rd') + ' person', p.pe + (p.pe === '1' ? 'st' : p.pe === '2' ? 'nd' : 'rd') + ' pers.') + chip(NUM[p.n]);
      if (p.c) h += chip(CASE[p.c]) + chip(NUM[p.n]) + chip(GEN[p.g]);
    } else if (p.c) {
      h += chip(CASE[p.c]) + chip(NUM[p.n]) + (p.g ? chip(GEN[p.g]) : '');
    }
    return h;
  }
  function hint(p, gloss) {   // a short, honest "how to read it" line
    var g = (gloss || '').split(/[;,(]/)[0].trim();
    if (p.verb) {
      if (p.m === 'I' && p.pe) {
        var who = PN[p.pe + p.n] || '';
        var how = { P: 'is/are …-ing, …s', I: 'was/were …-ing (ongoing past)', F: 'will …', A: 'simple past (…ed)', X: 'has/have …ed (result stands)', Y: 'had …ed' }[p.t];
        return 'Reads like: <b>' + esc(who) + '</b> + ' + esc(how) + (p.v === 'P' ? ' — passive: the subject <i>receives</i> the action' : '') + '.';
      }
      if (p.m === 'D') return 'A command' + (p.pe === '3' ? ' to a third party: “let him/them …”' : ': “…!”') + '.';
      if (p.m === 'S') return 'Subjunctive: look for ἵνα (“so that”), ἐάν (“if”), ὅταν (“whenever”) or a “let us …” sense nearby.';
      if (p.m === 'O') return 'Optative: usually a wish — “may … ”.';
      if (p.m === 'N') return 'Infinitive: “to …”.';
      if (p.m === 'P') return 'Participle: “…-ing / having …ed / the one who …”. Its case (' + (CASE[p.c] || '') + ') shows which noun it describes.';
    }
    if (p.c) return { N: 'Nominative: probably the subject (or after “is”).', G: 'Genitive: often “of …”.', D: 'Dative: often “to/for …” or “in/by/with …”.', A: 'Accusative: often the direct object, or after εἰς/πρός (“into/to”).', V: 'Vocative: someone being addressed — “O …!”.' }[p.c];
    return '';
  }
  /* ---------- paradigm from forms attested in the LXX ---------- */
  function paradigm(fd, curMi, curForm) {
    var rows = fd.f.map(function (x) { return { f: x[0], mi: x[1], n: x[2], ref: x[3], p: pcode((MORPH[x[1]] || [''])[0]) }; });
    var curF = norm(curForm);
    function cell(list) {
      if (!list || !list.length) return '<td class="empty">–</td>';
      var cur = list.some(function (x) { return x.mi === curMi && norm(x.f) === curF; });
      return '<td' + (cur ? ' class="curcell"' : '') + '>' + list.slice(0, 3).map(function (x) {
        var r = x.ref.split('|');
        return '<a class="pf' + (x.mi === curMi && norm(x.f) === curF ? ' cur' : '') + '" href="#/' + r[0] + '/' + r[1] + '/' + r[2] + '" title="' + x.n + '× · first at ' + esc(r[0] + ' ' + r[1] + ':' + r[2]) + '">' + esc(x.f) + '<sup>' + x.n + '</sup></a>';
      }).join(' ') + '</td>';
    }
    var h = '', verbs = rows.filter(function (x) { return x.p.verb; });
    if (verbs.length) {
      var groups = {}, order = [];
      verbs.forEach(function (x) {
        var key = x.p.t + x.p.v + (x.p.m === 'P' ? 'P' : x.p.m === 'N' ? 'N' : 'F');
        if (!groups[key]) { groups[key] = []; order.push(key); } groups[key].push(x);
      });
      var tOrd = 'PIFAXY', vOrd = 'AMEDPON';
      order.sort(function (a, b) { return tOrd.indexOf(a[0]) - tOrd.indexOf(b[0]) || vOrd.indexOf(a[1]) - vOrd.indexOf(b[1]) || 'FNP'.indexOf(a[2]) - 'FNP'.indexOf(b[2]); });
      var curKey = order.filter(function (k) { return groups[k].some(function (x) { return x.mi === curMi; }); })[0];
      if (curKey) order = [curKey].concat(order.filter(function (k) { return k !== curKey; }));
      order.forEach(function (key) {
        var list = groups[key], t = TENSE[key[0]], v = VOICE[key[1]], open = list.some(function (x) { return x.mi === curMi; });
        var title = t + ' ' + v + (key[2] === 'P' ? ' participle' : key[2] === 'N' ? ' infinitive' : '');
        var tot = list.reduce(function (s, x) { return s + x.n; }, 0), body = '';
        if (key[2] === 'F') {
          var moods = ['I', 'S', 'O', 'D'].filter(function (m) { return list.some(function (x) { return x.p.m === m; }); });
          body = '<table class="pd"><tr><th></th>' + moods.map(function (m) { return '<th>' + MOOD[m].slice(0, 4) + '.</th>'; }).join('') + '</tr>';
          ['1S', '2S', '3S', '1P', '2P', '3P'].forEach(function (pn) {
            if (!list.some(function (x) { return x.p.pe + x.p.n === pn; })) return;
            body += '<tr><th title="' + esc(PN[pn]) + '">' + pn[0] + (pn[1] === 'S' ? ' sg' : ' pl') + '</th>' + moods.map(function (m) {
              return cell(list.filter(function (x) { return x.p.m === m && x.p.pe + x.p.n === pn; }));
            }).join('') + '</tr>';
          });
          body += '</table>';
        } else if (key[2] === 'N') {
          body = '<table class="pd"><tr>' + cell(list) + '</tr></table>';
        } else body = nounTable(list, cell);
        h += '<details class="pg"' + (open && !h ? ' open' : '') + '><summary>' + esc(title) + ' <span class="small">' + tot + '×</span></summary>' + body + '</details>';
      });
    } else {
      var nom = rows.filter(function (x) { return x.p.c; });
      if (nom.length) h = nounTable(nom, cell);
    }
    return h;
  }
  function nounTable(list, cell) {
    var cols = [];
    ['S', 'P', 'D'].forEach(function (n) {
      ['M', 'F', 'N', ''].forEach(function (g) { if (list.some(function (x) { return x.p.n === n && (x.p.g || '') === g; })) cols.push(n + g); });
    });
    var cases = ['N', 'G', 'D', 'A', 'V'].filter(function (c) { return list.some(function (x) { return x.p.c === c; }); });
    if (!cols.length) return '';
    var h = '<table class="pd"><tr><th></th>' + cols.map(function (c) { return '<th>' + (c[0] === 'S' ? 'sg' : c[0] === 'P' ? 'pl' : 'du') + (c[1] ? ' ' + c[1].toLowerCase() : '') + '</th>'; }).join('') + '</tr>';
    cases.forEach(function (c) {
      h += '<tr><th>' + CASE[c].slice(0, 3) + '.</th>' + cols.map(function (col) { return cell(list.filter(function (x) { return x.p.c === c && x.p.n === col[0] && (x.p.g || '') === (col[1] || ''); })); }).join('') + '</tr>';
    });
    return h + '</table>';
  }
  /* ---------- the word panel ---------- */
  var VB_NAMES = { Jer: 'Jeremiah (the LXX chapter order differs from the Vulgate)', Sir: 'Sirach (Vulgate follows a different text and order)', TobBA: 'Tobit (the Vulgate was made from a different original)', TobS: 'Tobit (the Vulgate was made from a different original)', Jdt: 'Judith (the Vulgate was made from a different original)' };
  function bucket(dir, lid) { return get('data/' + dir + '/' + Math.floor(lid / 100) + '.json').then(function (d) { return d[lid]; }).catch(function () { return null; }); }
  function onceGet(url) { return get(url).catch(function () { return null; }); }
  function hebLine(s) {
    if (!s) return '';
    var t = s.replace(/^in LXX (chiefly |mostly |usually |always )?(for\s*)?/i, '').split(/[\d(]|\bal\.|;/)[0].replace(/[\s,.;:]+$/, '').replace(/[,\s]+[A-Z][a-z]*\.?$/, '');
    if (!t || t.length > 45 || !/[\u0590-\u05ff]/.test(t)) return '';
    return '<div class="sub">Heb. ' + esc(t) + '</div>';
  }
  function showWord(form, lid, mi, ref, omi, wi) {
    var L = LEX[lid] || ['', '', '', '', '', ''], M = MORPH[mi] || ['', ''], p = pcode(M[0]);
    var lemma = L[0], enc = encodeURIComponent, nChap = document.querySelectorAll('.w[data-l="' + lid + '"]').length;
    var posName = (L[2] || M[1].split(':')[0]).replace(/^Verbs$/, 'Verb');
    var st = L[5] && /^G\d+$/.test(L[5]) && +L[5].slice(1) <= 5624 ? L[5] : '';
    var lsjUrl = L[4] ? 'https://www.perseus.tufts.edu/hopper/text?doc=Perseus:text:1999.04.0057:entry=' + enc(L[4]) : 'https://www.perseus.tufts.edu/hopper/searchresults?q=' + enc(lemma);
    var fix = GFIX && GFIX[lid];
    var prs = M[1].replace(/^[^:]+: ?/, ''), pl = posName.toLowerCase() + (prs && prs.toLowerCase() !== posName.toLowerCase() ? ': ' + prs : '');
    var h = '<div class="sum"><div class="srow"><span class="slem" lang="grc">' + esc(lemma) + '</span><span class="tr">' + esc(L[3]) + '</span><span class="sfreq" id="sfreq" title="Occurrences in the LXX"></span></div>' +
      '<div class="sdef">' + esc(L[1] || '—') + (fix ? '<sup class="fx" title="Corrected gloss (source had “' + esc(fix.old) + '”)">*</sup>' : '') + '</div>' +
      '<div class="sparse"><span lang="grc" class="sform">' + esc(form) + '</span> ' + esc(pl) + '</div>' +
      '<button class="more" id="moreBtn" aria-expanded="false">More ▾</button></div>' +
      '<div id="more" hidden><div class="ph"><span class="form" hidden></span>' +
      '<div class="chips"><span class="chip pos">' + esc(posName) + '</span>' + (p.pos === 'RA' ? chip('article') : '') + parseChips(p) +
      (omi != null && MORPH[omi] ? '<span class="chip fx" title="Tag corrected; source had ' + esc(MORPH[omi][0]) + '">corrected</span>' : '') + '</div>' +
      '<div id="gexp" class="gexp" hidden></div></div>' +
      '<div class="tabs" id="mtabs"></div><div id="mbody" class="mbody"></div>' +
      '<details class="row" id="formsRow"><summary><span class="rl">Forms</span> <span class="rv">' + esc(M[1].replace(/^[^:]+: ?/, '')) + '</span></summary><div id="pdBox"></div></details>' +
      '<div class="row" id="etyRow" hidden></div>' +
      '<div class="row" id="refRow"><span class="rl">Refs</span> <span id="refChips"><a class="rc" href="#/search?lex=' + lid + '" id="freqChip">' + nChap + '× ch.</a></span><div id="refOpen" class="refopen" hidden></div></div>' +
      '<div class="row lat" id="latRow" hidden></div>' +
      '<div class="links"><a target="_blank" rel="noopener" href="https://logeion.uchicago.edu/' + enc(lemma) + '">Logeion</a><a target="_blank" rel="noopener" href="' + lsjUrl + '">LSJ</a>' +
      (st ? '<a target="_blank" rel="noopener" href="https://www.blueletterbible.org/lexicon/' + st.toLowerCase() + '/kjv/tr/0-1/">' + esc(st) + '</a>' : '') +
      '<a target="_blank" rel="noopener" href="https://en.wiktionary.org/wiki/' + enc(lemma) + '#Ancient_Greek">Wiktionary</a></div></div>';
    $('#panelBody').innerHTML = h;
    $('#panel').hidden = false; $('#panel').scrollTop = 0; document.body.classList.add('pop');
    setExp(innerWidth >= 1000 && load('lxx-exp') === '1');
    $('#panelBody').onclick = function (e) {
      if (e.target.closest('#moreBtn')) { setExp($('#more').hidden); store('lxx-exp', $('#more').hidden ? '0' : '1'); return; }
      var c = e.target.closest('.chip[data-g]');
      if (c) {
        var g = $('#gexp'), t = GRAM[c.dataset.g] || GRAM[c.dataset.g.split('/')[0]]; if (!t) return;
        if (!g.hidden && g.dataset.k === c.dataset.g) { g.hidden = true; return; }
        g.dataset.k = c.dataset.g; g.textContent = t.replace(/^[^:]+: /, ''); g.hidden = false; return;
      }
      var tb = e.target.closest('.tab'); if (tb) { showTab(+tb.dataset.i); return; }
      var rc = e.target.closest('.rc[data-n]');
      if (rc) { var o = $('#refOpen'); if (!o.hidden && o.dataset.n === rc.dataset.n) { o.hidden = true; return; } o.dataset.n = rc.dataset.n; o.innerHTML = rc.dataset.line; o.hidden = false; }
    };
    var token = (showWord.tok = {}); function alive() { return showWord.tok === token; }
    var TABS = [];
    function showTab(i) {
      document.querySelectorAll('#mtabs .tab').forEach(function (x, j) { x.classList.toggle('on', i === j); });
      var t = TABS[i]; if (!t) return;
      $('#mbody').innerHTML = '<ol class="senses">' + t.s.map(function (s) { return '<li>' + esc(s) + '</li>'; }).join('') + '</ol>' +
        (t.extra || '') + '<div class="src">' + t.src + '</div>';
      store('lxx-tab', t.key);
    }
    Promise.all([bucket('dict', lid), bucket('lsj', lid)]).then(function (r) {
      if (!alive()) return;
      var a = r[0], l = r[1];
      if (a && a.s && a.s.length) TABS.push({ key: 'as', name: 'Abbott-Smith', s: a.s, src: 'STEPBible TBESG · CC BY 4.0', extra: hebLine(a.lxx) });
      else if (a && a.g) TABS.push({ key: 'as', name: 'Abbott-Smith', s: [a.g], src: 'STEPBible TBESG · CC BY 4.0' });
      if (l && l.s.length) TABS.push({ key: 'lsj', name: 'LSJ', s: l.s, src: 'STEPBible TFLSJ (LSJ) · CC BY 4.0' });
      if (!TABS.length) TABS.push({ key: 'g', name: 'Gloss', s: [L[1] || '—'], src: 'CCAT/Eliran Wong lexicon' });
      $('#mtabs').innerHTML = TABS.map(function (t, i) { return '<button class="tab" data-i="' + i + '">' + esc(t.name) + '</button>'; }).join('');
      var pref = load('lxx-tab'), i0 = 0; TABS.forEach(function (t, i) { if (t.key === pref) i0 = i; });
      showTab(i0);
      if (l && l.lit) addRef('lit', 'Lit.', '<span class="small">Earliest LSJ citation:</span> ' + esc(l.lit));
    });
    bucket('forms', lid).then(function (fd) {
      if (!alive() || !fd) return;
      var tbl = paradigm(fd, mi, form);
      $('#pdBox').innerHTML = tbl || '<div class="small">Indeclinable.</div>';
      if (!tbl) $('#formsRow').classList.add('flat');
      var tot = 0; Object.keys(fd.b).forEach(function (b) { tot += fd.b[b]; });
      $('#freqChip').textContent = tot + '× LXX'; $('#sfreq').textContent = tot;
      $('#freqChip').title = nChap + '× in this chapter, ' + (fd.b[cur.book] || 0) + '× in this book — tap to list';
    });
    bucket('etym', lid).then(function (e) {
      if (!alive() || !e) return;
      var r = $('#etyRow'); r.hidden = false;
      r.innerHTML = '<span class="rl">Etym.</span> <span class="ety">' + esc(e.t) + (e.d && e.d.length ? ' <span class="sub">→ ' + e.d.map(esc).join(', ') + '</span>' : '') + '</span><div class="src">Wiktionary · CC BY-SA 4.0</div>';
    });
    function addRef(n, label, line) {
      var c = document.createElement('button'); c.className = 'rc'; c.dataset.n = n; c.dataset.line = line; c.textContent = label;
      $('#refChips').appendChild(c);
    }
    var nk = cur.book + '|' + cur.ch + '|' + ref;
    (NOTES ? Promise.resolve(NOTES) : onceGet('data/notes.json')).then(function (n) {
      if (!alive()) return; NOTES = n || {};
      (NOTES[nk] || []).forEach(function (x, i) {
        addRef('nt' + i, 'NT ' + x.nt, '<b>' + (x.kind === 'allusion' ? 'Echoed' : 'Quoted') + ': ' + esc(x.nt) + '</b>' + (x.short ? ' — ' + esc(x.short) : '') + '<div class="ntg" lang="grc">' + esc(x.ntg) + '</div>');
      });
    });
    Promise.all([onceGet('data/vul/' + cur.book + '/' + cur.ch + '.json'), onceGet('data/latw/' + cur.book + '/' + cur.ch + '.json'), LATLEX ? LATLEX : onceGet('data/latlex.json'), VULW ? VULW : onceGet('data/vulg_words.json')]).then(function (r) {
      if (!alive()) return;
      LATLEX = r[2] || {}; VULW = r[3] || {};
      var vd = r[0] && r[0][ref], al = r[1] && r[1][ref], e = al ? al[wi] : undefined, row = $('#latRow');
      if (!vd) return;
      row.hidden = false;
      var h = '<span class="rl">Latin</span> ';
      if (e && e.length) {
        var lx = LATLEX[e[1]] || null;
        h += '<span class="lw" lang="la" title="' + (e[3] < 0 ? 'Approximate: matched by word order between confident neighbours' : 'Word-alignment confidence ' + e[3] + '%') + '">' + (e[3] < 0 ? '≈ ' : '') + esc(e[0]) + '</span>' + (e[3] < 0 ? ' <span class="sub">(approx., by word order)</span>' : '') +
          (e[2] || e[1] ? ' <span class="lp">' + esc(e[2]) + (e[1] && e[1] !== e[0] ? (e[2] ? ', ' : '') + 'from <i lang="la">' + esc(e[1]) + '</i>' : '') + '</span>' : '') +
          (lx && lx[1] ? '<div class="lg">' + esc(lx[1]) + '</div>' : '') + '<div class="src">Latin parse &amp; meaning: Wiktionary · CC BY-SA 4.0</div>';
      } else if (e === 0) {
        h += '<span class="lnone">no Latin word (Latin has no article)</span>';
      } else {
        h += '<span class="lnone">no confident match</span>';
      }
      var words = vd[0].split(/([A-Za-zÆæŒœëÉéÈè]+)/), n = -1;
      var vt = words.map(function (s, k) { if (k % 2) { n++; return e && e.length && n === e[4] ? '<b>' + esc(s) + '</b>' : esc(s); } return esc(s); }).join('');
      h += '<details class="dr"><summary>Show Vulgate verse</summary><div class="lv" lang="la">' + vt + ' <span class="sub">' + esc(vd[2].replace(/^(\S+)/, function (b) { return VBOOK[b] || b; })) + '</span></div>' +
        (vd[1] ? '<div class="sub">Douay-Rheims: ' + esc(vd[1]) + '</div>' : '') + '</details>';
      row.innerHTML = h;
    });
  }
  var VBOOK = { GEN: 'Gen', EXO: 'Exod', LEV: 'Lev', NUM: 'Num', DEU: 'Deut', JOS: 'Josh', JDG: 'Judg', RUT: 'Ruth', '1SA': '1 Kgs (=1 Sam)', '2SA': '2 Kgs (=2 Sam)', '1KI': '3 Kgs (=1 Kings)', '2KI': '4 Kgs (=2 Kings)', '1CH': '1 Par (=1 Chr)', '2CH': '2 Par (=2 Chr)', EZR: '1 Esdras (=Ezra)', NEH: '2 Esdras (=Neh)', EST: 'Esther', JDT: 'Judith', TOB: 'Tobias', '1MA': '1 Macc', '2MA': '2 Macc', PSA: 'Ps', PRO: 'Prov', ECC: 'Eccle', SOL: 'Cant', JOB: 'Job', WIS: 'Wis', SIR: 'Ecclus', HOS: 'Osee', MIC: 'Mich', AMO: 'Amos', JOE: 'Joel', JON: 'Jonas', OBA: 'Abdias', NAH: 'Nahum', HAB: 'Hab', ZEP: 'Soph', HAG: 'Agg', ZEC: 'Zach', MAL: 'Mal', ISA: 'Isa', JER: 'Jer', BAR: 'Baruch', LAM: 'Lam', EZE: 'Ezech', DAN: 'Dan' };
  function enNote(s) {
    if (s.s === 'm') return 'Brenton numbers this verse ' + s.br + '. The English shown has been matched to this Greek verse by comparing Brenton’s own Greek text with the Greek shown (similarity ' + Math.round(s.q * 100) + '%).';
    if (s.s === 'h') return 'No English is shown: Brenton’s verse with this number does not match this Greek, and no reliable match was found.';
    if (s.s === 'j') return 'Brenton’s English for this verse is included with verse ' + s['with'] + ' (the two editions divide the verses differently).';
    if (s.s === 'd') return 'Brenton translated slightly different Greek here: his Greek has different wording or a different verse division (word overlap with the Greek shown: ' + Math.round(s.q * 100) + '%), so the English may include or omit words.';
    return '';
  }
  function setExp(on) {
    var m = $('#more'), b = $('#moreBtn'); if (!m) return;
    m.hidden = !on; b.textContent = on ? 'Less ▴' : 'More ▾'; b.setAttribute('aria-expanded', on);
    $('#panel').classList.toggle('exp', on);
  }
  (function () { /* drag the phone sheet's grip: up = expand, down = collapse / close */
    var g = document.querySelector('.panel-grip'), y0 = null; if (!g) return;
    g.addEventListener('click', function () { var on = $('#more') && $('#more').hidden; setExp(on); store('lxx-exp', on ? '1' : '0'); });
    g.addEventListener('touchstart', function (e) { y0 = e.touches[0].clientY; }, { passive: true });
    g.addEventListener('touchend', function (e) {
      if (y0 == null) return; var dy = e.changedTouches[0].clientY - y0; y0 = null;
      if (dy < -30) { setExp(true); store('lxx-exp', '1'); }
      else if (dy > 30) { if ($('#more') && !$('#more').hidden) { setExp(false); store('lxx-exp', '0'); } else closePanel(); }
    });
  })();
  function closePanel() {
    $('#panel').hidden = true; document.body.classList.remove('pop'); if ($('#books').hidden) $('#scrim').hidden = true;
    document.querySelectorAll('.w.sel').forEach(function (x) { x.classList.remove('sel'); }); highlight(null);
  }

  function search(q, lex) {
    cur = { book: null, ch: null }; $('#locBtn').textContent = 'Search'; document.title = 'Search — Septuagint Study Bible';
    $('#main').innerHTML = '<div class="search"><h1>Search the vocabulary</h1><input id="q" type="search" autocomplete="off" placeholder="Greek lemma (accents optional), transliteration, or English" value="' + esc(q) + '"><p class="small">Examples: λογος · logos · shepherd · ποιμαινω</p><div id="results"></div></div>';
    Promise.all([LEX ? LEX : get('data/lexicon.json'), COUNTS ? COUNTS : get('data/counts.json')]).then(function (r) {
      LEX = r[0]; COUNTS = r[1];
      var keys = Object.keys(LEX), idx = keys.map(function (k) { return [k, norm(LEX[k][0]), norm(LEX[k][3]), LEX[k][1].toLowerCase()]; });
      var inp = $('#q');
      function run() {
        var s = norm(inp.value.trim()); if (!s) { $('#results').innerHTML = ''; return; }
        var greek = /[\u0370-\u03ff\u1f00-\u1fff]/.test(s), hits = [];
        idx.forEach(function (x) {
          var sc = greek ? (x[1] === s ? 3 : x[1].indexOf(s) === 0 ? 2 : x[1].indexOf(s) > 0 ? 1 : 0)
            : (x[2] === s ? 3 : x[2].indexOf(s) === 0 ? 2 : new RegExp('\\b' + s.replace(/[^a-z ]/g, '')).test(x[3]) ? 1 : 0);
          if (sc) hits.push([sc, COUNTS[x[0]] || 0, x[0]]);
        });
        hits.sort(function (a, b) { return b[0] - a[0] || b[1] - a[1]; });
        $('#results').innerHTML = hits.slice(0, 80).map(function (hh) { var L = LEX[hh[2]]; return '<a class="res" href="#/search?lex=' + hh[2] + '"><b>' + esc(L[0]) + '</b> <span class="small">' + esc(L[3]) + ' · ' + esc(L[2]) + ' · ' + hh[1] + '×</span><br>' + esc(L[1]) + '</a>'; }).join('') || '<p class="small">No matches.</p>';
      }
      inp.oninput = function () { history.replaceState(null, '', '#/search?q=' + encodeURIComponent(inp.value)); run(); };
      if (lex) showOcc(lex); else { run(); inp.focus(); }
    }).catch(fail);
  }
  function showOcc(lex) {
    var L = LEX[lex]; if (!L) return;
    get('data/occ/' + Math.floor(lex / 100) + '.json').then(function (d) {
      var o = d[lex] || [0], refs = o.slice(1), by = {};
      refs.forEach(function (r) { var p = r.split('|'); (by[p[0]] = by[p[0]] || []).push(p); });
      var h = '<h1>' + esc(L[0]) + '<small>' + esc(L[3]) + ' · ' + esc(L[2]) + ' — “' + esc(L[1]) + '” — ' + o[0] + ' occurrences in ' + refs.length + ' verses</small></h1>' +
        '<div class="links" style="margin-bottom:1rem"><a target="_blank" rel="noopener" href="https://logeion.uchicago.edu/' + encodeURIComponent(L[0]) + '">Logeion</a><a target="_blank" rel="noopener" href="https://en.wiktionary.org/wiki/' + encodeURIComponent(L[0]) + '#Ancient_Greek">Wiktionary</a></div>';
      Object.keys(by).forEach(function (b) {
        h += '<div class="grp">' + esc(BYID[b] ? BYID[b].name : b) + ' (' + by[b].length + ')</div><div class="refs">' +
          by[b].map(function (p) { return '<a href="#/' + p[0] + '/' + p[1] + '/' + p[2] + '?lex=' + lex + '">' + esc(p[1] + ':' + p[2]) + '</a>'; }).join('') + '</div>';
      });
      $('#results').innerHTML = h;
    }).catch(fail);
  }

  function about() {
    cur = { book: null, ch: null }; $('#locBtn').textContent = 'About';
    fetch('about.html').then(function (r) { return r.text(); }).then(function (t) {
      var m = t.match(/<article[\s\S]*<\/article>/); $('#main').innerHTML = m ? m[0] : t; window.scrollTo(0, 0);
    });
  }
  init();
})();
