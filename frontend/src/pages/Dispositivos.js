import { el, input, label, button, form, table, badge, modal, confirmAction, toast, date, number, pageHeader, select, moneyInput } from '../ui/dom.js';
import { apiFetch, json } from '../services/api.js';

// A silent collector means "no recent evidence", never "device offline".
const COLLECTOR_NOTE = { DESATUALIZADO: ' · sem contato recente', NUNCA_CONECTADO: ' · ainda não conectado', REVOGADO: ' · revogado' };

export async function Dispositivos(session) {
  const body = el('div');
  const archived = el('input', { type: 'checkbox', name: 'arquivados' });
  let refresh;
  const editor = async (device = null) => {
    const collectors = (await apiFetch('/coletores').catch(() => [])).filter(c => c.estado !== 'REVOGADO' || c.id === device?.coletor_id);
    const tipo = input('tipo', 'Roteador, switch, servidor…', { value: device?.tipo || '', required: true, maxLength: 50 });
    const impact = impactFields(device, tipo);
    modal(device ? 'Editar dispositivo' : 'Cadastrar dispositivo', close => form([
    label('Nome', input('nome', 'Ex.: Switch do escritório', { value: device?.nome || '', required: true, maxLength: 100 })),
    label('Endereço IP', input('ip', 'IPv4 ou IPv6 do equipamento', { value: device?.ip || '', required: true, maxLength: 45, inputMode: 'url', autocapitalize: 'none', autocorrect: 'off', autoComplete: 'off', className: 'mono' })),
    label('Tipo', tipo),
    label('Localização', input('localizacao', 'Ex.: Sala de TI · Andar 2', { value: device?.localizacao || '', required: true, maxLength: 150 })),
    label('Origem da medição', select('coletor_id', [['', 'Worker local do servidor'], ...collectors.map(c => [c.id, `Coletor: ${c.nome}`])], device?.coletor_id || '')),
    impact.node,
    el('p', { className: 'muted full' }, `Empresa: ${session.empresa.nome_fantasia}. O estado de conexão é determinado pelo monitoramento. Em hospedagem na nuvem, dispositivos de rede privada precisam de um coletor instalado nessa rede.`)
  ], device ? 'Salvar alterações' : 'Cadastrar dispositivo', async data => {
    data.coletor_id = data.coletor_id ? Number(data.coletor_id) : null;
    Object.assign(data, impact.values());
    delete data.perda_opcao; delete data.perda_custom;
    await apiFetch(device ? `/dispositivos/${device.id}` : '/dispositivos', { method: device ? 'PUT' : 'POST', body: json(data) });
    close(); toast(device ? 'Dispositivo atualizado.' : 'Dispositivo cadastrado. Aguardando a primeira coleta.'); await refresh();
  }));
  };
  refresh = async () => {
    const devices = await apiFetch(`/dispositivos?arquivados=${archived.checked ? 1 : 0}`);
    body.replaceChildren(table(['Dispositivo', 'IP / Tipo', 'Localização', 'Conectividade', 'Última coleta', 'Ações'], devices.map(d => [
      el('div', {}, el('strong', {}, d.nome), d.arquivado_em ? el('small', { className: 'muted' }, 'Arquivado') : null),
      el('div', {}, el('span', { className: 'mono' }, d.ip), el('small', { className: 'muted' }, d.tipo)), d.localizacao,
      el('div', {}, badge(d.status), d.desatualizado && d.ultima_coleta ? el('small', { className: 'warning-text' }, 'Medição desatualizada') : null,
        d.erro_coleta ? el('small', { className: 'error-text' }, d.erro_coleta) : null,
        el('small', { className: d.coletor_estado && d.coletor_estado !== 'ATIVO' ? 'warning-text' : 'muted' },
          d.coletor ? `Coletor ${d.coletor}${COLLECTOR_NOTE[d.coletor_estado] || ''}` : 'Worker local')),
      el('div', {}, date(d.ultima_coleta), el('small', { className: 'muted' }, `${number(d.latencia_ms, ' ms')} · perda ${number(d.perda_pacotes_pct, '%')}`)),
      el('div', { className: 'actions compact' },
        button('Métricas', () => showMetrics(d), 'ghost'),
        !d.arquivado_em ? [button('Editar', () => editor(d).catch(e => toast(e.message, true)), 'ghost'),
          button('Coletar', async () => { try { const result = await apiFetch(`/dispositivos/${d.id}/coletas`, { method: 'POST', body: '{}' }); toast(result.mensagem); } catch(e) { toast(e.message,true); } }, 'ghost'),
          button('Arquivar', () => confirmAction('Arquivar dispositivo?', `“${d.nome}” deixará de ser monitorado. Métricas e ocorrências serão preservadas.`, async () => {
            await apiFetch(`/dispositivos/${d.id}`, { method: 'DELETE' }); toast('Dispositivo arquivado.'); await refresh();
          }, 'Arquivar'), 'ghost danger-text')]
          : button('Desarquivar', () => confirmAction('Desarquivar dispositivo?', `“${d.nome}” voltará a ser monitorado.`, async () => {
            await apiFetch(`/dispositivos/${d.id}/desarquivar`, { method: 'POST', body: '{}' });
            toast('Dispositivo desarquivado. Aguardando a primeira coleta.'); await refresh();
          }, 'Desarquivar', 'primary'), 'ghost'))
    ])));
  };
  archived.addEventListener('change', () => refresh().catch(e => toast(e.message,true)));
  const root = el('section', {}, pageHeader('Dispositivos', 'Inventário e conectividade da sua empresa.', button('Cadastrar dispositivo', () => editor().catch(e => toast(e.message, true)), 'primary')),
    el('div', { className: 'toolbar' }, el('label', { className: 'checkbox' }, archived, 'Incluir arquivados'), button('Atualizar', () => refresh().catch(e => toast(e.message,true)))), body);
  await refresh(); return root;
}

const LOSS = [['100', 'Para tudo', '100%'], ['50', 'Trabalha com dificuldade', '50%'], ['10', 'Quase não sente', '10%']];

// "Impacto no negócio": filled with the defaults for the type (from the API) until the person edits it.
export function impactFields(device, tipoInput) {
  let touched = Boolean(device && device.usuarios_dependentes !== null && device.usuarios_dependentes !== undefined);
  const users = input('usuarios_dependentes', 'Ex.: 10', { type: 'number', inputMode: 'numeric', min: 0, step: 1, value: device?.usuarios_dependentes ?? '' });
  const custom = input('perda_custom', '0 a 100', { type: 'number', inputMode: 'numeric', min: 0, max: 100, step: 1, 'aria-label': 'Perda de produtividade personalizada (%)' });
  const radio = value => el('input', { type: 'radio', name: 'perda_opcao', value });
  const options = el('fieldset', { className: 'choice-group full' }, el('legend', {}, 'Sem ele, a equipe…'),
    LOSS.map(([value, text, pct]) => el('label', { className: 'choice' }, radio(value), el('span', {}, text, el('small', { className: 'muted' }, pct)))),
    el('label', { className: 'choice' }, radio('custom'), el('span', {}, 'Personalizar', el('small', { className: 'muted' }, '% exato'))), custom);
  const revenue = input('receita_hora_dependente', 'Opcional · Ex.: 150,00', { inputMode: 'decimal', autoComplete: 'off', value: device?.receita_hora_dependente ? Number(device.receita_hora_dependente).toLocaleString('pt-BR', { minimumFractionDigits: 2 }) : '' });
  const usersHint = el('small', { className: 'muted' }), revenueHint = el('small', { className: 'muted' });
  const setLoss = pct => {
    const preset = LOSS.find(([v]) => Number(v) === Number(pct));
    options.querySelector(`[value="${preset ? preset[0] : 'custom'}"]`).checked = true;
    custom.value = preset ? '' : (pct ?? '');
    custom.hidden = Boolean(preset);
  };
  setLoss(device?.perda_produtividade_pct ?? 50);
  const apply = async () => {
    try {
      const d = await apiFetch(`/dispositivos/impacto-padrao?${new URLSearchParams({ tipo: tipoInput.value })}`);
      usersHint.textContent = d.regra_usuarios === 'SETOR' ? 'Informe quantas pessoas do setor dependem dele.' : d.dica;
      revenueHint.textContent = d.sugerir_receita ? 'Este tipo costuma gerar receita direta: informe quanto passa por ele por hora.' : '';
      if (touched) return;
      users.value = d.usuarios ?? '';
      setLoss(d.perda_pct);
    } catch { /* defaults are a convenience; the form still works without them */ }
  };
  let timer;
  tipoInput.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(apply, 300); });
  [users, custom, revenue].forEach(i => i.addEventListener('input', () => { touched = true; }));
  options.addEventListener('change', event => {
    touched = true;
    if (event.target.name !== 'perda_opcao') return;  // the custom % input also bubbles "change"
    custom.hidden = event.target.value !== 'custom';
    if (!custom.hidden) custom.focus();
  });
  apply();
  const node = el('fieldset', { className: 'impact-section full' }, el('legend', {}, 'Impacto no negócio'),
    el('p', { className: 'muted small' }, 'Usado para estimar o prejuízo das falhas. Os valores vêm do tipo do aparelho e podem ser ajustados.'),
    el('div', { className: 'form-grid' }, el('label', { className: 'field' }, el('span', {}, 'Quantas pessoas usam este aparelho?'), users, usersHint), options,
      el('label', { className: 'field' }, el('span', {}, 'Gera receita direta? (R$/hora, opcional)'), revenue, revenueHint)));
  return {
    node,
    values: () => {
      const choice = options.querySelector('[name=perda_opcao]:checked')?.value;
      return {
        usuarios_dependentes: users.value === '' ? null : Number(users.value),
        perda_produtividade_pct: choice === 'custom' ? (custom.value === '' ? null : Number(custom.value)) : Number(choice),
        receita_hora_dependente: moneyInput(revenue.value),
      };
    },
  };
}

async function showMetrics(d) {
  const body = el('div');
  const type = select('tipo', [['','Todas as métricas'],['latencia','Latência'],['perda_pacotes','Perda de pacotes'],['disponibilidade','Disponibilidade']]);
  const start = input('inicio','',{type:'date'}), end = input('fim','',{type:'date'});
  const paging = el('div',{className:'pagination'}); let page = 1;
  const load = async () => {
    const query = new URLSearchParams({ dispositivo_id:d.id,limite:100,pagina:page,tipo:type.value,inicio:start.value,fim:end.value });
    const result = await apiFetch(`/metricas?${query}`);
    const latency = !type.value || type.value==='latencia';
    const loss = !type.value || type.value==='perda_pacotes';
    const headings=['Data/hora',...(latency?['Latência']:[]),...(loss?['Perda']:[]), 'Respondeu','Pacotes','Estado'];
    body.replaceChildren(el('p',{className:'muted'},`${result.total} amostras no período. Página ${page}, até 100 em ordem cronológica.`), table(headings,result.items.map(m=>[
      date(m.coletada_em),...(latency?[number(m.latencia_ms,' ms')]:[]),...(loss?[number(m.perda_pacotes_pct,'%')]:[]),m.respondeu?'Sim':'Não',`${m.pacotes_recebidos}/${m.pacotes_enviados}`,badge(m.status)
    ])));
    paging.replaceChildren(button('Anterior',()=>{page--;load().catch(e=>toast(e.message,true));},'secondary',{disabled:page===1}),button('Próxima',()=>{page++;load().catch(e=>toast(e.message,true));},'secondary',{disabled:page*100>=result.total}));
  };
  modal(`Métricas · ${d.nome}`, el('div',{},el('div',{className:'filters'},label('Métrica',type),label('Início (UTC)',start),label('Fim (UTC)',end),button('Consultar',()=>{page=1;load().catch(e=>toast(e.message,true));},'primary')),body,paging));
  try { await load(); } catch(e) { body.textContent=e.message; }
}
