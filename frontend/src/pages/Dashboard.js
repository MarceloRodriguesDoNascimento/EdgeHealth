import Chart from 'chart.js/auto';
import { el,label,input,select,button,pageHeader,badge,table,date,number,empty,params,toast } from '../ui/dom.js';
import { apiFetch } from '../services/api.js';

export async function Dashboard(onDispose) {
  const initial=await apiFetch('/dashboard');
  const device=select('dispositivo_id',[['','Selecione um dispositivo'],...initial.dispositivos.map(d=>[d.id,d.nome])],initial.dispositivo_id||'');
  const start=input('inicio','',{type:'date'}),end=input('fim','',{type:'date'});
  const cards=el('div',{className:'stats-grid'}),severity=el('div',{className:'severity-list'}),recent=el('div'),time=el('span',{className:'muted small'}),sampleInfo=el('p',{className:'muted small'});
  const latency=el('canvas',{'aria-label':'Histórico de latência',role:'img'}),loss=el('canvas',{'aria-label':'Histórico de perda de pacotes',role:'img'});
  let charts=[]; let stopped=false; let requestId=0;
  const draw=(data)=>{
    cards.replaceChildren(...[['Dispositivos',data.indicadores.total,'neutral'],['Online',data.indicadores.online,'good'],['Instáveis',data.indicadores.instaveis,'warn'],['Offline',data.indicadores.offline,'bad'],['Falhas abertas',data.indicadores.falhas_abertas,'blue']].map(([title,value,color])=>el('div',{className:`stat ${color}`},el('span',{},title),el('strong',{},value))));
    time.textContent=`Atualizado em ${date(data.atualizado_em)}`;
    sampleInfo.textContent=`${data.serie.length} de ${data.serie_total} amostras do dispositivo no período; no máximo as 500 mais recentes. ${data.indicadores.sem_coleta} sem coleta e ${data.indicadores.desatualizados} com dados ausentes ou desatualizados.`;
    severity.replaceChildren(...['BAIXA','MEDIA','ALTA','CRITICA'].map(level=>el('div',{className:'severity-row'},badge(level),el('strong',{},data.severidades[level]||0))));
    charts.forEach(c=>c.destroy());charts=[];
    for(const [canvas,key,title,color,max] of [[latency,'latencia_ms','Latência (ms)','#087f8c',undefined],[loss,'perda_pacotes_pct','Perda (%)','#365cdb',100]]){
      charts.push(new Chart(canvas,{type:'line',data:{labels:data.serie.map(m=>new Date(m.coletada_em).toLocaleTimeString('pt-BR')),datasets:[{label:title,data:data.serie.map(m=>m[key]),borderColor:color,backgroundColor:color+'12',fill:true,tension:0.2,pointRadius:data.serie.length<40?3:0,spanGaps:false}]},options:{responsive:true,maintainAspectRatio:false,animation:false,plugins:{legend:{display:false},tooltip:{callbacks:{title:items=>items.length?date(data.serie[items[0].dataIndex].coletada_em):''}}},scales:{x:{grid:{display:false},ticks:{maxTicksLimit:5,maxRotation:0}},y:{beginAtZero:true,max,grid:{color:'#e9edf3'}}}}}));
    }
    recent.replaceChildren(data.falhas_recentes.length?table(['Dispositivo','Ocorrência','Severidade','Início'],data.falhas_recentes.map(f=>[
      el('a',{href:`#falha/${f.id}`,className:'text-link'},f.dispositivo),badge(f.estado,f.estado==='ABERTA'?'INSTAVEL':'ONLINE'),badge(f.severidade),date(f.inicio)
    ])):empty('Nenhuma ocorrência registrada. Novas falhas aparecerão aqui.'));
  };
  const refresh=async()=>{const own=++requestId;try{const data=await apiFetch(`/dashboard?${params({dispositivo_id:device.value,inicio:start.value,fim:end.value})}`);if(!stopped&&own===requestId)draw(data);}catch(e){if(!stopped&&own===requestId)toast(e.message,true);}};
  const root=el('section',{},pageHeader('Visão da rede','Disponibilidade, desempenho e ocorrências.',el('div',{className:'actions'},time,button('Atualizar',refresh))),cards,
    el('div',{className:'section-heading'},el('h2',{},'Desempenho no tempo'),el('span',{className:'muted small'},'Sem resposta: latência permanece desconhecida')),
    el('div',{className:'filters'},label('Dispositivo',device),label('Início (UTC)',start),label('Fim (UTC)',end),button('Aplicar',refresh,'primary')),
    sampleInfo,el('div',{className:'chart-grid'},el('div',{className:'panel'},el('h3',{},'Latência'),el('div',{className:'chart-box'},latency)),el('div',{className:'panel'},el('h3',{},'Perda de pacotes'),el('div',{className:'chart-box'},loss))),
    el('div',{className:'bottom-grid'},el('div',{},el('div',{className:'section-heading'},el('h2',{},'Ocorrências recentes'),el('a',{href:'#historico',className:'text-link'},'Ver histórico')),recent),
      el('aside',{className:'panel'},el('h3',{},'Severidade das falhas abertas'),severity)));
  // The canvas must be attached before its responsive chart is initialized.
  setTimeout(()=>{if(!stopped&&requestId===0)draw(initial);},0);
  const timer=setInterval(refresh,15000);
  onDispose(()=>{stopped=true;clearInterval(timer);charts.forEach(c=>c.destroy());});
  return root;
}
