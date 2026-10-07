import {test} from 'node:test';
import assert from 'node:assert/strict';
import {startApi, launch, seed, settle, findBrowser} from './support/live.js';
import {screens, contexts} from './support/audit.mjs';

// Real layout in Chrome/Edge (jsdom computes no widths). Skipped only when no browser is installed.
test('telas principais em 360 px sem rolagem horizontal; menu acessível; desktop preservado',
  {timeout: 180000, skip: findBrowser() ? false : 'Chrome/Edge não encontrado (defina EDGEHEALTH_BROWSER)'}, async t => {
    const stack = await startApi();
    t.after(() => stack.close());
    const browser = await launch();
    t.after(() => browser.close());
    const data = await seed(browser, stack);
    const ctx = await contexts(browser, stack.base, data);

    for (const [name, who, path, action] of screens(data.failureId)) {
      const context = await ctx(who, 360);
      const page = await context.newPage();
      await page.goto(path); await settle(page);
      if (action) await action(page);
      const layout = await page.evaluate(() => {
        const doc = document.documentElement, dialog = document.querySelector('dialog[open]');
        const r = dialog?.getBoundingClientRect();
        return {scroll: doc.scrollWidth, client: doc.clientWidth, dialog: r ? {left: r.left, right: r.right, top: r.top, bottom: r.bottom, vh: innerHeight} : null};
      });
      assert.ok(layout.scroll <= layout.client, `${name}: rolagem horizontal (${layout.scroll}px > ${layout.client}px)`);
      if (layout.dialog) {
        const d = layout.dialog;
        assert.ok(d.left >= 0 && d.right <= layout.client && d.top >= 0 && d.bottom <= d.vh, `${name}: modal fora da tela ${JSON.stringify(d)}`);
      }
      await context.close();
    }

    // Menu button below 850 px: aria-expanded, focus into the list, Esc and navigation close it.
    const phone = await (await ctx('admin', 360)).newPage();
    await phone.goto('/#dashboard'); await settle(phone);
    const menu = phone.locator('.menu-button'), nav = phone.locator('#main-nav');
    assert.equal(await menu.getAttribute('aria-expanded'), 'false');
    assert.equal(await nav.isVisible(), false);
    await menu.click();
    assert.equal(await menu.getAttribute('aria-expanded'), 'true');
    assert.ok(await nav.isVisible());
    assert.ok(await phone.evaluate(() => document.activeElement.closest('#main-nav') !== null), 'foco deve ir para a navegação');
    await phone.keyboard.press('Escape');
    assert.equal(await menu.getAttribute('aria-expanded'), 'false');
    assert.ok(await phone.evaluate(() => document.activeElement.classList.contains('menu-button')), 'Esc devolve o foco ao botão');
    await menu.click();
    await nav.getByRole('link', {name: 'Dispositivos'}).click();
    await phone.waitForURL(/#dispositivos$/);
    assert.equal(await menu.getAttribute('aria-expanded'), 'false');
    assert.equal(await nav.isVisible(), false);
    // Table rows become labelled cards; touch targets and input font follow phone guidance.
    await settle(phone);
    const cards = await phone.evaluate(() => {
      const cell = document.querySelector('.table-wrap td[data-label]');
      const targets = [...document.querySelectorAll('#content button, .menu-button')].map(b => b.getBoundingClientRect()).filter(r => r.width);
      return {display: getComputedStyle(cell).display, label: getComputedStyle(cell, '::before').content,
        minTarget: Math.min(...targets.map(r => Math.min(r.width, r.height)))};
    });
    assert.equal(cards.display, 'grid');
    assert.equal(cards.label, '"Dispositivo"');
    assert.ok(cards.minTarget >= 44, `alvo de toque com ${cards.minTarget}px`);
    await phone.getByRole('button', {name: 'Cadastrar dispositivo'}).click();
    await phone.waitForSelector('dialog[open] form');
    const fonts = await phone.evaluate(() => [...document.querySelectorAll('dialog input, dialog select')].map(e => parseFloat(getComputedStyle(e).fontSize)));
    assert.ok(fonts.length && fonts.every(f => f >= 16), `inputs com fonte < 16px: ${fonts}`);

    // Desktop keeps the sidebar navigation and the classic table.
    const desk = await (await browser.newContext({baseURL: stack.base, storageState: await phone.context().storageState(), viewport: {width: 1280, height: 800}})).newPage();
    await desk.goto('/#dispositivos'); await settle(desk);
    assert.equal(await desk.locator('.menu-button').isVisible(), false);
    assert.ok(await desk.locator('#main-nav').isVisible());
    assert.equal(await desk.evaluate(() => getComputedStyle(document.querySelector('.table-wrap td')).display), 'table-cell');
    assert.ok(await desk.evaluate(() => document.querySelector('.table-wrap th').getBoundingClientRect().height > 0));
  });
