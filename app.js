/* Septuagint Reader — vanilla JS, no dependencies. */
(function () {
  'use strict';
  var $ = function (s) { return document.querySelector(s); };
  var BOOKS = null, BYID = {}, LEX = null, MORPH = null, COUNTS = null, cache = {}, occCache = {};
  var cur = { book: null, ch: null }, selLex = null;
  var GROUPS = [['Law (Pentateuch)', 'Gen'], ['Historical books', 'JoshB'], ['Poetry & Wisdom', 'Ps'], ['Prophets', 'Hos']];

  function get(url) {
    if (cache[url]) return cache[url];
    return (cache[url] = fetch(url).then(function (r) { if (!r.ok) throw new Error(r.status + ' ' + url); return r.json(); }));
  }
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function norm(s) { return s.normalize('NFD').replace(/[\u0300-\u036f\u1fbd\u1fbf\u1ffe\u02bc\u2019]/g, '').toLowerCase().replace(/ς/g, 'σ'); }
  function store(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function load(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }

  function init() {
    Promise.all([get('data/books.json'), get('data/morph.json')]).then(function (r) {
      BOOKS = r[0]; MORPH = r[1];
      BOOKS.forEach(function (b, i) { b.i = i; BYID[b.id] = b; });
      buildBookList();
      window.addEventListener('hashchange', route);
      route();
      get('data/lexicon.json').then(function (l) { LEX = l; }); get('data/counts.json').then(function (c) { COUNTS = c; });
    }).catch(fail);
    $('#menuBtn').onclick = function () { toggleDrawer(true); };
    $('#locBtn').onclick = function () { toggleDrawer(true, true); };
    document.querySelectorAll('[data-close]').forEach(function (b) { b.onclick = function () { toggleDrawer(false); }; });
    $('#scrim').onclick = function () { toggleDrawer(false); closePanel(); };
    $('#panelClose').onclick = closePanel;
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
    if (load('lxx-en') === '0') document.body.classList.add('noen');
    $('#enBtn').classList.toggle('on', !document.body.classList.contains('noen'));
    $('#enBtn').onclick = function () {
      var off = document.body.classList.toggle('noen'); store('lxx-en', off ? '0' : '1'); this.classList.toggle('on', !off);
    };
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
    BOOKS.forEach(function (b) {
      if (g < GROUPS.length && GROUPS[g][1] === b.id) { h += '<div class="grp">' + GROUPS[g][0] + '</div>'; g++; }
      h += '<button class="bk" data-b="' + b.id + '">' + esc(b.name) + '</button><div class="chs" data-for="' + b.id + '" hidden></div>';
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
    if (i < 0) { b = BOOKS[b.i - 1]; if (!b) return; i = b.chapters.length - 1; }
    else if (i >= b.chapters.length) { b = BOOKS[b.i + 1]; if (!b) return; i = 0; }
    location.hash = '#/' + b.id + '/' + b.chapters[i];
  }
  function chName(b, ch) { return ch === 'Prolog' ? 'Prologue' : ch; }

  function chapter(b, ch, verse, lex) {
    cur = { book: b.id, ch: ch }; store('lxx-last', b.id + '/' + ch);
    $('#locBtn').textContent = b.name.replace(/ \(.*\)/, '') + ' ' + chName(b, ch);
    document.title = b.name + ' ' + chName(b, ch) + ' — Septuagint Reader';
    $('#main').innerHTML = '<p class="loading">Loading…</p>';
    get('data/' + b.id + '/' + ch + '.json').then(function (vs) {
      var h = '<h1>' + esc(b.name) + ' ' + esc(chName(b, ch)) + (b.id === 'Ps' ? '<small>Greek (LXX) psalm numbering — e.g. LXX Ps 22 = Hebrew/English Ps 23.</small>' : '') + '</h1>';
      vs.forEach(function (v) {
        h += '<p class="verse" id="v' + esc(v[0]) + '"><span class="vn">' + esc(v[0]) + '</span>';
        v[1].forEach(function (t, i) { h += '<span class="w" data-l="' + t[1] + '" data-m="' + t[2] + '">' + esc(t[0]) + '</span> '; });
        if (v[2]) h += '<span class="en">' + esc(v[2]) + '</span>';
        h += '</p>';
      });
      var bi = b.chapters.map(String).indexOf(ch);
      var prev = bi > 0 ? [b, b.chapters[bi - 1]] : (BOOKS[b.i - 1] ? [BOOKS[b.i - 1], BOOKS[b.i - 1].chapters.slice(-1)[0]] : null);
      var next = bi < b.chapters.length - 1 ? [b, b.chapters[bi + 1]] : (BOOKS[b.i + 1] ? [BOOKS[b.i + 1], BOOKS[b.i + 1].chapters[0]] : null);
      h += '<nav class="chnav">' + (prev ? '<a href="#/' + prev[0].id + '/' + prev[1] + '">‹ ' + esc(prev[0].name.replace(/ \(.*\)/, '')) + ' ' + prev[1] + '</a>' : '<span></span>') +
        (next ? '<a href="#/' + next[0].id + '/' + next[1] + '">' + esc(next[0].name.replace(/ \(.*\)/, '')) + ' ' + next[1] + ' ›</a>' : '') + '</nav>';
      if (!b.en) h += '<p class="small">No Brenton English is available for this book.</p>';
      h += '<p class="small">Greek: Rahlfs 1935 via CCAT/eliranwong (CC BY-NC-SA 4.0). English: Brenton 1851 (public domain), matched by verse number — may be offset in places. <a href="#/about">Sources</a></p>';
      var m = $('#main'); m.innerHTML = h; m.onclick = onWord;
      if (verse) { var el = document.getElementById('v' + verse); if (el) { el.scrollIntoView({ block: 'center' }); el.classList.add('flash'); } }
      else window.scrollTo(0, 0);
      if (lex) highlight(lex);
    }).catch(fail);
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
    (LEX ? Promise.resolve(LEX) : get('data/lexicon.json').then(function (l) { return (LEX = l); })).then(function () { showWord(w.textContent, w.dataset.l, +w.dataset.m, ref); });
  }
  function showWord(form, lid, mi, ref) {
    var L = LEX[lid] || ['', '', '', '', '', ''], M = MORPH[mi] || ['', ''];
    var lemma = L[0], n = document.querySelectorAll('.w[data-l="' + lid + '"]').length;
    var parse = M[1].replace(/^([^:]+): /, '<span class="small">$1</span><br>');
    var enc = encodeURIComponent;
    var lsj = L[4] ? 'https://www.perseus.tufts.edu/hopper/text?doc=Perseus:text:1999.04.0057:entry=' + enc(L[4]) : 'https://www.perseus.tufts.edu/hopper/searchresults?q=' + enc(lemma);
    var h = '<div class="form">' + esc(form) + '</div>' +
      '<div class="lemma">from <b>' + esc(lemma) + '</b> <span class="tr">' + esc(L[3]) + (L[2] ? ' · ' + esc(L[2].replace(/^Verbs$/, 'Verb')) : '') + '</span></div>' +
      '<div class="lbl">Parsing</div><div class="parse">' + parse + '</div><div class="code">' + esc(M[0]) + '</div>' +
      '<div class="lbl">Gloss</div><div class="gloss">' + (L[1] ? esc(L[1]) : '<i>No gloss in source data — see the lexicons below.</i>') + '</div>' +
      '<div class="lbl">Full entry &amp; inflection tables</div><div class="links">' +
      '<a target="_blank" rel="noopener" href="https://logeion.uchicago.edu/' + enc(lemma) + '">Logeion</a>' +
      '<a target="_blank" rel="noopener" href="' + lsj + '">LSJ (Perseus)</a>' +
      '<a target="_blank" rel="noopener" href="https://en.wiktionary.org/wiki/' + enc(lemma) + '#Ancient_Greek">Wiktionary (forms table)</a>' +
      '<a target="_blank" rel="noopener" href="https://www.perseus.tufts.edu/hopper/morph?la=greek&l=' + enc(form) + '">Perseus parse of this form</a></div>' +
      '<div class="lbl">Occurrences</div><div class="small">' + n + '× in this chapter (highlighted)' + (COUNTS ? ' · ' + (COUNTS[lid] || 0) + '× in the whole LXX' : '') +
      ' · <a href="#/search?lex=' + lid + '">list every verse</a>' + (L[5] ? ' · Strong’s ' + esc(L[5]) : '') + '</div>';
    $('#panelBody').innerHTML = h;
    $('#panel').hidden = false;
    if (!COUNTS) get('data/counts.json').then(function (c) { COUNTS = c; });
  }
  function closePanel() {
    $('#panel').hidden = true; if ($('#books').hidden) $('#scrim').hidden = true;
    document.querySelectorAll('.w.sel').forEach(function (x) { x.classList.remove('sel'); }); highlight(null);
  }

  function search(q, lex) {
    cur = { book: null, ch: null }; $('#locBtn').textContent = 'Search'; document.title = 'Search — Septuagint Reader';
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
