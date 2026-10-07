export function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props || {})) {
    if (value === undefined || value === null || value === false) continue;
    if (key.startsWith('on')) node.addEventListener(key.slice(2).toLowerCase(), value);
    else if (key === 'className') node.className = value;
    else if (key === 'dataset') Object.assign(node.dataset, value);
    else if (key in node && !key.startsWith('aria')) node[key] = value;
    else node.setAttribute(key, String(value));
  }
  for (const child of children.flat(Infinity)) {
    if (child !== null && child !== undefined && child !== false) node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}
export const empty = (text = 'Nenhum registro encontrado.') => el('div', { className: 'empty' }, text);
export const label = (text, input) => el('label', { className: 'field' }, el('span', {}, text), input);
export const input = (name, placeholder = '', props = {}) => el('input', { name, placeholder, ...props });
export const button = (text, action, kind = 'secondary', props = {}) => el('button', { type: 'button', className: `button ${kind}`, onclick: action, ...props }, text);
export const badge = (text, kind) => el('span', { className: `badge ${kind || text || 'SEM_COLETA'}` }, text || 'Aguardando coleta');
export function date(value) { return value ? new Date(value).toLocaleString('pt-BR') : '—'; }
export function duration(seconds) { const m = Math.floor(seconds / 60); return m >= 60 ? `${Math.floor(m/60)}h ${m%60}min` : `${m}min ${Math.floor(seconds%60)}s`; }
// Money arrives from the API as exact decimal text ("1234.56"); display only, never recomputed here.
export function brl(value) { return value === null || value === undefined || value === '' ? '—' : Number(value).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }); }
// "3.000,50", "3000,50" or "3000.50" -> "3000.50" (sent as text; the API keeps it as Decimal). Empty -> null.
export function moneyInput(text) {
  const raw = String(text ?? '').trim().replace(/^R\$\s*/i, '');
  if (!raw) return null;
  return raw.includes(',') ? raw.replace(/\./g, '').replace(',', '.') : raw;
}
export function number(value, suffix = '') { return value === null || value === undefined ? '—' : `${Number(value).toLocaleString('pt-BR', { maximumFractionDigits: 2 })}${suffix}`; }
export function select(name, items, value = '') {
  const node = el('select', { name }, items.map(([key, text]) => el('option', { value: String(key) }, text)));
  node.value = String(value); return node;
}
// On narrow screens each row becomes a card (styles.css): data-label carries the column name,
// and explicit roles keep the table semantics that display:block would drop.
export function table(headings, rows) {
  const isActions = cell => Boolean(cell?.classList?.contains('actions'));
  return el('div', { className: 'table-wrap' }, el('table', { role: 'table' },
    el('thead', { role: 'rowgroup' }, el('tr', { role: 'row' }, headings.map(h => el('th', { scope: 'col', role: 'columnheader' }, h)))),
    el('tbody', { role: 'rowgroup' }, rows.length
      ? rows.map(row => el('tr', { role: 'row' }, row.map((cell, i) => el('td', { role: 'cell', 'data-label': headings[i], className: isActions(cell) ? 'cell-actions' : null }, cell))))
      : el('tr', { role: 'row' }, el('td', { role: 'cell', colSpan: headings.length, className: 'cell-empty' }, empty())))));
}
export function toast(message, error = false) {
  const area = document.querySelector('#notifications');
  const node = el('div', { className: `toast ${error ? 'error' : ''}` }, message);
  area.append(node); setTimeout(() => node.remove(), 6000);
}
export function form(fields, submitText, onSubmit) {
  const error = el('div', { className: 'form-error', role: 'alert' });
  const submit = el('button', { type: 'submit', className: 'button primary' }, submitText);
  const node = el('form', { className: 'form-grid' }, fields, error, el('div', { className: 'form-actions' }, submit));
  node.addEventListener('submit', async event => {
    event.preventDefault(); error.textContent = ''; submit.disabled = true;
    const original = submit.textContent; submit.textContent = 'Salvando…';
    try { await onSubmit(Object.fromEntries(new FormData(node)), node); }
    catch (e) { error.textContent = e.message; }
    finally { submit.disabled = false; submit.textContent = original; }
  }); return node;
}
let modalCount = 0;
// Native <dialog> + showModal(): focus moves into the dialog and Esc closes it.
export function modal(title, content) {
  const previous = document.activeElement;
  const headingId = `modal-title-${++modalCount}`;
  const dialog = el('dialog', { className: 'modal', 'aria-labelledby': headingId });
  const close = () => dialog.close();
  dialog.append(el('div', { className: 'modal-heading' }, el('h2', { id: headingId }, title), button('Fechar', close, 'ghost modal-close')));
  dialog.append(typeof content === 'function' ? content(close) : content);
  dialog.addEventListener('close', () => { dialog.remove(); previous?.focus(); }, { once: true });
  document.body.append(dialog); dialog.showModal(); return dialog;
}
export function confirmAction(title, message, action, confirmText = 'Confirmar', kind = 'danger') {
  // Initial focus on "Cancelar": Enter right after opening never triggers the action.
  modal(title, close => el('div', {}, el('p', {}, message), el('div', { className: 'actions end' },
    button('Cancelar', close, 'secondary', { autofocus: true }), button(confirmText, async event => {
      const target = event.currentTarget;
      target.disabled = true;
      try { await action(); close(); }
      catch (e) { toast(e.message, true); target.disabled = false; }
    }, kind))));
}
export function pageHeader(title, description, actions) {
  return el('header', { className: 'page-heading' }, el('div', {}, el('h1', {}, title), description ? el('p', { className: 'muted' }, description) : null), actions);
}
export function params(data) { return new URLSearchParams(Object.entries(data).filter(([,v]) => v !== '' && v !== null && v !== undefined)).toString(); }
// Brand logo (public/logo.svg). The image carries the accessible name; adjacent text is aria-hidden.
export const brandLogo = () => el('img', { src: '/logo.svg', alt: 'EdgeHealth', className: 'brand-logo', width: 36, height: 36 });
