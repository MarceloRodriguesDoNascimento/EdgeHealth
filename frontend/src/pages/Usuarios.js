import { el,input,label,form,pageHeader,toast,button,modal,table,badge,select,confirmAction } from '../ui/dom.js';
import { apiFetch,json } from '../services/api.js';
export async function Usuarios(session) {
  const body=el('div'); let load;
  const editor=(user=null)=>modal(user?'Editar usuário':'Cadastrar usuário',close=>form([
    label('Nome',input('nome','Nome completo',{required:true,maxLength:100,value:user?.nome||''})),
    label('E-mail',input('email','nome@empresa.com.br',{type:'email',autoComplete:'off',required:true,value:user?.email||''})),
    label(user?'Nova senha (opcional)':'Senha',input('senha','Pelo menos 10 caracteres',{type:'password',required:!user,minLength:10,maxLength:128,autoComplete:'new-password'})),
    label('Permissão',select('papel',[['TECNICO','Técnico'],['ADMIN','Administrador']],user?.papel||'TECNICO')),
    el('p',{className:'muted full'},'A conta será vinculada à sua empresa. Alterações de senha ou permissão encerram as sessões dessa conta.')
  ],user?'Salvar usuário':'Cadastrar usuário',async data=>{
    if(user&&!data.senha) delete data.senha;
    if(user&&user.papel===data.papel) delete data.papel;
    await apiFetch(user?`/usuarios/${user.id}`:'/usuarios',{method:user?'PUT':'POST',body:json(data)});
    close();toast('Usuário salvo.');await load();
  }));
  load=async()=>{
    const users=await apiFetch('/usuarios');
    body.replaceChildren(table(['Nome','E-mail','Permissão','Situação','Ações'],users.map(u=>[u.nome,u.email,u.papel,badge(u.ativo?'Ativo':'Desativado',u.ativo?'ONLINE':'SEM_COLETA'),
      el('div',{className:'actions'},button('Editar',()=>editor(u),'ghost'),u.id!==session.usuario.id?button(u.ativo?'Desativar':'Ativar',()=>confirmAction('Alterar acesso?',`${u.nome} terá seu acesso ${u.ativo?'desativado':'ativado'}.`,async()=>{
        await apiFetch(`/usuarios/${u.id}`,{method:'PUT',body:json({ativo:!u.ativo})});toast('Acesso atualizado.');await load();
      }),'ghost'):null)])));
  };
  await load(); return el('section',{},pageHeader('Equipe','Gerencie as contas que acessam a sua empresa.',button('Cadastrar usuário',()=>editor(),'primary')),body);
}
