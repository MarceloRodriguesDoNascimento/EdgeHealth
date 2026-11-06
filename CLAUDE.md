# EdgeHealth — guia para quem continua o projeto

Leia isto antes de mexer. Resume o que foi construído, as decisões tomadas, os comandos que funcionam e as armadilhas já resolvidas. Responda sempre em **português**, de forma direta.

## O projeto

SaaS de monitoramento de rede para pequenas e médias empresas: um **coletor** dentro da rede da empresa mede os dispositivos (ICMP) e envia ao **servidor**, que classifica online/instável/offline, abre **ocorrências**, faz o **diagnóstico lógico** (causa provável + recomendações), estima o **prejuízo** em R$ (horas de expediente × pessoas × custo/hora + custos diretos) e **explica com IA** (Gemini). Trabalho da disciplina **[PS-3B1/2026] Projeto de Software — Colégio Cotemig** (professor Gleison Brito Batista).

Equipe: Marcelo Domingos (22400362), Marcelo Rodrigues Alves do Nascimento (12400815), Erick Daniel Coelho E Silva (12401188), Felipe Barbosa Poeiras (12402320), Matheus Brito Vaz Bernardes (12502391), João Lucas Santos Batista (12401617).

- Site: https://marcelodomingos.pythonanywhere.com (plano gratuito; **renovar todo mês** na aba Web → "Run until 1 month from today").
- Repositório: https://github.com/MarceloRodriguesDoNascimento/EdgeHealth — branch de trabalho `feat/edgehealth-mvp` (o PythonAnywhere puxa dela); `main` recebe por PR, que o **usuário** faz o merge.
- Release do coletor Windows: `v1.0.0-coletor` (`EdgeHealthColetor.exe`), link usado em `frontend/src/pages/Coletores.js`.

## Cronograma e situação (novembro de 2026)

- 23/10 MVP com 20+ funcionalidades e vídeo: **entregue**. 07/11: **apresentação final** (pitch ~10 min + demo ao vivo 5 min + arguição; 30 pontos).
- Rubrica: fluxo do sistema 4, cliente-servidor 4 (obrigatório), API em camadas 7 (obrigatório), persistência e consultas 4, diagrama de classes 3, fluxogramas 4, apresentação e documentação 4; bônus IA 2, hospedagem 2, termos 1. A auditoria (`docs/AUDITORIA.md`) estima 30/30 + 5.
- Feito: 27 funcionalidades (6 principais ★ no README), camadas, banco, diagrama, 6 fluxogramas, IA, hospedagem, termos/LGPD, novo visual (PR #2, merged), slides (`apresentacao/`), roteiros, 25 perguntas da arguição.
- Pendente com a equipe: conferir os slides renderizados no PowerPoint/Google Slides e exportar PDF; estudo da equipe (todos estudam tudo; o usuário decidiu **não** dividir falas antes do estudo); rodada de perguntas/simulado da arguição (começou pela pergunta 1, sem resposta ainda); depois montar a divisão da apresentação e ensaiar; pendrive com PDF e vídeo.
- Ponto fraco conhecido: `Empresa.js` ainda envia fator 1.7 e 220 h quando o campo fica vazio ao salvar custos (a prévia já vem do servidor).
- Depois da nota: versão de portfólio. Combinado: o repositório original continua preservado e público, e o README do portfólio conta a história verdadeira (projeto de disciplina, equipe de 6, apoio de assistentes de IA, qual foi a parte do usuário). Não preparar cópia sem histórico para uso como entrega.

## Arquitetura (a rubrica cobra; não quebre)

`backend/` Flask (app factory em `app/`): `controllers/` (classes, uma por recurso; rotas em `controllers/rotas.py`, lista `ROTAS`, prefixo `/api`) → `services/` (uma classe por caso de uso, método `executar()`) → `models/` (um arquivo por entidade, `BaseModel` com salvar/atualizar/deletar/listar_todos/buscar_por_id) e `repositories/` (só consultas especiais em SQL, nunca CRUD). Cada método de Controller chama **um único** Service. SQLite + Alembic; `backend/database/create_database.sql` é gerado das migrations. Integração Gemini só em `services/ia/gemini_service.py`.

`frontend/` Vite + JS puro (sem framework), `src/pages/*.js`, helpers em `src/ui/dom.js`, Chart.js. Em produção o Flask serve `frontend/dist`. Dev: Vite :5173 com proxy para Flask :5000.

Testes que guardam a documentação — se mudar rota, Service, Model ou link, atualize junto:
- `test_readme.py` (tabela "Funcionalidades Implementadas", tabela de rotas = `ROTAS`, links), `test_flowcharts.py`, `test_diagram.py` (`docs/gerar_diagrama_classes.py`), `test_database_script.py`, `test_architecture.py` (camadas, um Service por método).

## Visual atual (painel de switch)

Visão da rede abre com uma frase de resumo (`networkSummary`) e uma porta por dispositivo (`port()` em `dom.js`), LED na cor **e na forma** do status (redondo online, losango instável, quadrado offline, vazado sem dados); clicar numa porta troca os gráficos. Abas no topo, fonte Archivo (`@fontsource-variable/archivo`, pré-carregada no `index.html`), azul de cabo `#1c3fab`, cores de LED só para status. Ocorrência: resumo no topo, diagnóstico/recomendações/IA à esquerda, linha do tempo/prejuízo/impacto/severidade à direita. Códigos da API são traduzidos só na tela (`human()` em `dom.js`); o JSON não muda. Acessibilidade revisada (Lighthouse 100, foco mantido na atualização de 15 s, movimento reduzido também nos `::before`).

## Comandos (Windows; Bash do app ou PowerShell)

```
cd backend && .venv/Scripts/python.exe -m pytest -q        # 187 aprovados, 3 pulados (ICMP real)
cd frontend && npm test                                    # 23 de 23 (pretest faz o build; usa Chrome para o teste responsivo)
cd frontend && npm run build && node tests/support/telas.mjs   # regera docs/img/telas/*.png
cd frontend && npm run build && node tests/support/demo.mjs    # demo local com dados fictícios em http://127.0.0.1:5180 (login de teste em seed() de tests/support/live.js)
```
- Slides: `apresentacao/gerar_apresentacao.py` com uma venv fora do repo (`python -m venv %TEMP%\pptvenv`, `pip install python-pptx==1.0.2`). Sem PowerPoint/LibreOffice nesta máquina: ninguém vê o render; peça ao usuário para conferir.
- PowerShell está com ExecutionPolicy Restricted: use `npx.cmd`, não `npx`.
- Heredocs com aspas, crases e `\` quebram no Bash: para patches grandes, escreva um script Python num arquivo e execute.

## PythonAnywhere (quem executa é o usuário)

Nunca mexa no PythonAnywhere diretamente: passe os passos. Atualização padrão (detalhes em `docs/PYTHONANYWHERE.md`):
1. Se o frontend mudou: gere o ZIP com Python (não `Compress-Archive`, que grava `\`):
   `backend/.venv/Scripts/python.exe -I -c "<zip de frontend/dist>" frontend/dist deploy/pythonanywhere/edgehealth-frontend-dist.zip` (comando completo na seção 8 de `docs/PYTHONANYWHERE.md`). O usuário **apaga o ZIP antigo** da home antes de enviar o novo (já deu problema de descompactar o ZIP velho).
2. Console Bash: `cd ~/EdgeHealth && git pull --ff-only origin feat/edgehealth-mvp && rm -rf frontend/dist && unzip -o ~/edgehealth-frontend-dist.zip -d frontend/dist && git log --oneline -1`
3. Reload na aba Web. Conferir de fora com `curl` (health, nome do `index-*.js` servido).
- `.env` de produção: `GEMINI_MODEL=gemini-3.5-flash-lite` (o 3.8-flash dava 503). Whitelist do plano grátis inclui `.googleapis.com`.

## Laboratório de rede (só nesta máquina)

`tests/lab/edgelab.py` controla um lab em WSL2 (Ubuntu-24.04) e a API hospedada, com a Empresa **TESTE LAB**: `preparar`, `subir`, `status`, `falha offline impressora`, `falha restaurar todos`, `cenario`, `descer`, `noturno`. Credenciais em `tests/lab/.credenciais-lab.json` e `.coletor-lab.token` (git-ignored, ACL só do dono): nunca imprima nem copie.
- Para demo: rode em dia útil 08h–18h (fora do expediente o prejuízo de falha nova é R$ 0,00); derrube a impressora **10+ min antes** (falhas a menos de 5 min se correlacionam e o diagnóstico vira "Infraestrutura compartilhada").
- Estado em 06/11: TEST-NET (192.0.2.1) OFFLINE de propósito; dispositivo "Celular" arquivado; "Coletor Notebook" sem contato desde 10/10.

## Regras do usuário

- Nada de chave, senha, token ou e-mail de conta no código, testes, logs, commits ou README (repositório público). Credenciais de demonstração vão ao professor pelo Classroom. Nunca peça para colar segredo no chat (para chaves, use variável de ambiente lida com `Read-Host -AsSecureString`).
- Não use simulação de teclado. Não eleve privilégios de administrador sozinho.
- Não altere rotas, JSON, regras de negócio, protocolo do coletor ou migrations sem perguntar.
- Rode as suítes completas antes de fechar, informe os números reais, faça commit e push em `feat/edgehealth-mvp` quando pedido; merge na `main` é do usuário.
- Ferramentas instaladas: skills frontend-design e web-design-guidelines; MCPs chrome-devtools, shadcn (catálogo React, só referência) e 21st/Magic (conta grátis: sem geração por IA, 2 consultas de código por dia; `.mcp.json` lê `API_KEY_21ST` e fica fora do Git).

## Outros documentos

`README.md` (sumário, funcionalidades, rotas, como executar), `docs/AUDITORIA.md`, `docs/ROTEIRO_VIDEO.md`, `apresentacao/ROTEIRO_APRESENTACAO.md`, `apresentacao/PERGUNTAS_ARGUICAO.md`, `docs/DEPLOY.md`, `docs/LGPD.md`, `collector/README.md`, `tests/lab/README.md`.
