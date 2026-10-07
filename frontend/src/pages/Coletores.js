import { el, input, label, form, button, modal, table, badge, date, pageHeader, toast, confirmAction } from '../ui/dom.js';
import { apiFetch, json } from '../services/api.js';

const STATES = { ATIVO: ['Ativo', 'ONLINE'], DESATUALIZADO: ['Sem contato recente', 'OFFLINE'], NUNCA_CONECTADO: ['Aguardando conexão', 'SEM_COLETA'], REVOGADO: ['Revogado', 'SEM_COLETA'] };
export const collectorBadge = state => badge(...(STATES[state] || [state, 'SEM_COLETA']));

// The plain credential exists only in this response; the server keeps a hash.
function showToken(collector, token) {
  const field = el('input', { value: token, readOnly: true, className: 'mono', 'aria-label': 'Credencial do coletor' });
  modal(`Credencial · ${collector.nome}`, el('div', {},
    el('p', {}, 'Copie a credencial agora. Ela não será exibida novamente; se for perdida, gere outra (rotação).'),
    field,
    el('div', { className: 'actions end' }, button('Copiar', async () => {
      try { await navigator.clipboard.writeText(token); toast('Credencial copiada.'); } catch { field.select(); toast('Selecione e copie manualmente.', true); }
    }, 'primary')),
    el('p', { className: 'muted small' }, 'No computador da rede monitorada, salve-a em um arquivo com acesso restrito e informe-o ao coletor com --token-file. Consulte collector/README.md.')));
}

export async function Coletores() {
  const body = el('div'); let load;
  load = async () => {
    const collectors = await apiFetch('/coletores');
    body.replaceChildren(table(['Coletor', 'Situação', 'Último contato', 'Dispositivos', 'Fila local', 'Último erro', 'Ações'], collectors.map(c => [
      el('div', {}, el('strong', {}, c.nome), el('small', { className: 'muted mono' }, `${c.token_prefixo}…`)),
      collectorBadge(c.estado),
      el('div', {}, date(c.ultimo_contato), c.versao ? el('small', { className: 'muted' }, `versão ${c.versao}`) : null),
      String(c.dispositivos),
      c.fila_pendente === null ? '—' : String(c.fila_pendente),
      c.ultimo_erro ? el('small', { className: 'error-text' }, `${c.ultimo_erro} (${date(c.ultimo_erro_em)})`) : '—',
      c.estado === 'REVOGADO' ? el('small', { className: 'muted' }, `Revogado em ${date(c.revogado_em)}`) : el('div', { className: 'actions compact' },
        button('Nova credencial', () => confirmAction('Gerar nova credencial?', `A credencial atual de “${c.nome}” deixará de funcionar imediatamente.`, async () => {
          const result = await apiFetch(`/coletores/${c.id}/rotacionar`, { method: 'POST', body: '{}' });
          await load(); showToken(result.coletor, result.token);
        }), 'ghost'),
        button('Revogar', () => confirmAction('Revogar coletor?', `“${c.nome}” não poderá mais enviar dados. Os dispositivos atribuídos a ele ficarão sem coleta até serem atribuídos a outro coletor.`, async () => {
          await apiFetch(`/coletores/${c.id}/revogar`, { method: 'POST', body: '{}' }); toast('Coletor revogado.'); await load();
        }), 'ghost danger-text'))
    ])));
  };
  const create = () => modal('Cadastrar coletor', close => form([
    label('Nome', input('nome', 'Ex.: Coletor da matriz', { required: true, maxLength: 100 })),
    el('p', { className: 'muted full' }, 'O coletor é instalado em um computador dentro da rede da empresa. Ele mede os dispositivos atribuídos e envia os resultados por HTTPS; nenhuma porta de entrada é aberta na rede.')
  ], 'Cadastrar e gerar credencial', async data => {
    const result = await apiFetch('/coletores', { method: 'POST', body: json(data) });
    close(); await load(); showToken(result.coletor, result.token);
  }));
  await load();
  return el('section', {}, pageHeader('Coletores', 'Agentes que medem os dispositivos a partir da rede da empresa.', button('Cadastrar coletor', create, 'primary')),
    el('p', { className: 'muted' }, 'Dispositivos sem coletor atribuído são medidos pelo worker local do servidor, que só alcança redes acessíveis a ele. Na hospedagem em nuvem, atribua cada dispositivo da rede privada a um coletor.'),
    body);
}
