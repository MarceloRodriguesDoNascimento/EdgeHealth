// Funções que montam os elementos da tela
// Cria um elemento HTML
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
// Mensagem de nenhum registro
export const empty = (text = 'Nenhum registro encontrado.') => el('div', { className: 'empty' }, text);
// Campo com rótulo
export const label = (text, input) => el('label', { className: 'field' }, el('span', {}, text), input);
// Caixa de texto
export const input = (name, placeholder = '', props = {}) => el('input', { name, placeholder, ...props });
// Botão
export const button = (text, action, kind = 'secondary', props = {}) => el('button', { type: 'button', className: `button ${kind}`, onclick: action, ...props }, text);
const NAMES = { ONLINE: 'Online', INSTAVEL: 'Instável', OFFLINE: 'Offline', BAIXA: 'Baixa', MEDIA: 'Média', ALTA: 'Alta', CRITICA: 'Crítica',
  ABERTA: 'Aberta', ENCERRADA: 'Encerrada', INDISPONIBILIDADE: 'Indisponibilidade', INSTABILIDADE: 'Instabilidade',
  LOCALIZADA: 'Problema localizado', COMPARTILHADA: 'Infraestrutura compartilhada', CONGESTIONAMENTO: 'Congestionamento',
  LATENCIA: 'Latência alta', RECORRENTE: 'Falha recorrente', RECUPERACAO: 'O dispositivo voltou a responder', ARQUIVAMENTO: 'O dispositivo foi arquivado' };
// Traduz códigos da API para a tela
export const human = code => NAMES[code] || code;
// Selo colorido de status
export const badge = (text, kind) => el('span', { className: `badge ${kind || text || 'SEM_COLETA'}` }, text ? human(text) : 'Aguardando coleta');
// Data no formato brasileiro
export function date(value) { return value ? new Date(value).toLocaleString('pt-BR') : '—'; }
// Duração legível
export function duration(seconds) { const m = Math.floor(seconds / 60); return m >= 60 ? `${Math.floor(m/60)}h ${m%60}min` : `${m}min ${Math.floor(seconds%60)}s`; }
// Valor em reais
export function brl(value) { return value === null || value === undefined || value === '' ? '—' : Number(value).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }); }
// Converte valor digitado para a API
export function moneyInput(text) {
  const raw = String(text ?? '').trim().replace(/^R\$\s*/i, '');
  if (!raw) return null;
  return raw.includes(',') ? raw.replace(/\./g, '').replace(',', '.') : raw;
}
// Número com vírgula e sufixo
export function number(value, suffix = '') { return value === null || value === undefined ? '—' : `${Number(value).toLocaleString('pt-BR', { maximumFractionDigits: 2 })}${suffix}`; }
// Lista de opções
export function select(name, items, value = '') {
  const node = el('select', { name }, items.map(([key, text]) => el('option', { value: String(key) }, text)));
  node.value = String(value); return node;
}
// Tabela de dados
export function table(headings, rows) {
  // Diz se a célula é de ações
  const isActions = cell => Boolean(cell?.classList?.contains('actions'));
  return el('div', { className: 'table-wrap' }, el('table', { role: 'table' },
    el('thead', { role: 'rowgroup' }, el('tr', { role: 'row' }, headings.map(h => el('th', { scope: 'col', role: 'columnheader' }, h)))),
    el('tbody', { role: 'rowgroup' }, rows.length
      ? rows.map(row => el('tr', { role: 'row' }, row.map((cell, i) => el('td', { role: 'cell', 'data-label': headings[i], className: isActions(cell) ? 'cell-actions' : null }, cell))))
      : el('tr', { role: 'row' }, el('td', { role: 'cell', colSpan: headings.length, className: 'cell-empty' }, empty())))));
}
// Aviso rápido no canto da tela
export function toast(message, error = false) {
  const area = document.querySelector('#notifications');
  const node = el('div', { className: `toast ${error ? 'error' : ''}` }, message);
  area.append(node); setTimeout(() => node.remove(), 6000);
}
// Formulário com envio e mensagens de erro
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
// Janela modal
export function modal(title, content) {
  const previous = document.activeElement;
  const headingId = `modal-title-${++modalCount}`;
  const dialog = el('dialog', { className: 'modal', 'aria-labelledby': headingId });
  // Fecha a janela
  const close = () => dialog.close();
  dialog.append(el('div', { className: 'modal-heading' }, el('h2', { id: headingId }, title), button('Fechar', close, 'ghost modal-close')));
  dialog.append(typeof content === 'function' ? content(close) : content);
  dialog.addEventListener('close', () => { dialog.remove(); previous?.focus(); }, { once: true });
  document.body.append(dialog); dialog.showModal(); return dialog;
}
// Janela de confirmação
export function confirmAction(title, message, action, confirmText = 'Confirmar', kind = 'danger') {
  modal(title, close => el('div', {}, el('p', {}, message), el('div', { className: 'actions end' },
    button('Cancelar', close, 'secondary', { autofocus: true }), button(confirmText, async event => {
      const target = event.currentTarget;
      target.disabled = true;
      try { await action(); close(); }
      catch (e) { toast(e.message, true); target.disabled = false; }
    }, kind))));
}
// Título da tela
export function pageHeader(title, description, actions) {
  return el('header', { className: 'page-heading' }, el('div', {}, el('h1', {}, title), description ? el('p', { className: 'muted' }, description) : null), actions);
}
// Monta os parâmetros da URL
export function params(data) { return new URLSearchParams(Object.entries(data).filter(([,v]) => v !== '' && v !== null && v !== undefined)).toString(); }
const ICONS = {
  pulse: 'M3 12h4l3-7 4 14 3-7h4',
  server: 'M4 4h16v6H4zM4 14h16v6H4zM8 7h.01M8 17h.01',
  clock: 'M12 3a9 9 0 1 0 0 18a9 9 0 0 0 0-18zM12 7v5l3 2',
  download: 'M12 4v11M7.5 10.5 12 15l4.5-4.5M4 20h16',
  building: 'M5 21V4h10v17M15 10h4v11M3 21h18M9 8h2M9 12h2M9 16h2',
  antenna: 'M12 11v10M8 21h8M8.5 14.5a5 5 0 0 1 0-7M15.5 7.5a5 5 0 0 1 0 7M5.5 17.5a9 9 0 0 1 0-13M18.5 4.5a9 9 0 0 1 0 13',
  users: 'M9 11a4 4 0 1 0 0-8a4 4 0 0 0 0 8zM2 21v-1a6 6 0 0 1 6-6h2a6 6 0 0 1 6 6v1M16 3.5a4 4 0 0 1 0 7M18 14.3a6 6 0 0 1 4 5.7v1',
  menu: 'M4 7h16M4 12h16M4 17h16',
};
// Ícone do menu
export function icon(name) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  for (const [key, value] of Object.entries({ viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.7', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', class: 'icon', 'aria-hidden': 'true' })) node.setAttribute(key, value);
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('d', ICONS[name]); node.append(path);
  return node;
}
// Porta do painel com LED de status
export const port = (status, props = {}, tag = 'span') => el(tag, { className: `port ${status || 'SEM_COLETA'}`, ...(tag === 'button' ? { type: 'button' } : {}), ...props });
// Logo do EdgeHealth
export const brandLogo = () => el('img', { src: '/logo.svg', alt: 'EdgeHealth', className: 'brand-logo', width: 36, height: 36 });
