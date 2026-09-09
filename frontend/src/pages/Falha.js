import { el,input,label,form,pageHeader,button,badge,date,duration,number,table,toast,empty } from '../ui/dom.js';
import { apiFetch,json } from '../services/api.js';
export async function Falha(id){
  const root=el('section');
  const load=async()=>{
    const f=await apiFetch(`/falhas/${id}`);
    const diag=f.diagnostico;
    const causes=diag?.causas||[];
    const impact=form([
      label('Usuários afetados (estimativa)',input('usuarios_afetados','Não informado',{type:'number',min:0,max:1000000,step:1,required:true,value:f.impacto?.usuarios_afetados??''})),
      label('Origem da estimativa / observação',el('textarea',{name:'observacao',rows:3,maxLength:500,value:f.impacto?.observacao||'',placeholder:'Ex.: quantidade informada pelo responsável do setor'}))
    ],'Salvar impacto',async data=>{
      await apiFetch(`/falhas/${id}/impacto`,{method:'PUT',body:json({...data,usuarios_afetados:Number(data.usuarios_afetados)})});toast('Impacto atualizado. Severidade recalculada.');await load();
    });
    const timeline=el('dl',{className:'facts'},...[
      ['Início',date(f.inicio)],['Fim',date(f.fim)],['Duração da ocorrência',duration(f.duracao_segundos)],['Última observação',date(f.ultima_observacao)],['Localização',f.localizacao],['Encerramento',f.encerramento||'Ocorrência aberta']
    ].flatMap(([k,v])=>[el('dt',{},k),el('dd',{},v)]));
    const severity=el('div',{className:'panel'},el('h2',{},'Severidade'),badge(f.severidade),el('ul',{className:'reason-list'},(f.justificativa?.motivos||[]).map(m=>el('li',{},m))),el('p',{className:'muted small'},`Recalculada em ${date(f.justificativa?.calculada_em)}`));
    const analysis=el('div',{className:'panel'},el('div',{className:'section-heading'},el('h2',{},'Diagnóstico lógico'),badge(diag?.estado==='DISPONIVEL'?'Análise disponível':diag?'Evidência insuficiente':'Aguardando análise',diag?.estado==='DISPONIVEL'?'ONLINE':'SEM_COLETA')),
      el('p',{},diag?.descricao||'A análise será apresentada após o processamento da coleta.'),
      causes.length?el('ul',{className:'cause-list'},causes.map(c=>el('li',{},el('strong',{},c.regra),el('p',{},c.descricao)))):empty('Não há evidências suficientes para determinar uma causa provável.'),
      el('p',{className:'muted small'},diag?`Análise em ${date(diag.analisado_em)}. Regras ${diag.versao_regras}. Hipóteses a verificar pela equipe.`:''));
    const recs=el('div',{className:'panel'},el('h2',{},'Recomendações'),diag?.recomendacoes?.length?el('ol',{className:'recommendations'},diag.recomendacoes.map(r=>el('li',{},el('strong',{},r.titulo),el('p',{},r.acao)))):empty('Nenhuma recomendação associada sem evidência suficiente.'));
    const metrics=diag?.evidencias?.amostras||[];
    const evidence=el('div',{className:'panel'},el('h2',{},'Evidências da análise'),
      el('p',{className:'muted'},`${diag?.evidencias?.outros_dispositivos?.length||0} outros dispositivos observados · ${diag?.evidencias?.ocorrencias_anteriores?.length||0} ocorrências anteriores consideradas`),
      table(['Coleta','Estado','Latência','Perda'],metrics.map(m=>[date(m.coletada_em),badge(m.status),number(m.latencia_ms,' ms'),number(m.perda_pacotes_pct,'%')])),
      diag?el('details',{},el('summary',{},'Ver evidências completas'),el('pre',{className:'evidence-json'},JSON.stringify(diag.evidencias,null,2))):null);
    root.replaceChildren(el('a',{href:'#historico',className:'text-link'},'← Voltar ao histórico'),pageHeader(`Ocorrência #${f.id}`,`${f.dispositivo} · ${f.ip}`,button('Atualizar',()=>load().catch(e=>toast(e.message,true)))),
      el('div',{className:'actions'},badge(f.estado,f.estado==='ABERTA'?'INSTAVEL':'ONLINE'),badge(f.tipo,'SEM_COLETA')),
      el('div',{className:'detail-grid'},el('div',{className:'panel'},el('h2',{},f.dispositivo),el('p',{},f.descricao),timeline),severity),
      analysis,recs,el('div',{className:'panel'},el('h2',{},'Impacto operacional'),el('p',{className:'muted'},f.impacto?.origem==='INFORMADO_PELO_USUARIO'?'Estimativa informada pela equipe. A duração é calculada automaticamente.':'Usuários afetados ainda não informados. A duração é calculada automaticamente.'),impact),evidence);
  };
  await load();return root;
}
