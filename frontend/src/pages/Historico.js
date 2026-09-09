import { el,input,label,select,button,pageHeader,table,badge,date,duration,params,toast } from '../ui/dom.js';
import { apiFetch } from '../services/api.js';
export async function Historico(){
  const devices=await apiFetch('/dispositivos?arquivados=1');
  const device=select('dispositivo_id',[['','Todos os dispositivos'],...devices.map(d=>[d.id,d.nome])]);
  const state=select('estado',[['','Todas'],['ABERTA','Abertas'],['ENCERRADA','Encerradas']]);
  const severity=select('severidade',[['','Todas'],...['BAIXA','MEDIA','ALTA','CRITICA'].map(x=>[x,x])]);
  const start=input('inicio','',{type:'date'}),end=input('fim','',{type:'date'});
  const body=el('div'),paging=el('div',{className:'pagination'});let page=1;
  const load=async()=>{
    const result=await apiFetch(`/falhas?${params({dispositivo_id:device.value,estado:state.value,severidade:severity.value,inicio:start.value,fim:end.value,pagina:page,limite:25})}`);
    body.replaceChildren(table(['Dispositivo','Tipo','Situação','Severidade','Início','Duração'],result.items.map(f=>[
      el('a',{href:`#falha/${f.id}`,className:'text-link'},f.dispositivo),f.tipo,badge(f.estado,f.estado==='ABERTA'?'INSTAVEL':'ONLINE'),badge(f.severidade),date(f.inicio),duration(f.duracao_segundos)
    ])));
    paging.replaceChildren(el('span',{className:'muted'},`${result.total} ocorrências · Página ${page}`),el('div',{className:'actions'},button('Anterior',()=>{page--;load().catch(e=>toast(e.message,true));},'secondary',{disabled:page===1}),button('Próxima',()=>{page++;load().catch(e=>toast(e.message,true));},'secondary',{disabled:page*25>=result.total})));
  };
  const root=el('section',{},pageHeader('Histórico de falhas','Investigue ocorrências abertas e encerradas, incluindo dispositivos arquivados.'),
    el('div',{className:'filters'},label('Dispositivo',device),label('Situação',state),label('Severidade',severity),label('Início (UTC)',start),label('Fim (UTC)',end),button('Filtrar',()=>{page=1;load().catch(e=>toast(e.message,true));},'primary')),body,paging);
  await load();return root;
}
