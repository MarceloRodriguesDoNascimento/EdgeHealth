// Screenshots of the main screens for the documentation (README "Casos de uso e telas").
//   npm run build && node tests/support/telas.mjs
// Same disposable API and fictitious data as the responsive test; output: ../docs/img/telas/*.png
import {mkdirSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {startApi, launch, seed, settle} from './live.js';
import {screens, contexts} from './audit.mjs';

const out = fileURLToPath(new URL('../../../docs/img/telas/', import.meta.url));
mkdirSync(out, {recursive: true});
const WANTED = ['login', 'cadastro', 'visao-da-rede', 'dispositivos', 'modal-dispositivo', 'modal-metricas', 'historico', 'falha',
  'relatorios', 'coletores', 'empresa', 'equipe'];

const stack = await startApi();
const browser = await launch();
if (!browser) throw new Error('Nenhum Chrome/Edge encontrado (defina EDGEHEALTH_BROWSER).');
try {
  const data = await seed(browser, stack);
  const ctx = await contexts(browser, stack.base, data);
  for (const [name, who, path, action] of screens(data.failureId).filter(s => WANTED.includes(s[0]))) {
    const context = await ctx(who, 1280);
    const page = await context.newPage();
    await page.goto(path); await settle(page);
    if (action) await action(page);
    await page.screenshot({path: `${out}${name}.png`, fullPage: !name.startsWith('modal')});
    await context.close();
  }
  console.log(`${WANTED.length} telas em ${out}`);
} finally {
  await browser.close(); await stack.close();
}
