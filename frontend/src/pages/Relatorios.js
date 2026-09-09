import { el,input,label,select,form,pageHeader,toast } from '../ui/dom.js';
import { apiFetch } from '../services/api.js';
export async function Relatorios(){
  const devices=await apiFetch('/dispositivos?arquivados=1');
  return el('section',{},pageHeader('Relatórios','Exporte o inventário, as medições e a análise das ocorrências.'),el('div',{className:'panel narrow'},
    el('h2',{},'Exportar dados da empresa'),el('p',{className:'muted'},'O download contém quatro arquivos CSV em um ZIP: dispositivos, métricas, falhas e diagnósticos. Inclui recomendações e impacto das ocorrências.'),
    form([label('Dispositivo',select('dispositivo_id',[['','Todos os dispositivos'],...devices.map(d=>[d.id,d.nome])])),
      label('Início (UTC)',input('inicio','',{type:'date'})),label('Fim (UTC)',input('fim','',{type:'date'})),
      el('p',{className:'muted full'},'Sem período informado, são consultados os últimos 30 dias. O inventário inclui arquivados. Ocorrências que se sobrepõem ao intervalo também são incluídas.')
    ],'Baixar relatório CSV',async data=>{
      const query=new URLSearchParams(data);
      const blob=await apiFetch(`/relatorios/exportar?${query}`,{download:true});
      const url=URL.createObjectURL(blob);
      const anchor=el('a',{href:url,download:`edgehealth-${new Date().toISOString().slice(0,10)}.zip`});
      document.body.append(anchor);anchor.click();anchor.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('Relatório gerado. Download iniciado.');
    })));
}
