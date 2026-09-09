import { el,input,label,form,pageHeader,toast } from '../ui/dom.js';
import { apiFetch,json } from '../services/api.js';
export async function Empresa(session) {
  const company=await apiFetch('/empresa');
  return el('section',{},pageHeader('Empresa','Dados da organização e vínculo da equipe.'),el('div',{className:'panel narrow'},form([
    label('Nome da empresa',input('nome_fantasia','',{required:true,value:company.nome_fantasia,maxLength:150})),
    label('CNPJ',input('cnpj','',{required:true,value:company.cnpj,maxLength:18})),
    label('E-mail de contato',input('email','',{type:'email',value:company.email||''})),
    label('Telefone',input('telefone','',{value:company.telefone||'',maxLength:30}))
  ],'Salvar empresa',async data=>{ const updated=await apiFetch('/empresa',{method:'PUT',body:json(data)}); session.empresa=updated; toast('Dados da empresa atualizados.'); document.querySelector('#company-name').textContent=updated.nome_fantasia; })));
}
