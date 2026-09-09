import { el, input, label, button, form, table, badge, modal, confirmAction, toast, date, number, pageHeader, select } from '../ui/dom.js';
import { apiFetch, json } from '../services/api.js';

export async function Dispositivos(session) {
  const body = el('div');
  const archived = el('input', { type: 'checkbox', name: 'arquivados' });
  let refresh;
  const editor = (device = null) => modal(device ? 'Editar dispositivo' : 'Cadastrar dispositivo', close => form([
    label('Nome', input('nome', 'Ex.: Switch do escritório', { value: device?.nome || '', required: true, maxLength: 100 })),
    label('Endereço IP', input('ip', '192.168.1.1', { value: device?.ip || '', required: true, maxLength: 45 })),
    label('Tipo', input('tipo', 'Roteador, switch, servidor…', { value: device?.tipo || '', required: true, maxLength: 50 })),
    label('Localização', input('localizacao', 'Ex.: Sala de TI · Andar 2', { value: device?.localizacao || '', required: true, maxLength: 150 })),
    el('p', { className: 'muted full' }, `Empresa: ${session.empresa.nome_fantasia}. O estado de conexão é determinado pelo monitoramento.`)
  ], device ? 'Salvar alterações' : 'Cadastrar dispositivo', async data => {
    await apiFetch(device ? `/dispositivos/${device.id}` : '/dispositivos', { method: device ? 'PUT' : 'POST', body: json(data) });
    close(); toast(device ? 'Dispositivo atualizado.' : 'Dispositivo cadastrado. Aguardando a primeira coleta.'); await refresh();
  }));
  refresh = async () => {
    const devices = await apiFetch(`/dispositivos?arquivados=${archived.checked ? 1 : 0}`);
    body.replaceChildren(table(['Dispositivo', 'IP / Tipo', 'Localização', 'Conectividade', 'Última coleta', 'Ações'], devices.map(d => [
      el('div', {}, el('strong', {}, d.nome), d.arquivado_em ? el('small', { className: 'muted' }, 'Arquivado') : null),
      el('div', {}, el('span', { className: 'mono' }, d.ip), el('small', { className: 'muted' }, d.tipo)), d.localizacao,
      el('div', {}, badge(d.status), d.desatualizado && d.ultima_coleta ? el('small', { className: 'warning-text' }, 'Medição desatualizada') : null,
        d.erro_coleta ? el('small', { className: 'error-text' }, d.erro_coleta) : null),
      el('div', {}, date(d.ultima_coleta), el('small', { className: 'muted' }, `${number(d.latencia_ms, ' ms')} · perda ${number(d.perda_pacotes_pct, '%')}`)),
      el('div', { className: 'actions compact' },
        button('Métricas', () => showMetrics(d), 'ghost'),
        !d.arquivado_em ? [button('Editar', () => editor(d), 'ghost'),
          button('Coletar', async () => { try { const result = await apiFetch(`/dispositivos/${d.id}/coletas`, { method: 'POST', body: '{}' }); toast(result.mensagem); } catch(e) { toast(e.message,true); } }, 'ghost'),
          button('Arquivar', () => confirmAction('Arquivar dispositivo?', `“${d.nome}” deixará de ser monitorado. Métricas e ocorrências serão preservadas.`, async () => {
            await apiFetch(`/dispositivos/${d.id}`, { method: 'DELETE' }); toast('Dispositivo arquivado.'); await refresh();
          }), 'ghost danger-text')] : null)
    ])));
  };
  archived.addEventListener('change', () => refresh().catch(e => toast(e.message,true)));
  const root = el('section', {}, pageHeader('Dispositivos', 'Inventário e conectividade da sua empresa.', button('Cadastrar dispositivo', () => editor(), 'primary')),
    el('div', { className: 'toolbar' }, el('label', { className: 'checkbox' }, archived, 'Incluir arquivados'), button('Atualizar', () => refresh().catch(e => toast(e.message,true)))), body);
  await refresh(); return root;
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
