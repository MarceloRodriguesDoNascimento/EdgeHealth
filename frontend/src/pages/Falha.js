import { el,input,label,form,pageHeader,button,badge,date,duration,number,table,toast,empty,brl,moneyInput,port,human } from '../ui/dom.js';
import { apiFetch,json } from '../services/api.js';
export async function Falha(id){
  const root=el('section');
  const load=async()=>{
    const f=await apiFetch(`/falhas/${id}`);
    const diag=f.diagnostico;
    const causes=diag?.causas||[];
    const impact=form([
      label('Usuários afetados (estimativa)',input('usuarios_afetados','Padrão do dispositivo',{type:'number',inputMode:'numeric',min:0,max:1000000,step:1,value:f.impacto?.usuarios_afetados??''})),
      label('Custos diretos (R$): técnico, peças, multas',input('custos_diretos','Ex.: 250,00',{inputMode:'decimal',autoComplete:'off',value:f.impacto?.custos_diretos?Number(f.impacto.custos_diretos).toLocaleString('pt-BR',{minimumFractionDigits:2}):''})),
      label('Origem da estimativa / observação',el('textarea',{name:'observacao',rows:3,maxLength:500,value:f.impacto?.observacao||'',placeholder:'Ex.: quantidade informada pelo responsável do setor'}))
    ],'Salvar impacto',async data=>{
      await apiFetch(`/falhas/${id}/impacto`,{method:'PUT',body:json({observacao:data.observacao,usuarios_afetados:data.usuarios_afetados===''?null:Number(data.usuarios_afetados),custos_diretos:moneyInput(data.custos_diretos)})});
      toast('Impacto atualizado. Severidade e prejuízo recalculados.');await load();
    });
    const facts=el('dl',{className:'facts'},...[['Localização',f.localizacao],['Encerramento',f.encerramento?human(f.encerramento):'Ocorrência aberta']].flatMap(([k,v])=>[el('dt',{},k),el('dd',{},v)]));
    const timeline=el('div',{className:'panel'},el('h2',{},'Linha do tempo'),el('ol',{className:'timeline'},
      el('li',{},el('strong',{},'Início'),el('span',{},date(f.inicio))),
      el('li',{},el('strong',{},'Última observação'),el('span',{},date(f.ultima_observacao))),
      f.fim?el('li',{className:'done'},el('strong',{},'Fim'),el('span',{},date(f.fim))):el('li',{className:'open'},el('strong',{},'Em andamento'),el('span',{},'Ainda sem recuperação'))),
      facts);
    const severity=el('div',{className:'panel'},el('h2',{},'Por que essa severidade'),el('ul',{className:'reason-list'},(f.justificativa?.motivos||[]).map(m=>el('li',{},m))),el('p',{className:'muted small'},`Recalculada em ${date(f.justificativa?.calculada_em)}`));
    const analysis=el('div',{className:'panel'},el('div',{className:'section-heading'},el('h2',{},'Diagnóstico lógico'),badge(diag?.estado==='DISPONIVEL'?'Análise disponível':diag?'Evidência insuficiente':'Aguardando análise',diag?.estado==='DISPONIVEL'?'ONLINE':'SEM_COLETA')),
      el('p',{},diag?.descricao||'A análise será apresentada após o processamento da coleta.'),
      causes.length?el('ul',{className:'cause-list'},causes.map(c=>el('li',{},el('strong',{},human(c.regra)),el('p',{},c.descricao)))):empty('Não há evidências suficientes para determinar uma causa provável.'),
      el('p',{className:'muted small'},diag?`Análise em ${date(diag.analisado_em)}. Regras ${diag.versao_regras}. Hipóteses a verificar pela equipe.`:''));
    const recs=el('div',{className:'panel'},el('h2',{},'Recomendações'),diag?.recomendacoes?.length?el('ol',{className:'recommendations'},diag.recomendacoes.map(r=>el('li',{},el('strong',{},r.titulo),el('p',{},r.acao)))):empty('Nenhuma recomendação associada sem evidência suficiente.'));
    const metrics=diag?.evidencias?.amostras||[];
    const evidence=el('details',{className:'panel evidence'},el('summary',{},`Ver as ${metrics.length} medições usadas na análise`),
      el('p',{className:'muted'},`${diag?.evidencias?.outros_dispositivos?.length||0} outros dispositivos observados. ${diag?.evidencias?.ocorrencias_anteriores?.length||0} ocorrências anteriores consideradas.`),
      table(['Coleta','Estado','Latência','Perda'],metrics.map(m=>[date(m.coletada_em),badge(m.status),number(m.latencia_ms,' ms'),number(m.perda_pacotes_pct,'%')])),
      diag?el('details',{},el('summary',{},'Ver dados completos'),el('pre',{className:'evidence-json'},JSON.stringify(diag.evidencias,null,2))):null);
    const open=f.estado==='ABERTA',down=f.tipo==='INDISPONIBILIDADE';
    const head=el('div',{className:'faceplate incident-head'},
      el('div',{className:'incident-title'},el('div',{className:'ports','aria-hidden':'true'},port(open?(down?'OFFLINE':'INSTAVEL'):'ONLINE')),el('h2',{},incidentSummary(f))),
      el('dl',{className:'incident-facts'},...[['Severidade',badge(f.severidade)],['Situação',badge(f.estado,open?'INSTAVEL':'ONLINE')],['Duração',duration(f.duracao_segundos)],['Prejuízo estimado',f.prejuizo?.configurado?brl(f.prejuizo.valor):'Não configurado']].flatMap(([k,v])=>[el('div',{},el('dt',{},k),el('dd',{},v))])));
    root.replaceChildren(el('a',{href:'#historico',className:'text-link'},'← Voltar ao histórico'),pageHeader(`Ocorrência #${f.id}`,`${f.descricao} IP ${f.ip}.`,button('Atualizar',()=>load().catch(e=>toast(e.message,true)))),head,
      el('div',{className:'incident-grid'},
        el('div',{},analysis,recs,aiPanel(f,()=>apiFetch(`/falhas/${id}/explicacao-ia`,{method:'POST',body:'{}'})),evidence),
        el('aside',{className:'incident-side'},timeline,lossPanel(f.prejuizo),el('div',{className:'panel'},el('h2',{},'Impacto operacional'),el('p',{className:'muted small'},f.impacto?.origem==='INFORMADO_PELO_USUARIO'?'Estimativa informada pela equipe. A duração é calculada automaticamente.':'Usuários afetados ainda não informados. A duração é calculada automaticamente.'),impact),severity)));
  };
  await load();return root;
}

// The incident in one sentence: what is wrong, on which device, for how long.
export function incidentSummary(f){
  const time=duration(f.duracao_segundos),state=f.tipo==='INDISPONIBILIDADE'?'offline':'instável';
  return f.estado==='ABERTA'?`${f.dispositivo} está ${state} há ${time}.`:`${f.dispositivo} ficou ${state} por ${time}.`;
}

// Financial loss estimate: always the open calculation next to the value, never a bare number.
export function lossPanel(p){
  const root=el('div',{className:'panel loss-panel'},el('h2',{},'Prejuízo estimado'));
  if(!p||!p.configurado){
    root.append(el('p',{},p?.mensagem||'Configure os custos da empresa para ver a estimativa.'),el('a',{href:'#empresa',className:'text-link'},'Configurar custos da empresa'));
    return root;
  }
  root.append(el('p',{className:'money-hero'},brl(p.valor),p.em_andamento?el('span',{className:'badge INSTAVEL'},'em andamento'):null),
    el('p',{className:'loss-formula'},p.conta),
    el('p',{className:'muted small'},`${p.detalhe.horas_expediente.replace('.',',')} h de expediente dentro da falha · pessoas: ${p.detalhe.origem_pessoas}${p.em_andamento?' · parcial até agora':''}.`));
  if(p.detalhe.pessoas===0)root.append(el('p',{className:'warning-text small'},'Nenhuma pessoa considerada: informe quantas pessoas usam este aparelho em Dispositivos → Editar, ou os usuários afetados no Impacto operacional abaixo.'));
  if(p.grupo)root.append(el('div',{className:'loss-group'},el('strong',{},`Total do grupo compartilhado: ${brl(p.grupo.valor)}`),el('p',{className:'small'},p.grupo.explicacao)));
  root.append(el('p',{className:'muted small'},p.aviso));
  return root;
}

// Plain-language explanation by the AI (Gemini) from the diagnosis the system already computed.
// `explain` returns the API answer; injected so the panel can be tested without the network.
export function aiPanel(f,explain){
  const available=Boolean(f.ia_disponivel);
  const output=el('div',{className:'ai-output','aria-live':'polite'});
  const trigger=button('Explicar com IA',async()=>{
    trigger.disabled=true;trigger.textContent='Gerando explicação…';output.setAttribute('aria-busy','true');
    output.replaceChildren(el('p',{className:'muted small'},'A IA está lendo o diagnóstico desta ocorrência…'));
    try{
      const r=await explain();
      output.replaceChildren(...r.texto.split(/\n+/).map(p=>p.trim()).filter(Boolean).map(p=>el('p',{},p)),
        el('p',{className:'ai-warning small'},r.aviso));
    }catch(e){
      output.replaceChildren(el('p',{className:'error-text',role:'alert'},e.message));
    }finally{
      trigger.disabled=false;trigger.textContent='Explicar com IA';output.removeAttribute('aria-busy');
    }
  },'secondary',{disabled:!available,title:available?'':'IA não configurada neste servidor','aria-describedby':'ai-hint'});
  return el('div',{className:'panel ai-panel'},
    el('div',{className:'section-heading'},el('h2',{},'Explicação com IA'),trigger),
    el('p',{className:'muted small',id:'ai-hint'},available
      ?'Gera um resumo em linguagem simples para gestores: o que aconteceu, o impacto provável e os próximos passos. Envia à IA somente dados técnicos da ocorrência, nunca nomes, e-mails, CNPJ ou IP.'
      :'IA não configurada neste servidor.'),
    output);
}
