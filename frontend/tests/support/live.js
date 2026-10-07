// Real-browser harness for layout checks: the disposable API (backend/tests/ui_server.py)
// serves the built frontend (dist) and a migrated temporary SQLite; Chrome or Edge renders it.
// Only layout can be checked here: jsdom does not compute widths.
import {spawn} from 'node:child_process';
import {createInterface} from 'node:readline';
import {existsSync} from 'node:fs';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright-core';

const pause = ms => new Promise(resolve => setTimeout(resolve, ms));

export function findBrowser() {
  const candidates = [process.env.EDGEHEALTH_BROWSER,
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
    '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'];
  return candidates.find(path => path && existsSync(path)) || null;
}

export async function startApi() {
  const backend = fileURLToPath(new URL('../../../backend/', import.meta.url));
  const candidate = join(backend, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  const python = process.env.EDGEHEALTH_PYTHON || (existsSync(candidate) ? candidate : (process.platform === 'win32' ? 'python' : 'python3'));
  const child = spawn(python, ['-u', join(backend, 'tests/ui_server.py')], {cwd: backend, stdio: ['pipe', 'pipe', 'pipe']});
  let base, errors = '', sequence = 0;
  const pending = new Map();
  child.stderr.on('data', chunk => { errors += chunk; });
  const lines = createInterface({input: child.stdout});
  lines.on('line', line => {
    let data; try { data = JSON.parse(line); } catch { return; }
    if (data.ready) base = data.ready;
    if (data.id && pending.has(data.id)) { pending.get(data.id)(data); pending.delete(data.id); }
  });
  for (let i = 0; i < 300 && !base && child.exitCode === null; i++) await pause(50);
  if (!base) throw new Error('API de teste não iniciou: ' + errors);
  // Deterministic probe through the real collection pipeline (see ui_server.py).
  const probe = (deviceId, received, latency = null) => new Promise(resolve => {
    const id = ++sequence; pending.set(id, resolve);
    child.stdin.write(JSON.stringify({id, device_id: deviceId, sent: 4, received, latency_ms: latency}) + '\n');
  });
  const close = async () => {
    child.stdin.end();
    for (let i = 0; i < 120 && child.exitCode === null; i++) await pause(50);
    if (child.exitCode === null) child.kill();
    lines.close();
  };
  return {base, probe, close};
}

export async function launch() {
  const executablePath = findBrowser();
  if (!executablePath) return null;
  return chromium.launch({executablePath, headless: true});
}

async function api(context, method, path, data) {
  const csrf = (await context.cookies()).find(c => c.name === 'edgehealth_csrf')?.value || '';
  const response = await context.request.fetch(path, {method, data, headers: {'X-CSRF-Token': csrf}});
  if (!response.ok()) throw new Error(`${method} ${path}: HTTP ${response.status()} ${await response.text()}`);
  return response.status() === 204 ? null : response.json();
}

// Long names, IPv6 and every incident kind: the worst realistic content for narrow screens.
export async function seed(browser, {base, probe}) {
  const admin = await browser.newContext({baseURL: base});
  await api(admin, 'POST', '/api/auth/registro', {nome_fantasia: 'Rede Corporativa de Demonstração Responsiva Ltda', cnpj: '11222333000181',
    nome: 'Administradora Responsável pela Infraestrutura', email: 'admin@responsivo.example', senha: 'senha-responsiva-123', aceite_termos: true});
  await api(admin, 'POST', '/api/coletores', {nome: 'Coletor da matriz — andar térreo, sala de TI'});
  // Costs configured: the first-access cost assistant is checked on its own (responsive.test.js).
  await api(admin, 'PUT', '/api/empresa/custos', {salario_medio: '3000', total_funcionarios: 40,
    expediente: {dias: [1, 2, 3, 4, 5, 6, 7], inicio: '00:00', fim: '23:59'}});
  const devices = [];
  for (const [nome, ip, tipo, localizacao] of [
    ['Switch principal do segundo andar (rack B)', '10.20.30.40', 'Switch gerenciável', 'Andar 2 · rack B · corredor norte'],
    ['Servidor de arquivos', '2001:db8:85a3:0:0:8a2e:370:7334', 'Servidor', 'Datacenter'],
    ['Impressora da recepção', '10.20.30.41', 'Impressora', 'Térreo · recepção']]) {
    devices.push(await api(admin, 'POST', '/api/dispositivos', {nome, ip, tipo, localizacao}));
  }
  const [sw, server, printer] = devices;
  for (let i = 0; i < 24; i++) {
    await probe(server.id, 4, 2 + (i % 7) * 3);
    await probe(sw.id, i % 5 === 4 ? 3 : 4, 8 + (i % 4) * 5);
  }
  for (let i = 0; i < 3; i++) await probe(printer.id, 0);  // INDISPONIBILIDADE
  await probe(sw.id, 4, 240);                              // INSTABILIDADE (latency)
  const failures = await api(admin, 'GET', '/api/falhas?limite=10');
  await api(admin, 'POST', '/api/usuarios', {nome: 'Técnico de Plantão', email: 'tecnico@responsivo.example', senha: 'senha-tecnico-123'});
  return {admin, failureId: failures.items[0].id, adminLogin: ['admin@responsivo.example', 'senha-responsiva-123'],
    technicianLogin: ['tecnico@responsivo.example', 'senha-tecnico-123']};
}

// Layout problems a phone user would notice, measured by the browser.
export function auditPage() {
  const doc = document.documentElement, vw = doc.clientWidth, vh = window.innerHeight;
  const visible = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e); return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; };
  const name = e => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (typeof e.className === 'string' && e.className ? '.' + e.className.trim().split(/\s+/).join('.') : '') + (e.textContent ? ` "${e.textContent.trim().slice(0, 28)}"` : '');
  const all = [...document.querySelectorAll('body *')].filter(visible);
  const inScroller = e => { for (let p = e.parentElement; p && p !== document.body; p = p.parentElement) { const o = getComputedStyle(p).overflowX; if (o === 'auto' || o === 'scroll' || o === 'hidden') return true; } return false; };
  const outside = all.filter(e => e.getBoundingClientRect().right > vw + 1 && !inScroller(e)).map(name);
  const scrollers = all.filter(e => e.scrollWidth > e.clientWidth + 1 && ['auto', 'scroll'].includes(getComputedStyle(e).overflowX) && !e.matches('pre,textarea,.evidence-json')).map(name);
  const targets = all.filter(e => e.matches('button,a[href],input:not([type=hidden]),select,textarea,summary'));
  const small = targets.filter(e => { const r = e.getBoundingClientRect(); const box = e.matches('input[type=checkbox],input[type=radio]') ? e.closest('label') || e : e; const b = box.getBoundingClientRect();
    const inline = e.matches('a') && getComputedStyle(e).display === 'inline' && e.closest('p,li,dd,span,small');  // links inside running text
    return !inline && (Math.min(r.height, b.height) < 44 - 0.5 && b.height < 44 - 0.5 || b.width < 44 - 0.5); }).map(name);
  const smallFont = all.filter(e => e.matches('input:not([type=checkbox]):not([type=radio]),select,textarea') && parseFloat(getComputedStyle(e).fontSize) < 16).map(name);
  const dialog = document.querySelector('dialog[open]');
  let modal = null;
  if (dialog) { const r = dialog.getBoundingClientRect(); modal = {fits: r.left >= 0 && r.right <= vw + 1 && r.top >= 0 && r.bottom <= vh + 1, scrolls: dialog.scrollHeight > dialog.clientHeight, width: Math.round(r.width)}; }
  const overlaps = (() => {
    const bar = document.querySelector('.topbar'); if (!bar) return [];
    const kids = [...bar.querySelectorAll('strong,button,.user-name,.menu-button')].filter(visible).map(e => [e, e.getBoundingClientRect()]);
    const hits = [];
    for (let i = 0; i < kids.length; i++) for (let j = i + 1; j < kids.length; j++) { const [a, ra] = kids[i], [b, rb] = kids[j];
      if (a.contains(b) || b.contains(a)) continue;
      if (ra.left < rb.right - 1 && rb.left < ra.right - 1 && ra.top < rb.bottom - 1 && rb.top < ra.bottom - 1) hits.push(name(a) + ' × ' + name(b)); }
    return hits;
  })();
  return {width: vw, pageOverflow: doc.scrollWidth - doc.clientWidth, outside: outside.slice(0, 8), outsideCount: outside.length,
    innerHorizontalScroll: scrollers.slice(0, 5), smallTargets: small.length, smallTargetSamples: small.slice(0, 6),
    smallInputFont: smallFont.length, modal, topbarOverlap: overlaps};
}

export async function settle(page) {
  // Static pages (termos.html, privacidade.html) have no #app.
  await page.waitForFunction(() => !document.querySelector('#app') || (!document.querySelector('.loading') && document.querySelector('#app').children.length), null, {timeout: 15000});
  await page.waitForTimeout(350);  // charts and fonts
}
