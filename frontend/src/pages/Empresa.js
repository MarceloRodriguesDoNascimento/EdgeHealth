import { el,input,label,form,pageHeader,toast,button,modal,brl,moneyInput } from '../ui/dom.js';
import { apiFetch,json } from '../services/api.js';

const DAYS=[[1,'Seg'],[2,'Ter'],[3,'Qua'],[4,'Qui'],[5,'Sex'],[6,'Sáb'],[7,'Dom']];
const fmt=(n,d=0)=>Number(n).toLocaleString('pt-BR',{minimumFractionDigits:d,maximumFractionDigits:2});

const HINT='Informe o salário médio para ver o custo por hora estimado.';

// The server computes the cost per hour (same formula used everywhere); the page only shows the answer.
export function costPreview(){
  let seq=0,timer;
  return (salary,factor,hours,show)=>{
    clearTimeout(timer);const mine=++seq;
    const salario_medio=moneyInput(salary);
    if(!(Number(salario_medio)>0)){show(HINT);return Promise.resolve();}
    return new Promise(resolve=>{timer=setTimeout(async()=>{
      try{
        const r=await apiFetch('/empresa/custos/previa',{method:'POST',body:json({salario_medio,
          fator_encargos:moneyInput(factor),horas_mes:hours===''?null:Number(hours)})});
        if(mine===seq)show(`Custo por hora estimado: ${brl(r.custo_hora)} (${fmt(r.salario_medio)} × ${fmt(r.fator_encargos,1)} ÷ ${fmt(r.horas_mes)})`);
      }catch(e){if(mine===seq)show(e.message);}
      resolve();
    },300);});
  };
}

export async function Empresa(session) {
  const company=await apiFetch('/empresa');
  const admin=session.usuario.papel==='ADMIN';
  const data=admin?el('div',{className:'panel narrow'},form([
    label('Nome da empresa',input('nome_fantasia','',{required:true,value:company.nome_fantasia,maxLength:150})),
    label('CNPJ',input('cnpj','',{required:true,value:company.cnpj,maxLength:18,autoComplete:'off',autocapitalize:'characters',autocorrect:'off'})),
    label('E-mail de contato',input('email','',{type:'email',value:company.email||'',autoComplete:'email'})),
    label('Telefone',input('telefone','',{type:'tel',value:company.telefone||'',maxLength:30,autoComplete:'tel'}))
  ],'Salvar empresa',async data=>{ const updated=await apiFetch('/empresa',{method:'PUT',body:json(data)}); session.empresa=updated; toast('Dados da empresa atualizados.'); document.querySelector('#company-name').textContent=updated.nome_fantasia; }))
    :el('div',{className:'panel narrow'},el('dl',{className:'facts'},...[['Nome',company.nome_fantasia],['CNPJ',company.cnpj],['E-mail',company.email||'—'],['Telefone',company.telefone||'—']].flatMap(([k,v])=>[el('dt',{},k),el('dd',{},v)])));
  return el('section',{},pageHeader('Empresa','Dados da organização e custos usados na estimativa de prejuízo.'),data,costsPanel(company,session,admin));
}

function costsPanel(company,session,admin){
  const c=company.custos;
  const intro=el('p',{className:'muted'},'Usados para estimar o prejuízo financeiro das falhas: horas de expediente × pessoas afetadas × custo por hora. O resultado é sempre uma estimativa.');
  if(!admin){
    return el('div',{className:'panel narrow',id:'custos'},el('h2',{},'Custos'),intro,c.configurado?el('dl',{className:'facts'},...[
      ['Custo por hora estimado',brl(c.custo_hora)],['Salário médio',brl(c.salario_medio)],['Fator de encargos',fmt(c.fator_encargos,1)],
      ['Funcionários',c.total_funcionarios??'—'],['Expediente',`${c.expediente.dias.map(d=>DAYS[d-1][1]).join(', ')} · ${c.expediente.inicio}–${c.expediente.fim}`]
    ].flatMap(([k,v])=>[el('dt',{},k),el('dd',{},String(v))])):el('p',{},'Os custos ainda não foram configurados. Peça a um administrador da empresa.'));
  }
  const salary=input('salario_medio','Ex.: 3.000,00',{value:c.salario_medio?fmt(c.salario_medio,2):'',inputMode:'decimal',autoComplete:'off',required:true});
  const people=input('total_funcionarios','Ex.: 40',{type:'number',inputMode:'numeric',min:0,step:1,value:c.total_funcionarios??''});
  const factor=input('fator_encargos','1,7',{value:fmt(c.fator_encargos,1),inputMode:'decimal',autoComplete:'off'});
  const hours=input('horas_mes','220',{type:'number',inputMode:'numeric',min:1,max:744,value:c.horas_mes});
  const zone=input('fuso','America/Sao_Paulo',{value:c.fuso,autoComplete:'off',autocapitalize:'none'});
  const start=input('inicio','',{type:'time',value:c.expediente.inicio,required:true}),end=input('fim','',{type:'time',value:c.expediente.fim,required:true});
  const days=el('fieldset',{className:'day-picker full'},el('legend',{},'Dias de expediente'),
    DAYS.map(([d,name])=>el('label',{className:'checkbox'},el('input',{type:'checkbox',name:'dias',value:String(d),checked:c.expediente.dias.includes(d)}),name)));
  const preview=el('p',{className:'cost-preview full',role:'status','aria-live':'polite'});
  const ask=costPreview();
  const update=()=>ask(salary.value,factor.value,hours.value,text=>{preview.textContent=text;});
  [salary,factor,hours].forEach(i=>i.addEventListener('input',update));update();
  const node=form([
    label('Salário médio mensal (R$)',salary),label('Total de funcionários',people),
    days,label('Início do expediente',start),label('Fim do expediente',end),
    el('details',{className:'full'},el('summary',{},'Avançado'),el('div',{className:'form-grid'},
      label('Fator de encargos (salário → custo total)',factor),label('Horas trabalhadas por mês',hours),label('Fuso horário',zone),
      el('p',{className:'muted small full'},'O fator 1,7 cobre encargos e benefícios típicos (INSS, FGTS, férias, 13º). 220 h é a jornada mensal de 44 h semanais.'))),
    preview
  ],'Salvar custos',async(_,formNode)=>{
    const body={salario_medio:moneyInput(salary.value),total_funcionarios:people.value===''?null:Number(people.value),
      fator_encargos:moneyInput(factor.value)||'1.7',horas_mes:Number(hours.value)||220,fuso:zone.value.trim(),
      expediente:{dias:[...formNode.querySelectorAll('[name=dias]:checked')].map(x=>Number(x.value)),inicio:start.value,fim:end.value}};
    const updated=await apiFetch('/empresa/custos',{method:'PUT',body:json(body)});
    session.empresa=updated;toast(`Custos salvos. Custo por hora estimado: ${brl(updated.custos.custo_hora)}.`);
  });
  return el('div',{className:'panel narrow',id:'custos'},el('h2',{},'Custos'),intro,node);
}

// Offered once to the administrator right after creating the company; "skip" is remembered.
export function costAssistant(session,onDone=()=>{}){
  let decided=false;
  const salary=input('salario_medio','Ex.: 3.000,00',{inputMode:'decimal',autoComplete:'off',required:true});
  const people=input('total_funcionarios','Ex.: 40',{type:'number',inputMode:'numeric',min:0,step:1,required:true});
  const skip=async()=>{if(decided)return;decided=true;try{session.empresa=await apiFetch('/empresa/custos/pular',{method:'POST',body:'{}'});}catch(e){toast(e.message,true);}onDone();};
  const dialog=modal('Quer estimar o custo das falhas?',close=>el('div',{},
    el('p',{},'Com o salário médio e o número de funcionários, o EdgeHealth estima quanto cada falha custou em horas paradas. Você pode ajustar tudo depois em Empresa → Custos.'),
    form([label('Salário médio mensal (R$)',salary),label('Total de funcionários',people)],'Salvar',async()=>{
      session.empresa=await apiFetch('/empresa/custos',{method:'PUT',body:json({salario_medio:moneyInput(salary.value),total_funcionarios:Number(people.value)})});
      decided=true;close();toast(`Custos salvos. Custo por hora estimado: ${brl(session.empresa.custos.custo_hora)}.`);onDone();
    }),
    el('div',{className:'actions'},button('Pular, faço depois',()=>{skip();close();},'link'))));
  dialog.addEventListener('close',()=>skip());  // Esc or "Fechar" also count as "later": never nag again
  return dialog;
}
