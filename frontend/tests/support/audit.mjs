// Responsive audit: every screen at 360/390/414/768/1024 px, plus 390 px screenshots.
//   node tests/support/audit.mjs antes|depois
// Output: ../tests/responsivo/<label>/ (audit.json, audit.md and PNGs; git-ignored).
import {mkdirSync, writeFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {startApi, launch, seed, auditPage, settle} from './live.js';

const label = process.argv[2] || 'auditoria';
const out = fileURLToPath(new URL(`../../../tests/responsivo/${label}/`, import.meta.url));
mkdirSync(out, {recursive: true});
const WIDTHS = [360, 390, 414, 768, 1024];

export function screens(failureId) {
  const open = text => async page => { await page.getByRole('button', {name: text, exact: true}).first().click(); await page.waitForSelector('dialog[open]'); await page.waitForTimeout(300); };
  return [
    ['login', 'anon', '/', null],
    ['cadastro', 'anon', '/', async page => { await page.getByRole('button', {name: 'Cadastrar minha empresa'}).click(); }],
    ['termos-pendentes', 'tech', '/', null],
    ['visao-da-rede', 'admin', '/#dashboard', null],
    ['menu-aberto', 'admin', '/#dashboard', async page => { const b = page.locator('.menu-button'); if (await b.isVisible()) { await b.click(); await page.waitForTimeout(200); } }],
    ['dispositivos', 'admin', '/#dispositivos', null],
    ['modal-dispositivo', 'admin', '/#dispositivos', open('Cadastrar dispositivo')],
    ['modal-metricas', 'admin', '/#dispositivos', open('Métricas')],
    ['historico', 'admin', '/#historico', null],
    ['falha', 'admin', `/#falha/${failureId}`, null],
    ['relatorios', 'admin', '/#relatorios', null],
    ['coletores', 'admin', '/#coletores', null],
    ['empresa', 'admin', '/#empresa', null],
    ['equipe', 'admin', '/#usuarios', null],
    ['modal-usuario', 'admin', '/#usuarios', open('Cadastrar usuário')],
    ['confirmar-sair', 'admin', '/#dashboard', open('Sair')],
    ['termos-html', 'anon', '/termos.html', null],
    ['privacidade-html', 'anon', '/privacidade.html', null],
  ];
}

// One browser context per account and width: below 768 px the context emulates a phone
// (isMobile, touch, overlay scrollbars), otherwise a classic desktop window.
export async function contexts(browser, base, data) {
  const states = {};
  for (const [who, login] of [['anon', null], ['admin', data.adminLogin], ['tech', data.technicianLogin]]) {
    const context = await browser.newContext({baseURL: base});
    if (login) {
      const r = await context.request.post('/api/auth/login', {data: {email: login[0], senha: login[1]}});
      if (!r.ok()) throw new Error('login falhou: ' + await r.text());
    }
    states[who] = await context.storageState(); await context.close();
  }
  return (who, width) => browser.newContext({baseURL: base, storageState: states[who], viewport: {width, height: 800},
    ...(width < 768 ? {isMobile: true, hasTouch: true, deviceScaleFactor: 2} : {})});
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const stack = await startApi();
  const browser = await launch();
  if (!browser) throw new Error('Nenhum Chrome/Edge encontrado (defina EDGEHEALTH_BROWSER).');
  try {
    const data = await seed(browser, stack);
    const ctx = await contexts(browser, stack.base, data);
    const results = [];
    for (const [name, who, path, action] of screens(data.failureId)) {
      for (const width of WIDTHS) {
        const context = await ctx(who, width);
        const page = await context.newPage();
        await page.goto(path); await settle(page);
        if (action) await action(page);
        const audit = await page.evaluate(auditPage);
        results.push({screen: name, viewport: width, ...audit});
        if (width === 390) await page.screenshot({path: `${out}${name}.png`, fullPage: true});
        await context.close();
      }
    }
    writeFileSync(`${out}audit.json`, JSON.stringify(results, null, 2));
    const rows = results.map(r => `| ${r.screen} | ${r.viewport} | ${r.pageOverflow > 0 ? `**${r.pageOverflow}px**` : 0} | ${r.outsideCount}${r.outside.length ? ': ' + r.outside.slice(0, 3).join('; ') : ''} | ${r.innerHorizontalScroll.join('; ') || '-'} | ${r.smallTargets}${r.smallTargetSamples.length ? ': ' + r.smallTargetSamples.slice(0, 3).join('; ') : ''} | ${r.smallInputFont} | ${r.modal ? `${r.modal.fits ? 'cabe' : '**sai da tela**'}${r.modal.scrolls ? ', rola' : ''}` : '-'} | ${r.topbarOverlap.join('; ') || '-'} |`);
    writeFileSync(`${out}audit.md`, ['| Tela | px | Rolagem horizontal | Elementos fora da tela | Rolagem interna | Alvos < 44px | Inputs < 16px | Modal | Topbar sobreposta |', '|---|---|---|---|---|---|---|---|---|', ...rows].join('\n').replace(/\|/g, '|') + '\n');
    console.log(`Auditoria: ${results.length} medições em ${out}`);
  } finally {
    await browser.close(); await stack.close();
  }
}
