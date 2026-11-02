import '@fontsource-variable/archivo/wdth.css';
import './styles.css';
import { apiFetch } from './services/api.js';
import { el,button,toast,confirmAction,brandLogo,icon } from './ui/dom.js';
import { Login, TermsPending } from './pages/Login.js';
import { Coletores } from './pages/Coletores.js';
import { Dashboard } from './pages/Dashboard.js';
import { Dispositivos } from './pages/Dispositivos.js';
import { Empresa, costAssistant } from './pages/Empresa.js';
import { Usuarios } from './pages/Usuarios.js';
import { Historico } from './pages/Historico.js';
import { Falha } from './pages/Falha.js';
import { Relatorios } from './pages/Relatorios.js';

const app=document.querySelector('#app');
let session=null,cleanup=()=>{},generation=0;
// A failed logout keeps the dialog open and shows the error; an already-expired session just signs out.
async function endSession(){try{await apiFetch('/auth/logout',{method:'POST',body:'{}'});}catch(e){if(e.status!==401)throw e;}signedOut();}
const logout=()=>confirmAction('Sair do EdgeHealth?','Sua sessão será encerrada neste navegador.',endSession,'Sair');
function enter(data){
  session=data;
  if(session.usuario.termos_pendentes){app.replaceChildren(TermsPending(session,enter,logout));return;}
  shell();navigate();
  // Optional cost assistant, offered once to the administrator (skipping is remembered).
  const c=session.empresa.custos;
  if(session.usuario.papel==='ADMIN'&&c&&!c.configurado&&!c.assistente)costAssistant(session);
}
function signedIn(data){window.location.hash='dashboard';enter(data);}
function signedOut(){session=null;cleanup();generation++;app.replaceChildren(Login(signedIn));}
function shell(){
  const links=[['dashboard','Visão da rede','pulse'],['dispositivos','Dispositivos','server'],['historico','Histórico de falhas','clock'],['relatorios','Relatórios','download'],['empresa','Empresa','building'],...(session.usuario.papel==='ADMIN'?[['coletores','Coletores','antenna'],['usuarios','Equipe','users']]:[])];
  // Below 850 px the navigation collapses behind a menu button (styles.css); on wider screens the button is hidden.
  const menuButton=button([icon('menu'),'Menu'],()=>setMenu(menuButton.getAttribute('aria-expanded')!=='true'),'menu-button',{'aria-expanded':'false','aria-controls':'main-nav'});
  // Hash routing owns "#...": the skip link moves focus instead of changing the route.
  const skip=el('a',{href:'#',className:'skip-link',onclick:e=>{e.preventDefault();document.querySelector('#content').focus();}},'Ir para o conteúdo');
  app.replaceChildren(skip,el('div',{className:'app-layout'},
    el('aside',{className:'sidebar'},el('div',{className:'sidebar-head'},el('a',{href:'#dashboard',className:'brand'},brandLogo(),el('span',{'aria-hidden':'true'},'EdgeHealth')),menuButton),
      el('nav',{id:'main-nav','aria-label':'Navegação principal',onclick:e=>{if(e.target.closest('a'))setMenu(false);}},links.map(([key,text,symbol])=>el('a',{href:`#${key}`,dataset:{route:key}},icon(symbol),text)))),
    el('div',{className:'workspace'},el('header',{className:'topbar'},el('div',{},el('strong',{id:'company-name'},session.empresa.nome_fantasia)),
      el('div',{className:'actions'},el('span',{className:'user-name'},session.usuario.nome),button('Sair',logout,'ghost'))),el('main',{id:'content',tabIndex:-1}),
      el('footer',{className:'app-footer muted small'},el('a',{href:'/termos.html',target:'_blank',rel:'noopener'},'Termos de Uso'),' · ',el('a',{href:'/privacidade.html',target:'_blank',rel:'noopener'},'Aviso de Privacidade')))))
}
function setMenu(open,{restoreFocus=false}={}){
  const toggle=document.querySelector('.menu-button');if(!toggle)return;
  toggle.setAttribute('aria-expanded',String(open));
  toggle.closest('.sidebar').classList.toggle('nav-open',open);
  if(open)(document.querySelector('#main-nav a.active')||document.querySelector('#main-nav a'))?.focus();
  else if(restoreFocus)toggle.focus();
}
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&document.querySelector('.sidebar.nav-open')&&!document.querySelector('dialog[open]'))setMenu(false,{restoreFocus:true});});
async function navigate(){
  if(!session)return;
  setMenu(false);
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
    else if(page==='coletores')view=await Coletores();
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
apiFetch('/auth/me').then(enter).catch(error=>{signedOut();if(error.status!==401)toast(error.message,true);});
