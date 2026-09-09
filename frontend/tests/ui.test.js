import {test,beforeEach,afterEach} from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {el,form,table,confirmAction} from '../src/ui/dom.js';
import {apiFetch} from '../src/services/api.js';

let dom;
beforeEach(()=>{
  dom=new JSDOM('<div id="app"></div><div id="notifications"></div>',{url:'http://localhost/'});
  for(const key of ['window','document','Node','Event','FormData'])Object.defineProperty(globalThis,key,{value:dom.window[key],configurable:true,writable:true});
  dom.window.HTMLDialogElement.prototype.showModal=function(){this.open=true;};
  dom.window.HTMLDialogElement.prototype.close=function(){this.open=false;this.dispatchEvent(new Event('close'));};
});
afterEach(()=>dom.window.close());

test('user content is text, never executable HTML',()=>{
  const node=el('div',{},'<img src=x onerror=alert(1)>');
  assert.equal(node.querySelector('img'),null);
  assert.match(node.textContent,/onerror/);
  const t=table(['Nome'],[['<script>bad()</script>']]);
  assert.equal(t.querySelector('script'),null);
});

test('form submits fields, prevents native navigation and reports errors',async()=>{
  let received;
  const node=form([el('input',{name:'nome',value:'Empresa'})],'Salvar',async data=>{received=data;throw new Error('Validação de exemplo');});
  document.body.append(node);
  const event=new Event('submit',{cancelable:true});
  node.dispatchEvent(event);
  await new Promise(r=>setTimeout(r,0));
  assert.equal(event.defaultPrevented,true);
  assert.equal(received.nome,'Empresa');
  assert.equal(node.querySelector('[role=alert]').textContent,'Validação de exemplo');
  assert.equal(node.querySelector('button').disabled,false);
});

test('HTTP 204 has no JSON and mutations carry CSRF',async()=>{
  document.cookie='edgehealth_csrf=nonce';let sent;
  globalThis.fetch=async(url,options)=>{sent={url,...options};return {ok:true,status:204};};
  assert.equal(await apiFetch('/dispositivos/1',{method:'DELETE'}),null);
  assert.equal(sent.headers['X-CSRF-Token'],'nonce');
  assert.equal(sent.credentials,'same-origin');
});

test('expired session emits event and exposes the real error',async()=>{
  let expired=false;
  window.addEventListener('session-expired',()=>{expired=true;});
  globalThis.fetch=async()=>({ok:false,status:401,json:async()=>({erro:'Sessão expirada'})});
  await assert.rejects(apiFetch('/dispositivos'),/Sessão expirada/);
  assert.equal(expired,true);
});

test('destructive action needs confirmation in the interface',async()=>{
  let ran=false;
  confirmAction('Arquivar?','Histórico preservado',async()=>{ran=true;});
  assert.equal(ran,false);
  const dialog=document.querySelector('dialog');
  [...dialog.querySelectorAll('button')].find(b=>b.textContent==='Confirmar').click();
  await new Promise(r=>setTimeout(r,0));
  assert.equal(ran,true);
  assert.equal(document.querySelector('dialog'),null);
});

test('failed confirmation keeps the dialog usable and displays the API error',async()=>{
  confirmAction('Arquivar?','Histórico preservado',async()=>{throw new Error('Coleta em andamento');});
  const confirm=[...document.querySelectorAll('dialog button')].find(b=>b.textContent==='Confirmar');
  confirm.click();
  await new Promise(r=>setTimeout(r,0));
  assert.equal(confirm.disabled,false);
  assert.ok(document.querySelector('dialog'));
  assert.match(document.querySelector('#notifications').textContent,/Coleta em andamento/);
});
