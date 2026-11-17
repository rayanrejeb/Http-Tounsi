/* HTTP Tounsi — front. Tous les échanges passent par transport() : un vrai fetch() vers Django. */
(() => {
const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
const sleep = ms => new Promise(r => setTimeout(r, ms));
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const pad = n => String(n).padStart(2, '0');

const FAMILIES = {
  '1xx': { slogan: 'Stanna chwaya', desc: 'Information : la suite arrive.' },
  '2xx': { slogan: 'Behi', desc: "Tout s'est bien passé." },
  '3xx': { slogan: 'Emchi l blasa okhra', desc: 'Va voir ailleurs : redirection.' },
  '4xx': { slogan: 'Ghaltetek enti', desc: "C'est la faute du client." },
  '5xx': { slogan: 'Ghaltet el serveur', desc: "C'est la faute du serveur." },
};
const famOf = n => (n >= 100 && n < 600 ? `${String(n)[0]}xx` : '5xx');
const CONFIG = JSON.parse($('#config').textContent || '{}');
const SECTIONS = CONFIG.sections || {};
const TOKENS = CONFIG.tokens || {};  // vide si la page n'est pas ouverte depuis 127.0.0.1
const HINT_HEADERS = ['Location', 'Retry-After', 'Allow', 'WWW-Authenticate'];
const TRIGGERS = CONFIG.triggers || {};  // code -> requête de démo qui le déclenche (codes/demo.py)
const state = { view: 'tounsi', catalog: new Map(), slide: 1, slideTitle: '', onSlide: true, up: null,
  typing: 0, busy: false, galleryReq: null };

const getH = (h, name) => { const k = Object.keys(h || {}).find(k => k.toLowerCase() === name.toLowerCase()); return k ? h[k] : null; };

/* ---------- transport : le seul point de contact avec le serveur ---------- */
async function transport({ method, path, headers = {}, body }) {
  // no-store : le navigateur n'intercale pas son cache, on voit les vrais 200 / 304 du serveur.
  const r = await fetch(path, { method, headers, body: body || undefined, cache: 'no-store' });
  return {
    status: r.status, statusText: r.statusText, headers: Object.fromEntries(r.headers),
    body: await r.text(), redirected: r.redirected, url: r.url,
  };
}

/* ---------- requête ---------- */
function readBar() {
  const method = $('#method').value;
  let path = $('#path').value.trim() || '/';
  if (!path.startsWith('/')) path = '/' + path;
  const headers = {};
  for (const line of $('#extra-headers').value.split('\n')) {
    const i = line.indexOf(':');
    if (i > 0) headers[line.slice(0, i).trim()] = line.slice(i + 1).trim();
  }
  const tok = $('#token').value.trim().replace(/^Token\s+/i, '');
  if (tok) headers.Authorization = `Token ${tok}`;
  const body = ['POST', 'PUT', 'PATCH'].includes(method) ? $('#body').value.trim() : '';
  if (body) {
    const xml = body.startsWith('<');
    headers['Content-Type'] ??= xml ? 'text/xml; charset=utf-8' : 'application/json';
    if (xml && path.startsWith('/soap/')) headers.SOAPAction ??= '"urn:http-tounsi:codes#GetCode"';
  }
  return { method, path, headers, body };
}

async function send(req = readBar()) {
  const loadTimer = setTimeout(() => showLoading(req), 150);
  state.busy = true;
  $('#send').classList.add('busy');
  const t0 = performance.now();
  let res;
  try { res = await transport(req); }
  catch (e) { res = { status: 0, headers: {}, body: String(e?.message || e) }; }
  res.ms = Math.round(performance.now() - t0);
  res.size = new Blob([res.body || '']).size;
  clearTimeout(loadTimer);
  state.busy = false;
  $('#loading').hidden = true;
  $('#send').classList.remove('busy');
  render(req, res);
}

function showLoading(req) {
  $('#loading-text').textContent = req.path.includes('504') ? 'Nestannaw fil louage… yetla3 wa9t ?'
    : ['Nestannaw fil serveur…', 'El garçon jey…', 'Chwaya sabr…'][Math.floor(Math.random() * 3)];
  $('#loading').hidden = false;
}

/* ---------- barre : frappe animée ---------- */
function setMethod(m) {
  const sel = $('#method');
  sel.value = m;
  sel.className = `method m-${m}`;
}

async function typePath(path) {
  const id = ++state.typing;
  const input = $('#path');
  input.value = '';
  input.classList.add('typing');
  for (const ch of path) {
    if (id !== state.typing) return false;
    input.value += ch;
    await sleep(16 + Math.random() * 26);
  }
  input.classList.remove('typing');
  await sleep(140);
  return id === state.typing;
}

/* "MÉTHODE /chemin/ {body optionnel}" -> la barre se remplit puis envoie */
async function go(line, typed = true) {
  const m = /^(\w+)\s+(\S+)\s*(.*)$/.exec(line.trim());
  if (!m) return;
  const [, method, path, body] = m;
  setMethod(method.toUpperCase());
  if (body) {
    $('#body').value = body.startsWith('<') ? body.replace(/></g, '>\n<') : prettyJson(body);
    toggleBody(true);
  } else {
    // Requête suivante sans body (slide, galerie, code…) : le panneau se referme et se vide,
    // pour qu'aucun body ni If-None-Match caché ne parte avec les requêtes d'après.
    $('#body').value = $('#extra-headers').value = '';
    toggleBody(false);
  }
  updateDot();
  if (typed) { if (!(await typePath(path))) return; }
  else { ++state.typing; $('#path').value = path; }
  const btn = $('#send');
  btn.classList.add('pressed');
  setTimeout(() => btn.classList.remove('pressed'), 180);
  send();
}

function nav(delta) {
  // En détour (code, galerie, erreur), ← ramène à la slide d'où l'on vient au lieu de reculer d'une slide.
  if (!state.onSlide && delta < 0) delta = 0;
  state.slide = Math.max(1, state.slide + delta);
  setView('tounsi');
  go(`GET /api/slides/${state.slide}/`);
}

function toggleBody(open = $('#body-panel').hidden) {
  $('#body-panel').hidden = !open;
  $('#toggle-body').setAttribute('aria-expanded', open);
  $('#toggle-body .caret').textContent = open ? '▾' : '▸';
}

function prettyJson(t) { try { return JSON.stringify(JSON.parse(t), null, 2); } catch { return t; } }

function setToken(who) {
  const t = TOKENS[who];
  if (!t) { toast(`Pas de token « ${who} » : lance <code>setup_demo</code> et ouvre la page via 127.0.0.1`); return; }
  const input = $('#token');
  input.value = input.value === t ? '' : t;  // même raccourci une 2e fois = vider
  toast(input.value ? `🔑 Token <b>${who}</b> dans la barre` : '🔑 Token retiré', 1800);
  input.classList.remove('flash'); void input.offsetWidth; input.classList.add('flash');
}

function toast(html, ms = 6000) {
  const el = document.createElement('div');
  el.className = 'toast';
  el.innerHTML = html;
  $('#toasts').append(el);
  setTimeout(() => el.remove(), ms);
}

/* ---------- rendu ---------- */
function setView(v) {
  state.view = v;
  $('#tounsi').hidden = v !== 'tounsi';
  $('#raw').hidden = v !== 'raw';
  $$('.switch [data-view]').forEach(b => b.setAttribute('aria-selected', String(b.dataset.view === v)));
}

function render(req, res) {
  const ct = getH(res.headers, 'Content-Type') || '';
  let data = null;
  if (/json/.test(ct)) { try { data = JSON.parse(res.body); } catch { /* body invalide : vue brute */ } }
  renderMeta(req, res);
  renderRaw(req, res, ct);
  renderTounsi(req, res, data, ct);
  // Un XML réussi se lit en vue brute ; une erreur (SOAP Fault 500…) garde sa carte.
  if (/xml/.test(ct) && res.status < 300) setView('raw');
  window.scrollTo({ top: 0 });
}

function statusInfo(res) {
  const s = res.status;
  if (!s) return {
    code: 'ERR', famille: '5xx', nom_officiel: 'Network Error', titre_derja: 'El connexion ta7et',
    situation: 'Le serveur ne répond pas du tout : il est éteint, ou le Wi-Fi a lâché.', explication_technique: res.body,
  };
  const fam = famOf(s);
  return state.catalog.get(s) || {
    code: s, famille: fam, nom_officiel: res.statusText || '', titre_derja: FAMILIES[fam]?.slogan || '…',
    situation: FAMILIES[fam]?.desc || '', explication_technique: '',
  };
}

function renderMeta(req, res) {
  const info = statusInfo(res);
  $('#meta').hidden = false;
  const pill = $('#m-status');
  pill.className = `status-pill fam-${info.famille}`;
  pill.textContent = `${res.status || 'ERR'} ${info.nom_officiel}${res.redirected ? ' ↪' : ''}`;
  $('#m-time').innerHTML = `<b>${res.ms}</b> ms`;
  $('#m-size').innerHTML = `<b>${res.size}</b> octets`;
  const isApi = /^\/api\//.test(req.path) && res.status;
  $('#toggle-format').hidden = !isApi;
  $('#fmt-label').textContent = /[?&]format=xml/.test(req.path) ? 'XML' : 'JSON';
  const etag = getH(res.headers, 'ETag');
  $('#replay-etag').hidden = !(etag && req.method === 'GET' && res.status === 200 && req.path.startsWith('/api/codes/'));
  $('#replay-etag').dataset.etag = etag || '';
}

const finalPath = res => { const u = new URL(res.url); return u.pathname + u.search; };

function renderTounsi(req, res, data, ct) {
  const p = req.path.split('?')[0];
  const s = res.status;
  const list = Array.isArray(data) ? data : Array.isArray(data?.results) ? data.results : null;
  let html;
  state.galleryReq = null;
  if (res.redirected) {
    // fetch() suit la redirection tout seul et ne laisse jamais lire le 301 intermédiaire.
    html = codeCard(statusInfo({ status: 301 }), `<p class="note">Le navigateur a suivi la redirection tout seul :
      <code>${esc(req.path)}</code> ➜ <code>${esc(finalPath(res))}</code> (${s}).
      Le 301 lui-même se voit dans l'onglet Réseau (F12) ou avec <code>check_demo</code>.</p>
      <div class="hints"><span class="hint"><button class="mini-go" data-go="GET ${esc(finalPath(res))}">voir ${esc(finalPath(res))} ➤</button></span></div>`);
  }
  const isEnd = req.method === 'DELETE' && p === '/api/presentation/' && s === 204;
  state.onSlide = !res.redirected && /^\/api\/slides\/\d+\/$/.test(p) && s === 200 && !!data;
  let fam = null;  // famille du code affiché, pour la flèche ↑
  if (isEnd) html = endScreen();
  else if (state.onSlide) html = slideView(data);
  else if (s === 200 && list && list.every(c => c.code !== undefined)) html = gallery(list, req);
  else if (s === 200 && data?.code !== undefined && data?.titre_derja) {
    fam = data.famille;
    html = codeCard(data, `<p class="note">Fiche du code <b>${esc(data.code)}</b>, renvoyée avec <b>200 OK</b> par <code>${esc(req.method)} ${esc(req.path)}</code></p>`);
  } else html = codeCard(statusInfo(res), extras(req, res, data, ct));
  // Détour hors des slides : flèches de retour (↑ code -> sa famille -> la slide ; ← la slide).
  state.up = state.onSlide || isEnd ? null : fam ? `GET /api/codes/?famille=${fam}` : `GET /api/slides/${state.slide}/`;
  $('#tounsi').innerHTML = (state.up ? crumbs(fam, fam && TRIGGERS[data.code]) : '') + html;
}

/* indices utiles sous la carte d'un statut : message du serveur, en-têtes parlants, body */
function extras(req, res, data, ct) {
  let out = '';
  const fault = /xml/.test(ct) && new DOMParser().parseFromString(res.body, 'text/xml').querySelector('faultstring')?.textContent;
  if (res.status === 201 && data?.code) {
    out += `<p class="note">Nouveau code créé : <b>${esc(data.code)}</b> — « ${esc(data.titre_derja)} »${data.propose_par ? ` par ${esc(data.propose_par)}` : ''}</p>`;
  } else if (fault) {
    out += `<p class="note"><b>soap:Fault</b> en HTTP ${res.status} : « ${esc(fault)} ». En REST, ce serait un simple 404.</p>`;
  } else if (data?.detail) {
    out += `<p class="note">Le serveur dit : « ${esc(data.detail)} »</p>`;
  } else if (data && typeof data === 'object') {
    out += `<pre class="code mini">${hlJson(JSON.stringify(data))}</pre>`;
  }
  const hints = [...HINT_HEADERS, ...(res.status === 304 ? ['ETag'] : [])].map(h => [h, getH(res.headers, h)]).filter(([, v]) => v);
  if (hints.length) out += `<div class="hints">${hints.map(([k, v]) => {
    const extra = k === 'Retry-After' && Number(v) >= 3600 ? ` <i>(${Math.round(v / 3600)} h, erja3 ghodwa)</i>` : '';
    const follow = k === 'Location' ? ` <button class="mini-go" data-go="GET ${esc(v)}">suivre ➤</button>` : '';
    return `<span class="hint"><code>${esc(k)}: ${esc(v)}</code>${extra}${follow}</span>`;
  }).join('')}</div>`;
  return out;
}

function codeMedia(c, compact = false) {
  if (c.image_url) return `<img src="${esc(c.image_url)}" alt="${esc(c.titre_derja)}">`;
  return `<div class="ph">
    <span class="ph-code">${esc(c.code)}</span>
    ${compact ? '' : `<span class="ph-title">« ${esc(c.titre_derja)} »</span>`}
    <span class="ph-file">static/img/codes/${esc(c.code)}.webp</span>
  </div>`;
}

function sectionMedia(url, name, label = '') {
  if (url) return `<img src="${esc(url)}" alt="">`;
  return `<div class="ph ph-section">
    ${label ? `<span class="ph-code">${esc(label)}</span>` : '<span class="ph-star" aria-hidden="true"></span>'}
    <span class="ph-file">static/img/sections/${esc(name)}.webp</span>
  </div>`;
}

function codeCard(c, extra = '') {
  const fam = c.famille || famOf(c.code);
  return `<article class="card-tounsi fam-${fam}">
    <figure class="media">${codeMedia(c)}</figure>
    <div class="info">
      <span class="fam-chip">${fam} · ${esc(FAMILIES[fam]?.slogan)}</span>
      <div class="code-big">${esc(c.code)}</div>
      <div class="official">${esc(c.nom_officiel)}</div>
      <h1 class="derja">« ${esc(c.titre_derja)} »</h1>
      ${c.situation ? `<p class="situation">${esc(c.situation)}</p>` : ''}
      ${c.explication_technique ? `<p class="tech"><strong>Côté technique</strong>${esc(c.explication_technique)}</p>` : ''}
      ${c.propose_par ? `<p class="by">Proposé par <b>${esc(c.propose_par)}</b></p>` : ''}
      ${extra}
    </div>
  </article>`;
}

const famParam = req => new URLSearchParams(req.path.split('?')[1] || '').get('famille') || '';

function gallery(items, req) {
  state.galleryReq = req;
  const f = famParam(req);
  const chips = ['', '2xx', '3xx', '4xx', '5xx'].map(x =>
    `<button class="filter fam-${x || 'all'}${x === f ? ' on' : ''}" data-go="GET /api/codes/${x ? `?famille=${x}` : ''}" data-fast>${x || 'Tous'}</button>`).join('');
  const banner = FAMILIES[f] ? `<div class="fam-banner fam-${f}">
      <div class="fb-media">${sectionMedia(SECTIONS[f], f, f)}</div>
      <div><span class="fam-chip">${f}</span><h2>« ${FAMILIES[f].slogan} »</h2><p>${FAMILIES[f].desc}</p></div>
    </div>` : '';
  const cards = items.map(c => `
    <button class="g-card fam-${esc(c.famille)}${c.propose_par ? ' proposed' : ''}" data-go="GET /api/codes/${esc(c.code)}/" data-fast>
      <div class="g-media">${codeMedia(c, true)}</div>
      <div class="g-body">
        <span class="g-code">${esc(c.code)}</span><span class="g-off">${esc(c.nom_officiel)}</span>
        <span class="g-derja">« ${esc(c.titre_derja)} »</span>
        ${c.propose_par ? `<span class="g-by">par ${esc(c.propose_par)}</span>` : ''}
      </div>
    </button>`).join('');
  return `<section class="gallery">
    <header class="g-head"><h1>Galerie <small>${items.length} code${items.length > 1 ? 's' : ''}</small></h1><div class="filters">${chips}</div></header>
    ${banner}
    <div class="grid">${cards || '<p class="empty">Walou. Aucun code dans cette famille.</p>'}</div>
  </section>`;
}

function crumbs(fam, trigger = null) {
  const back = `<button class="crumb" data-go="GET /api/slides/${state.slide}/"><kbd>←</kbd>${fam ? '' : '<kbd>↑</kbd>'}
    Slide ${state.slide}${state.slideTitle ? ` : ${esc(state.slideTitle)}` : ''}</button>`;
  const up = fam ? `<button class="crumb fam-${esc(fam)}" data-go="GET /api/codes/?famille=${esc(fam)}"><kbd>↑</kbd>
    Famille ${esc(fam)} : « ${esc(FAMILIES[fam]?.slogan)} »</button>` : '';
  // Fiche d'un code : la vraie requête qui le déclenche (codes/demo.py), à côté des flèches.
  const t = trigger ? `<span class="trigger fam-${esc(fam)}"><b>▶ Déclencher</b>${reqChip(trigger.line)}<small>${esc(trigger.hint)}</small></span>` : '';
  return `<nav class="crumbs" aria-label="Retour">${back}${up}${t}</nav>`;
}

function slideView(s) {
  state.slide = s.numero;
  state.slideTitle = s.titre;
  $('#slide-pos').textContent = s.total ? `${s.numero}/${s.total}` : s.numero;
  const media = s.image === 'familles' ? familyTiles()
    : s.image ? `<figure class="slide-media">${sectionMedia(s.image_url, s.image)}</figure>` : '';
  const kind = ({ hero: ' slide-hero', familles: ' slide-fams' }[s.image] || (media ? ' has-media' : ''))
    + (s.image_url ? ' has-img' : '');
  return `<section class="slide${kind}">
    <div class="slide-text">
      <div class="slide-num">${pad(s.numero)}${s.total ? ` <span>/ ${pad(s.total)}</span>` : ''}</div>
      <h1>${esc(s.titre)}</h1>
      <div class="slide-content">${richText(s.contenu)}</div>
    </div>
    ${media}
  </section>`;
}

function familyTiles() {
  return `<div class="fam-tiles">${['2xx', '3xx', '4xx', '5xx'].map(f => `
    <button class="fam-tile fam-${f}" data-go="GET /api/codes/?famille=${f}">
      <div class="ft-media">${sectionMedia(SECTIONS[f], f, f)}</div>
      <div class="ft-text"><b>${f}</b><span>« ${FAMILIES[f].slogan} »</span><small>${FAMILIES[f].desc}</small></div>
    </button>`).join('')}</div>`;
}

/* "- " puce, "**gras**", "`code`", "> GET /x/ {body}" = requête cliquable */
function richText(text) {
  const out = []; let ul = []; let chips = [];
  const inline = s => esc(s).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/`(.+?)`/g, '<code>$1</code>');
  const flush = () => {
    if (ul.length) out.push(`<ul>${ul.join('')}</ul>`);
    if (chips.length) out.push(`<div class="req-chips">${chips.join('')}</div>`);
    ul = []; chips = [];
  };
  for (const line of String(text || '').split('\n')) {
    if (line.startsWith('- ')) { if (chips.length) flush(); ul.push(`<li>${inline(line.slice(2))}</li>`); }
    else if (line.startsWith('> ')) { if (ul.length) flush(); chips.push(reqChip(line.slice(2))); }
    else { flush(); if (line.trim()) out.push(`<p>${inline(line)}</p>`); }
  }
  flush();
  return out.join('');
}

function reqChip(line) {
  const m = /^(\w+)\s+(\S+)\s*(.*)$/.exec(line.trim());
  if (!m) return '';
  const b = m[3];
  const badge = !b ? ''
    : b.startsWith('<') ? `&lt;Code&gt;${esc(/<tns:Code>([^<]*)/.exec(b)?.[1] ?? '?')}&lt;/Code&gt;`
    : esc(b.length > 30 ? b.slice(0, 28) + '…' : b);
  return `<button class="req-chip" data-go="${esc(line)}">
    <span class="mth m-${esc(m[1])}">${esc(m[1])}</span><code>${esc(m[2])}</code>${badge ? `<span class="has-body">${badge}</span>` : ''}
  </button>`;
}

function endScreen() {
  const petals = Array.from({ length: 22 }, () =>
    `<i style="left:${(Math.random() * 100).toFixed(1)}%;animation-delay:-${(Math.random() * 9).toFixed(2)}s;animation-duration:${(7 + Math.random() * 6).toFixed(2)}s;--s:${(0.6 + Math.random() * 0.9).toFixed(2)}"></i>`).join('');
  return `<section class="end">
    <div class="jasmine" aria-hidden="true">${petals}</div>
    <figure class="end-media">${sectionMedia(SECTIONS.fin, 'fin')}</figure>
    <div class="end-text">
      <div class="end-code">204</div>
      <div class="end-off">No Content</div>
      <h1>Ya3tikom essa7a</h1>
      <p>Body vide, cœur plein. Merci pour votre attention !</p>
      <p class="end-q">Des questions ? <code>POST /api/questions/</code></p>
    </div>
  </section>`;
}

/* ---------- vue brute ---------- */
const hlBody = (text, ct = '') => /json/.test(ct) ? hlJson(text) : /xml|html/.test(ct) || text.startsWith('<') ? hlXml(text) : esc(text);

function renderRaw(req, res, ct) {
  const reqHeaders = Object.entries({ Host: location.host, ...req.headers }).map(([k, v]) => `${k}: ${v}`).join('\n');
  const resHeaders = Object.entries(res.headers || {}).map(([k, v]) => `<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`).join('');
  const info = statusInfo(res);
  const reqBody = !req.body ? '' : req.body.startsWith('<') ? hlXml(req.body) : hlJson(req.body);
  $('#raw').innerHTML = `<div class="raw-grid">
    <section class="raw-req">
      <h3>Requête</h3>
      <pre class="code"><span class="t">${esc(req.method)}</span> ${esc(req.path)} HTTP/1.1\n<span class="h">${esc(reqHeaders)}</span>${reqBody ? `\n\n${reqBody}` : ''}</pre>
    </section>
    <section class="raw-res fam-${info.famille}">
      <h3>Réponse</h3>
      ${res.redirected ? `<p class="raw-note">↪ Redirection suivie par le navigateur : cette réponse vient de <code>${esc(finalPath(res))}</code></p>` : ''}
      <div class="raw-status">HTTP/1.1 <b>${res.status || 'ERR'}</b> ${esc(info.nom_officiel)}</div>
      <table class="headers">${resHeaders || '<tr><td class="empty">(aucun en-tête)</td></tr>'}</table>
      <pre class="code">${res.body ? hlBody(res.body, ct) : '<span class="empty">(body vide)</span>'}</pre>
    </section>
  </div>`;
}

function hlJson(text) {
  let pretty;
  try { pretty = JSON.stringify(JSON.parse(text), null, 2); } catch { return esc(text); }
  return pretty.replace(/("(?:\\.|[^"\\])*")(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/g,
    (m, str, colon, kw) => str ? (colon ? `<span class="k">${esc(str)}</span>${colon}` : `<span class="s">${esc(str)}</span>`)
      : `<span class="${kw ? 'b' : 'n'}">${m}</span>`);
}

function hlXml(text) {
  return esc(text)
    .replace(/&lt;\?.*?\?&gt;/g, m => `<span class="p">${m}</span>`)
    .replace(/&lt;(\/?)([\w:.-]+)((?:\s+[\w:.-]+=&quot;.*?&quot;)*)\s*(\/?)&gt;/g, (m, sl, name, attrs, self) =>
      `<span class="t">&lt;${sl}${name}</span>${attrs.replace(/([\w:.-]+)=(&quot;.*?&quot;)/g, '<span class="a">$1</span>=<span class="s">$2</span>')}<span class="t">${self}&gt;</span>`);
}

/* ---------- événements ---------- */
$('#req').addEventListener('submit', e => { e.preventDefault(); ++state.typing; send(); });
$('#method').addEventListener('change', e => { setMethod(e.target.value); if (['POST', 'PUT', 'PATCH'].includes(e.target.value)) toggleBody(true); });
$('#toggle-body').addEventListener('click', () => toggleBody());
const updateDot = () => { $('#body-dot').hidden = !($('#body').value.trim() || $('#extra-headers').value.trim()); };
$('#body').addEventListener('input', updateDot);
$('#extra-headers').addEventListener('input', updateDot);

document.addEventListener('click', e => {
  const goEl = e.target.closest('[data-go]');
  if (goEl) { go(goEl.dataset.go, !('fast' in goEl.dataset)); return; }
  const v = e.target.closest('[data-view]');
  if (v) setView(v.dataset.view);
  const sl = e.target.closest('[data-slide]');
  if (sl) nav(Number(sl.dataset.slide));
});

$('#toggle-format').addEventListener('click', () => {
  const [p, qs] = $('#path').value.split('?');
  const q = new URLSearchParams(qs || '');
  q.set('format', q.get('format') === 'xml' ? 'json' : 'xml');
  setView('raw');
  go(`${$('#method').value} ${p}?${q}`, false);
});

$('#replay-etag').addEventListener('click', e => {
  const lines = $('#extra-headers').value.split('\n').filter(l => l.trim() && !/^if-none-match\s*:/i.test(l));
  lines.push(`If-None-Match: ${e.currentTarget.dataset.etag}`);
  $('#extra-headers').value = lines.join('\n');
  updateDot();
  toggleBody(true);
  send();
});

document.addEventListener('keydown', e => {
  // Alt+A / Alt+E marchent partout, même dans un champ ; e.code ne dépend pas du clavier (AZERTY…)
  if (e.altKey && !e.ctrlKey && (e.code === 'KeyA' || e.code === 'KeyE')) {
    e.preventDefault();
    setToken(e.code === 'KeyA' ? 'admin' : 'etudiant');
    return;
  }
  if (e.target.closest('input, textarea, select') || e.altKey || e.ctrlKey || e.metaKey) return;
  if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') { e.preventDefault(); nav(e.key === 'ArrowRight' ? 1 : -1); }
  else if (e.key === 'ArrowUp' && state.up) { e.preventDefault(); setView('tounsi'); go(state.up); }
  else if (e.key === 'v') setView(state.view === 'tounsi' ? 'raw' : 'tounsi');
});

/* ---------- démarrage ---------- */
$('#origin').textContent = location.origin;
(async () => {
  try {  // catalogue des codes : titres et images des cartes d'erreur
    JSON.parse((await transport({ method: 'GET', path: '/api/codes/' })).body).forEach(c => state.catalog.set(c.code, c));
  } catch { /* serveur absent : cartes génériques par famille */ }
  // ?go=GET%20/api/slides/5/ : reprendre la présentation à un endroit précis
  go(new URLSearchParams(location.search).get('go') || 'GET /api/slides/1/');
})();
})();
