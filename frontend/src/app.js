import './styles.css';
import { apiFetch } from './services/api.js';
import { el,button,toast } from './ui/dom.js';
import { Login } from './pages/Login.js';
import { Dashboard } from './pages/Dashboard.js';
import { Dispositivos } from './pages/Dispositivos.js';
import { Empresa } from './pages/Empresa.js';
import { Usuarios } from './pages/Usuarios.js';
import { Historico } from './pages/Historico.js';
import { Falha } from './pages/Falha.js';
import { Relatorios } from './pages/Relatorios.js';

const app=document.querySelector('#app');
let session=null,cleanup=()=>{},generation=0;
function signedIn(data){session=data;window.location.hash='dashboard';shell();navigate();}
function signedOut(){session=null;cleanup();generation++;app.replaceChildren(Login(signedIn));}
function shell(){
  const links=[['dashboard','Visão da rede','◫'],['dispositivos','Dispositivos','▤'],['historico','Histórico de falhas','◷'],['relatorios','Relatórios','↓'],...(session.usuario.papel==='ADMIN'?[['empresa','Empresa','▦'],['usuarios','Equipe','◎']]:[])];
  app.replaceChildren(el('div',{className:'app-layout'},
    el('aside',{className:'sidebar'},el('a',{href:'#dashboard',className:'brand'},el('span',{className:'brand-mark'},'E'),'EdgeHealth'),
      el('p',{className:'nav-caption'},'ESPAÇO DA EMPRESA'),el('nav',{'aria-label':'Navegação principal'},links.map(([key,text,icon])=>el('a',{href:`#${key}`,dataset:{route:key}},el('span',{'aria-hidden':'true'},icon),text))),
      el('div',{className:'sidebar-bottom'},el('span',{className:'small'},'Conectividade com contexto'),el('strong',{},'EdgeHealth / MVP'))),
    el('div',{className:'workspace'},el('header',{className:'topbar'},el('div',{},el('span',{className:'muted small'},'EMPRESA'),el('strong',{id:'company-name'},session.empresa.nome_fantasia)),
      el('div',{className:'actions'},el('span',{className:'user-name'},session.usuario.nome),button('Sair',async()=>{try{await apiFetch('/auth/logout',{method:'POST',body:'{}'});signedOut();}catch(e){if(e.status===401)signedOut();else toast(e.message,true);}},'ghost'))),el('main',{id:'content',tabIndex:-1}))))
}
async function navigate(){
  if(!session)return;
  cleanup();cleanup=()=>{};
  const own=++generation;
  const page=(window.location.hash||'#dashboard').slice(1);
  document.querySelectorAll('[data-route]').forEach(a=>{a.classList.toggle('active',a.dataset.route===page);a.setAttribute('aria-current',a.dataset.route===page?'page':'false');});
  const main=document.querySelector('#content');main.replaceChildren(el('div',{className:'loading',role:'status'},'Carregando…'));
  let disposable=()=>{};
  try{
    let view;
    if(page==='dashboard')view=await Dashboard(fn=>{disposable=fn;});
    else if(page==='dispositivos')view=await Dispositivos(session);
    else if(page==='historico')view=await Historico();
    else if(/^falha\/\d+$/.test(page))view=await Falha(Number(page.split('/')[1]));
    else if(page==='empresa')view=await Empresa(session);
    else if(page==='usuarios')view=await Usuarios(session);
    else if(page==='relatorios')view=await Relatorios();
    else{window.location.hash='dashboard';return;}
    if(own!==generation){disposable();return;}
    cleanup=disposable;main.replaceChildren(view);
  }catch(e){
    disposable();
    if(own===generation)main.replaceChildren(el('div',{className:'panel'},el('h1',{},'Não foi possível carregar'),el('p',{role:'alert'},e.message),button('Tentar novamente',navigate)));
  }
}
window.addEventListener('hashchange',navigate);
window.addEventListener('session-expired',()=>{if(session){signedOut();toast('Sua sessão expirou. Entre novamente.',true);}});
apiFetch('/auth/me').then(data=>{session=data;shell();navigate();}).catch(error=>{signedOut();if(error.status!==401)toast(error.message,true);});
