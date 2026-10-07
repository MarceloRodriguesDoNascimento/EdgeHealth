import {test} from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {createInterface} from 'node:readline';
import {fileURLToPath} from 'node:url';
import {join} from 'node:path';
import {existsSync} from 'node:fs';
import {JSDOM} from 'jsdom';
import {createServer} from 'vite';
import Chart from 'chart.js/auto';
import {Login} from '../src/pages/Login.js';
import {Empresa} from '../src/pages/Empresa.js';
import {Usuarios} from '../src/pages/Usuarios.js';
import {Dispositivos} from '../src/pages/Dispositivos.js';
import {Historico} from '../src/pages/Historico.js';
import {Falha} from '../src/pages/Falha.js';
import {Dashboard} from '../src/pages/Dashboard.js';
import {Relatorios} from '../src/pages/Relatorios.js';
import {Coletores} from '../src/pages/Coletores.js';
import {apiFetch} from '../src/services/api.js';

const nativeFetch=globalThis.fetch;
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function until(check, message, timeout=5000) {
  const end=Date.now()+timeout;
  while(Date.now()<end) { if(check()) return; await pause(10); }
  assert.fail(message);
}
function button(text, within=document) {
  const found=[...within.querySelectorAll('button')].find(b=>b.textContent===text);
  assert.ok(found,`Botão não encontrado: ${text}`);return found;
}
async function submit(values, within=document, expectError=false) {
  const form=within.querySelector('form');assert.ok(form);
  for(const [name,value] of Object.entries(values)) { const field=form.elements.namedItem(name);assert.ok(field,name);if(field.type==='checkbox')field.checked=Boolean(value);else field.value=value; }
  form.dispatchEvent(new Event('submit',{cancelable:true,bubbles:true}));
  await until(()=>!form.querySelector('[type=submit]').disabled,'Formulário não terminou');
  if(!expectError) assert.equal(form.querySelector('[role=alert]').textContent,'');
  return form;
}

test('interface completa usa a API HTTP e SQLite migrado, sem respostas HTTP simuladas', {timeout:45000}, async t=>{
  const backend=fileURLToPath(new URL('../../backend/',import.meta.url));
  const candidate=join(backend,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
  const python=process.env.EDGEHEALTH_PYTHON||(existsSync(candidate)?candidate:(process.platform==='win32'?'python':'python3'));
  const child=spawn(python,['-u',join(backend,'tests/ui_server.py')],{cwd:backend,stdio:['pipe','pipe','pipe']});
  let serverError='',base,sequence=0;const pending=new Map();
  child.stderr.on('data',chunk=>{serverError+=chunk;});
  const lines=createInterface({input:child.stdout});
  lines.on('line',line=>{
    let data;try{data=JSON.parse(line);}catch{return;}
    if(data.ready)base=data.ready;
    if(data.id&&pending.has(data.id)){pending.get(data.id)(data);pending.delete(data.id);}
  });
  child.on('error',error=>{serverError+=error.message;});
  t.after(async()=>{child.stdin.end();await until(()=>child.exitCode!==null,'Servidor de teste não encerrou',6000).catch(()=>child.kill());lines.close();});
  await until(()=>base||child.exitCode!==null,'API de teste não iniciou: '+serverError,15000);
  assert.ok(base,serverError);
  const dom=new JSDOM('<span id="company-name"></span><div id="app"></div><div id="notifications"></div>',{url:base,pretendToBeVisual:true});
  t.after(()=>dom.window.close());
  for(const key of ['window','document','Node','Event','FormData','MutationObserver'])Object.defineProperty(globalThis,key,{value:dom.window[key],configurable:true,writable:true});
  dom.window.HTMLDialogElement.prototype.showModal=function(){this.open=true;};
  dom.window.HTMLDialogElement.prototype.close=function(){this.open=false;this.dispatchEvent(new Event('close'));};
  // Canvas rendering is not provided by jsdom. Only this drawing surface is a
  // test double; chart datasets and all HTTP responses come from the real API.
  globalThis.ResizeObserver=class{observe(){}unobserve(){}disconnect(){}};
  const contexts=new WeakMap();
  dom.window.HTMLCanvasElement.prototype.getContext=function(){
    if(!contexts.has(this))contexts.set(this,new Proxy({canvas:this,measureText:text=>({width:String(text).length*7})},{get:(object,key)=>key in object?object[key]:()=>{}}));
    return contexts.get(this);
  };
  const requests=[];
  globalThis.fetch=async(path,options={})=>{
    const headers={...options.headers,Cookie:dom.cookieJar.getCookieStringSync(base)};
    const response=await nativeFetch(new URL(path,base),{...options,headers});
    for(const cookie of response.headers.getSetCookie())dom.cookieJar.setCookieSync(cookie,base);
    requests.push({path,method:options.method||'GET',status:response.status});
    return response;
  };
  t.after(()=>{globalThis.fetch=nativeFetch;});
  const mount=node=>document.querySelector('#app').replaceChildren(node);
  let session,deviceId,failureId,dispose=()=>{},download;
  t.after(()=>dispose());
  const collect=async(received,latency_ms)=>{
    const id=++sequence;
    const result=new Promise(resolve=>pending.set(id,resolve));
    child.stdin.write(JSON.stringify({id,device_id:deviceId,sent:4,received,latency_ms})+'\n');
    assert.equal((await result).success,true);
  };

  await t.test('cadastro de empresa, login, sessão e edição da organização',async()=>{
    mount(Login(data=>{session=data;},true));
    await submit({nome_fantasia:'Empresa de integração',cnpj:'11222333000181',nome:'Administrador',email:'admin@integration.example',senha:'test-integration-password',aceite_termos:true});
    assert.equal(session.usuario.papel,'ADMIN');assert.equal(session.usuario.termos_pendentes,false);
    assert.equal(document.querySelector('img.brand-logo').alt,'EdgeHealth');
    assert.equal((await apiFetch('/empresa')).nome_fantasia,'Empresa de integração');
    await apiFetch('/auth/logout',{method:'POST',body:'{}'});
    mount(Login(data=>{session=data;}));
    await submit({email:'admin@integration.example',senha:'test-integration-password'});
    assert.ok(session.usuario.id);
    mount(await Empresa(session));
    await submit({nome_fantasia:'Empresa atualizada',telefone:'31999999999'});
    assert.equal((await apiFetch('/empresa')).nome_fantasia,'Empresa atualizada');
    // Costs: live cost-per-hour preview, then saved as exact decimals (all day, every day: deterministic tests).
    const costs=document.querySelector('#custos');
    const salary=costs.querySelector('[name=salario_medio]');salary.value='3.000,00';salary.dispatchEvent(new Event('input'));
    assert.match(costs.querySelector('.cost-preview').textContent,/Custo por hora estimado: R\$\s23,18 \(3\.000 × 1,7 ÷ 220\)/);
    costs.querySelectorAll('[name=dias]').forEach(box=>{box.checked=true;});
    await submit({salario_medio:'3.000,00',total_funcionarios:'40',inicio:'00:00',fim:'23:59'},costs);
    const saved=(await apiFetch('/empresa')).custos;
    assert.equal(saved.custo_hora,'23.18');assert.equal(saved.salario_medio,'3000.00');assert.deepEqual(saved.expediente.dias,[1,2,3,4,5,6,7]);
  });

  await t.test('criação, edição e desativação de usuário da equipe',async()=>{
    mount(await Usuarios(session));button('Cadastrar usuário').click();
    await submit({nome:'Técnico',email:'tech@integration.example',senha:'test-technician-password',papel:'TECNICO'},document.querySelector('dialog'));
    let users=await apiFetch('/usuarios');assert.equal(users.length,2);
    let row=[...document.querySelectorAll('tbody tr')].find(r=>r.textContent.includes('tech@integration.example'));
    button('Editar',row).click();await submit({nome:'Técnico atualizado'},document.querySelector('dialog'));
    users=await apiFetch('/usuarios');assert.equal(users.find(u=>u.email==='tech@integration.example').nome,'Técnico atualizado');
    row=[...document.querySelectorAll('tbody tr')].find(r=>r.textContent.includes('tech@integration.example'));
    button('Desativar',row).click();button('Confirmar',document.querySelector('dialog')).click();
    await until(()=>!document.querySelector('dialog'),'Desativação pendente');
    assert.equal((await apiFetch('/usuarios')).find(u=>u.email==='tech@integration.example').ativo,false);
  });

  await t.test('cadastro, validação, edição e solicitação assíncrona de coleta',async()=>{
    mount(await Dispositivos(session));button('Cadastrar dispositivo').click();await until(()=>document.querySelector('dialog'),'Formulário não abriu');
    const invalid=await submit({nome:'Servidor',ip:'IP inválido',tipo:'Servidor',localizacao:'Sala TI'},document.querySelector('dialog'),true);
    assert.match(invalid.querySelector('[role=alert]').textContent,/IPv4 ou IPv6/);
    await submit({ip:'127.0.0.1'},document.querySelector('dialog'));
    const devices=await apiFetch('/dispositivos');assert.equal(devices.length,1);deviceId=devices[0].id;
    assert.equal(devices[0].status,null);
    button('Editar').click();await until(()=>document.querySelector('dialog'),'Edição não abriu');await submit({nome:'Servidor atualizado'},document.querySelector('dialog'));
    assert.equal((await apiFetch(`/dispositivos/${deviceId}`)).nome,'Servidor atualizado');
    button('Coletar').click();await until(()=>requests.some(r=>r.path.endsWith('/coletas')&&r.status===202),'Coleta não solicitada');
    assert.equal((await apiFetch('/metricas')).total,0);
    await collect(4,2.5);assert.equal((await apiFetch(`/dispositivos/${deviceId}`)).status,'ONLINE');
    // "Impacto no negócio" follows the type until edited: a printer is 10 people, 30% (custom).
    button('Cadastrar dispositivo').click();await until(()=>document.querySelector('dialog form'),'Formulário não abriu');
    const dialog=document.querySelector('dialog'),tipo=dialog.querySelector('[name=tipo]');
    tipo.value='Impressora';tipo.dispatchEvent(new Event('input'));
    await until(()=>dialog.querySelector('[name=usuarios_dependentes]').value==='10','Padrão do tipo não aplicado',3000);
    assert.equal(dialog.querySelector('[name=perda_opcao]:checked').value,'custom');assert.equal(dialog.querySelector('[name=perda_custom]').value,'30');
    tipo.value='Máquina de cartão';tipo.dispatchEvent(new Event('input'));
    await until(()=>dialog.querySelector('[name=usuarios_dependentes]').value==='1'&&/receita direta/.test(dialog.textContent),'PDV não sugeriu receita',3000);
    assert.equal(dialog.querySelector('[name=perda_opcao]:checked').value,'100');
    const people=dialog.querySelector('[name=usuarios_dependentes]');people.value='3';people.dispatchEvent(new Event('input'));
    tipo.value='Roteador';tipo.dispatchEvent(new Event('input'));await pause(450);
    assert.equal(people.value,'3');  // edited by the person: the type no longer overwrites it
    dialog.querySelector('[value="10"][name=perda_opcao]').click();
    await submit({nome:'Caixa da loja',ip:'127.0.0.9',localizacao:'Loja',receita_hora_dependente:'1.234,50'},dialog);
    const pos=(await apiFetch('/dispositivos')).find(d=>d.nome==='Caixa da loja');
    assert.deepEqual([pos.usuarios_dependentes,pos.perda_produtividade_pct,pos.receita_hora_dependente],[3,10,'1234.50']);
    await apiFetch(`/dispositivos/${pos.id}`,{method:'DELETE'});
  });

  await t.test('falha única, severidade, diagnóstico, causas e impacto na tela',async()=>{
    await collect(3,220);await collect(3,240);
    const failures=await apiFetch('/falhas');assert.equal(failures.total,1);failureId=failures.items[0].id;
    mount(await Historico());assert.match(document.querySelector('#app').textContent,/Servidor atualizado/);
    mount(await Falha(failureId));
    assert.match(document.querySelector('#app').textContent,/CONGESTIONAMENTO/);
    assert.match(document.querySelector('#app').textContent,/Verificar tráfego e interfaces/);
    await submit({usuarios_afetados:'60',custos_diretos:'250,00',observacao:'Informação do responsável de TI'});
    assert.equal((await apiFetch(`/falhas/${failureId}`)).severidade,'CRITICA');
    assert.match(document.querySelector('#app').textContent,/Estimativa informada pela equipe/);
    // Loss estimate: the value and the open calculation, with the disclaimer.
    const loss=document.querySelector('.loss-panel').textContent,estimate=(await apiFetch(`/falhas/${failureId}`)).prejuizo;
    assert.match(loss,/60 pessoas × R\$ 23,18\/h × 50% × [\d,]+ h de expediente \+ R\$ 250,00 de custos diretos/);
    assert.match(loss,/Estimativa baseada nos custos informados pela empresa/);
    assert.equal(estimate.detalhe.custos_diretos,'250.00');assert.equal(estimate.detalhe.pessoas,60);
  });

  await t.test('dashboard apresenta métricas e gráficos com dados persistidos',async()=>{
    mount(await Dashboard(fn=>{dispose=fn;}));
    await until(()=>document.querySelectorAll('.stat strong').length===5,'Dashboard não desenhou');
    assert.deepEqual([...document.querySelectorAll('.stat strong')].map(n=>n.textContent),['1','0','1','0','1']);
    const canvas=document.querySelectorAll('canvas');assert.equal(canvas.length,2);
    assert.match(document.querySelector('.cost-summary').textContent,/R\$\s[\d.]+,\d{2}/);
    assert.match(document.querySelector('.cost-summary').textContent,/Servidor atualizado/);
    assert.deepEqual(Chart.getChart(canvas[0]).data.datasets[0].data,[2.5,220,240]);
    assert.deepEqual(Chart.getChart(canvas[1]).data.datasets[0].data,[0,25,25]);
    dispose();dispose=()=>{};
  });

  await t.test('offline, recuperação e histórico conservam a ocorrência e suas evidências',async()=>{
    await collect(0,null);await collect(0,null);await collect(0,null);
    assert.equal((await apiFetch(`/dispositivos/${deviceId}`)).status,'OFFLINE');
    assert.equal((await apiFetch('/falhas')).total,1);
    await collect(3,260);await collect(4,2);await collect(4,2);
    const incident=await apiFetch(`/falhas/${failureId}`);
    assert.equal(incident.estado,'ENCERRADA');
    assert.ok(incident.diagnostico.recomendacoes.length);
    mount(await Historico());
    document.querySelector('[name=estado]').value='ENCERRADA';button('Filtrar').click();
    await until(()=>document.querySelector('tbody').textContent.includes('ENCERRADA'),'Histórico não filtrou');
    mount(await Dispositivos(session));button('Métricas').click();
    await until(()=>document.querySelector('dialog tbody tr'),'Métricas não carregaram');
    assert.match(document.querySelector('dialog').textContent,/9 amostras/);
    button('Fechar',document.querySelector('dialog')).click();
  });

  await t.test('coletor remoto: cadastro, credencial única, atribuição e revogação pela tela',async()=>{
    mount(await Coletores());
    const download=[...document.querySelectorAll('a')].find(a=>a.textContent==='Baixar coletor para Windows');
    assert.equal(download?.getAttribute('href'),'https://github.com/MarceloRodriguesDoNascimento/EdgeHealth/releases/latest/download/EdgeHealthColetor.exe');
    button('Cadastrar coletor').click();
    await submit({nome:'Coletor da filial'},document.querySelector('dialog'));
    await until(()=>document.querySelector('dialog input[readonly]'),'Credencial não exibida');
    const token=document.querySelector('dialog input[readonly]').value;
    assert.match(token,/^ehc_/);
    const [collector]=await apiFetch('/coletores');
    assert.equal(collector.estado,'NUNCA_CONECTADO');assert.ok(!('token' in collector));
    button('Fechar',document.querySelector('dialog')).click();
    // The collector authenticates with its own credential, never with the user cookie.
    const config=await nativeFetch(base+'/api/coletor/configuracao',{headers:{Authorization:'Bearer '+token}});
    assert.equal(config.status,200);assert.deepEqual((await config.json()).dispositivos,[]);
    mount(await Dispositivos(session));button('Editar').click();await until(()=>document.querySelector('dialog'),'Edição não abriu');
    await submit({coletor_id:String(collector.id)},document.querySelector('dialog'));
    assert.equal((await apiFetch(`/dispositivos/${deviceId}`)).coletor_id,collector.id);
    assert.match(document.querySelector('#app').textContent,/Coletor da filial · sem contato recente|Coletor da filial/);
    mount(await Coletores());button('Revogar').click();button('Confirmar',document.querySelector('dialog')).click();
    await until(()=>!document.querySelector('dialog'),'Revogação pendente');
    assert.equal((await nativeFetch(base+'/api/coletor/configuracao',{headers:{Authorization:'Bearer '+token}})).status,401);
    mount(await Dispositivos(session));button('Editar').click();await until(()=>document.querySelector('dialog'),'Edição não abriu');
    await submit({coletor_id:''},document.querySelector('dialog'));
    assert.equal((await apiFetch(`/dispositivos/${deviceId}`)).coletor_id,null);
  });

  await t.test('exportação gera ZIP real pela tela; arquivamento conserva todo o histórico',async()=>{
    const create=URL.createObjectURL,revoke=URL.revokeObjectURL;
    URL.createObjectURL=blob=>{download=blob;return 'blob:test-export';};URL.revokeObjectURL=()=>{};
    dom.window.HTMLAnchorElement.prototype.click=function(){};
    t.after(()=>{URL.createObjectURL=create;URL.revokeObjectURL=revoke;});
    mount(await Relatorios());await submit({});
    assert.equal(download.type,'application/zip');
    const bytes=new Uint8Array(await download.arrayBuffer());assert.deepEqual([...bytes.slice(0,2)],[80,75]);
    assert.ok(bytes.length>1000);
    mount(await Dispositivos(session));button('Arquivar').click();
    assert.equal(document.querySelector('dialog h2').textContent,'Arquivar dispositivo?');
    button('Arquivar',document.querySelector('dialog')).click();
    await until(()=>!document.querySelector('dialog'),'Arquivamento pendente');
    assert.equal((await apiFetch('/dispositivos')).length,0);
    assert.equal((await apiFetch('/metricas')).total,9);
    assert.equal((await apiFetch('/falhas')).total,1);
    // Restore from the "Incluir arquivados" view, then archive again.
    const include=document.querySelector('[name=arquivados]');include.checked=true;include.dispatchEvent(new Event('change'));
    await until(()=>[...document.querySelectorAll('button')].some(b=>b.textContent==='Desarquivar'),'Botão Desarquivar ausente');
    button('Desarquivar').click();
    assert.match(document.querySelector('dialog').textContent,/voltará a ser monitorado/);
    button('Desarquivar',document.querySelector('dialog')).click();
    await until(()=>!document.querySelector('dialog'),'Desarquivamento pendente');
    const restored=await apiFetch('/dispositivos');
    assert.equal(restored.length,1);assert.equal(restored[0].arquivado_em,null);assert.equal(restored[0].status,null);
    assert.equal((await apiFetch('/metricas')).total,9);  // history preserved
    await until(()=>[...document.querySelectorAll('button')].some(b=>b.textContent==='Arquivar'),'Lista não atualizou');
    button('Arquivar').click();button('Arquivar',document.querySelector('dialog')).click();
    await until(()=>!document.querySelector('dialog'),'Novo arquivamento pendente');
    assert.equal((await apiFetch('/dispositivos')).length,0);
    await apiFetch('/auth/logout',{method:'POST',body:'{}'});
    await assert.rejects(apiFetch('/dispositivos'),error=>error.status===401);
  });
  await t.test('build servido pelo Flask e proxy Vite alcançam a mesma API',async()=>{
    const production=await nativeFetch(base+'/');
    assert.equal(production.status,200);
    assert.match(production.headers.get('content-security-policy'),/default-src 'self'/);
    const html=await production.text();
    const asset=html.match(/src="(\/assets\/[^\"]+\.js)"/)[1];
    assert.equal((await nativeFetch(base+asset)).status,200);
    for(const page of ['/termos.html','/privacidade.html']){
      const legal=await nativeFetch(base+page);
      assert.equal(legal.status,200);const text=await legal.text();
      assert.match(text,/MINUTA/);assert.match(text,/rel="icon"[^>]*\/logo\.svg/);
    }
    assert.match(html,/rel="icon"[^>]*\/logo\.svg/);
    const logo=await nativeFetch(base+'/logo.svg');
    assert.equal(logo.status,200);assert.match(logo.headers.get('content-type'),/image\/svg\+xml/);
    const oldTarget=process.env.API_PROXY_TARGET;
    process.env.API_PROXY_TARGET=base;
    let vite;
    try {
      vite=await createServer({configFile:fileURLToPath(new URL('../vite.config.js',import.meta.url)),root:fileURLToPath(new URL('../',import.meta.url)),server:{host:'127.0.0.1',port:0},logLevel:'silent'});
      await vite.listen();
      const address=`http://127.0.0.1:${vite.httpServer.address().port}`;
      assert.equal((await nativeFetch(address+'/')).status,200);
      const health=await nativeFetch(address+'/api/health');
      assert.equal(health.status,200);assert.equal((await health.json()).status,'ok');
      assert.equal((await nativeFetch(address+'/api/dispositivos')).status,401);
    } finally {
      if(vite)await vite.close();
      if(oldTarget===undefined)delete process.env.API_PROXY_TARGET;else process.env.API_PROXY_TARGET=oldTarget;
    }
  });
  assert.ok(requests.length>35);
  assert.equal(requests.filter(r=>r.status>=500).length,0,JSON.stringify(requests));
});
