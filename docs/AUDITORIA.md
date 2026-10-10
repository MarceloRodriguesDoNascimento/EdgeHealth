# Auditoria final contra a rubrica — Projeto de Software

Auditoria de **09/10/2026**, na branch `feat/edgehealth-mvp`, feita como correção do professor: cada critério foi conferido no código, nos testes, por comandos e na produção (<https://marcelodomingos.pythonanywhere.com>). Entrega do MVP: 23/10. Apresentação final: 07/11.

**Nota estimada: 30/30 + 5/5 de bônus.** Os dois critérios obrigatórios (cliente-servidor e camadas) estão completos. Os riscos estão na seção [Pontos fracos](#pontos-fracos-encontrados) e no que depende da equipe (vídeo e apresentação).

Legenda: ✅ atendido · ⚠️ atendido com ressalva · ❌ não atendido.

## Rubrica

| Critério | Pontos | Evidência | Status | Ação |
| --- | --- | --- | --- | --- |
| **Fluxo do sistema** — funcionalidades principais não-CRUD de ponta a ponta | 4/4 | 6 funcionalidades ★ no README (detecção de falhas pelo coletor, diagnóstico com recomendações, prejuízo estimado, explicação com IA, dashboard com ranking de custo, relatório ZIP). Todas chamadas **em produção** em 09/10/2026 (tabela [Produção](#produção-0910-2026)). | ✅ | — |
| **Cliente-servidor** — servidores separados (2) | 2/2 | `frontend/` (Vite) e `backend/` (Flask) são aplicações separadas. Prova: Vite escutando em `:5173` (PID 21272) e Flask em `:5000` (PID 21596) ao mesmo tempo (`netstat`). | ✅ | — |
| **Cliente-servidor** — frontend consome a API por requisições (2) | 2/2 | `frontend/src/services/api.js` usa `fetch('/api…')`; `curl :5173/api/health` → 200 JSON, e o log do Flask registrou `GET /api/health` vindo do Vite. Comandos no README, seção "Cliente-servidor". | ✅ | — |
| **Camadas** — Controllers recebem e acionam casos de uso (1) | 1/1 | `backend/controllers/`: 12 classes, uma por recurso, herdando `BaseController`; `rotas.py` liga URL → método. Nenhum importa `db`/`sqlalchemy` (`tests/test_architecture.py`). | ✅ | Cada método chama um único Service (`test_architecture.py`). |
| **Camadas** — Services por caso de uso e regras (3) | 3/3 | `backend/services/<recurso>/`: um caso de uso por classe com `executar()` (ex.: `CadastrarDispositivoService`, `RegistrarImpactoService`, `ExplicarFalhaComIaService`). Métodos extras são auxiliares do mesmo caso (`ObterFalhaService.buscar`, `GeminiService.disponivel`). Services não leem `flask.request`/`g` nem executam SQL (`test_architecture.py`). | ✅ | — |
| **Camadas** — Models (1) | 1/1 | `backend/models/`: 13 entidades, um arquivo cada, herdando `BaseModel(db.Model)` com `salvar`, `atualizar`, `deletar`, `listar_todos`, `buscar_por_id` (+ `buscar_um_por`). Uso nos services: `salvar` 19×, `atualizar` 15×, `buscar_por_id` 25×, `deletar` 1×, `listar_todos` 1×. | ✅ | — |
| **Camadas** — Repositories com responsabilidade definida (1) | 1/1 | `backend/repositories/`: só consultas especiais (multiempresa, histórico paginado, agregações, ranking, lease, retenção) e `Transacao`. Nenhum método repete o CRUD da base; todos os métodos públicos são usados (varredura de referências). | ✅ | — |
| **Camadas** — comunicação coerente (1) | 1/1 | Tela → Controller → Service → Model/Repository → Banco em todos os 6 fluxogramas; `test_flowcharts.py` confere cada classe e método citados; `test_readme.py` confere as 27 funcionalidades e as 39 rotas. | ✅ | — |
| **Persistência** — CRUD com ORM (2) | 2/2 | SQLAlchemy via `BaseModel`; CRUD de dispositivos, usuários, coletores, impacto e empresa testado em `tests/test_auth_and_crud.py`. | ✅ | — |
| **Persistência** — SQL no Repository com resultados corretos (2) | 2/2 | `text()` em `DashboardRepository`, `FalhaRepository.ranking_dispositivos`, `RankingCustoRepository.top_dispositivos` (CTE); Core nos demais. `tests/test_repositories.py` (11 testes) confere resultado exato de cada consulta especial. `backend/database/create_database.sql` existe e é testado contra as migrations (`test_database_script.py`). | ✅ | — |
| **Diagrama de classes** — classes e atributos (1) | 1/1 | [`docs/diagrama-classes.md`](diagrama-classes.md) + SVG/PNG, gerado dos Models. | ✅ | — |
| **Diagrama de classes** — relacionamentos (1) | 1/1 | 13 relações com cardinalidade e tipo (composição, agregação, associação): Empresa 1–0..* Usuário/Dispositivo/Coletor, Dispositivo 1–0..* Falha e Métrica, Falha 1–1 Impacto e 1–0..1 Diagnóstico, Diagnóstico N–N Recomendação via `DiagnosticoRecomendacao`. | ✅ | — |
| **Diagrama de classes** — correspondência com o sistema (1) | 1/1 | `tests/test_diagram.py` (4 testes) falha se o diagrama divergir dos Models. | ✅ | — |
| **Fluxogramas** — recuperação de dados (2) | 2/2 | [`docs/fluxogramas.md`](fluxogramas.md) casos 4, 5 e 6 (histórico, dashboard, IA), cada um passando pelo Repository. | ✅ | — |
| **Fluxogramas** — entrada de dados (2) | 2/2 | Casos 1, 2 e 3 (cadastrar dispositivo, coletor envia amostras, registrar impacto). `test_flowcharts.py` exige Controller, Service e Repository em todos. | ✅ | — |
| **Apresentação e documentação** — descrição, público e problema (1) | 1/1 | README, 2 parágrafos iniciais. | ✅ | Repetir no pitch. |
| **Apresentação e documentação** — cinco casos de uso e telas (1) | 1/1 | README, seção "Casos de uso e telas": 6 casos com as telas; 12 capturas em `docs/img/telas/` (geradas nesta auditoria). | ✅ | Mostrar as telas ao vivo no vídeo. |
| **Apresentação e documentação** — arquitetura, diretórios e tecnologias (1) | 1/1 | README: Stack com versões, árvore de diretórios, tabela das camadas, diagrama cliente-servidor. | ✅ | — |
| **Apresentação e documentação** — README com casos implementados (1) | 1/1 | Seção "Funcionalidades Implementadas" com 27 itens numerados (tela, rota, Service, Repository/Model). | ✅ | — |
| **Bônus: IA como serviço** | 2/2 | `GeminiService` é a única classe que chama o LLM (nenhum outro arquivo usa `urllib`/Gemini); `ExplicarFalhaComIaService` monta o contexto só com dados técnicos; chave só no `.env`; 20 testes em `test_ia.py` sem rede. Produção: 200 com `gemini-3.5-flash-lite`. | ✅ | — |
| **Bônus: hospedagem** | 2/2 | <https://marcelodomingos.pythonanywhere.com>: HTTPS (HTTP → 302 HTTPS), HSTS, CSP, assets do build 200, rotas protegidas 401 sem sessão. | ⚠️ | **Renovar o plano gratuito antes de 07/11** (o site expira se não renovado). |
| **Bônus: termos de consentimento** | 1/1 | Aceite obrigatório no cadastro e no primeiro acesso (`AceitarTermosService`, versão registrada; 403 até aceitar), `termos.html` e `privacidade.html` publicados (200 em produção). | ✅ | Minutas precisam de revisão dos responsáveis. |
| **Total** | **30/30 + 5** | | | |

## Requisitos das atividades

| Requisito | Evidência | Status |
| --- | --- | --- |
| `backend/controllers`, `services`, `models`, `repositories` e `database/create_database.sql` | Todos presentes; o script SQL é gerado das migrations e testado. | ✅ |
| Controllers como classes, um por recurso, sem regra de negócio | 12 classes em `controllers/`; `test_architecture.py`. | ✅ |
| Um Service (classe) por caso de uso | 68 classes `*Service` em `services/<recurso>/`. | ✅ |
| Models herdando de `db.Model` com as 5 operações | `models/base.py` (`BaseModel(db.Model)`, abstrato); `test_architecture.py` exige as 5. | ✅ |
| Repository só para consultas especiais | Ver rubrica. | ✅ |
| Integração com LLM encapsulada num Service | `services/ia/gemini_service.py`. | ✅ |
| Chaves em `.env`, nunca no repositório | `.env` e `*.db` no `.gitignore`; varredura do histórico abaixo. | ✅ |
| README: nome, integrantes, stack, descrição, como executar, "Funcionalidades Implementadas" (≥ 20), onde está o diagrama de classes | Tudo no README; `test_readme.py` garante a tabela, as rotas e os links. | ✅ |
| Vídeo de até 5 min | Responsabilidade da equipe. | ⚠️ pendente |

## Segredos no histórico do Git

Varredura dos **39 commits** de todas as branches (`git grep` em `git rev-list --all`):

- Chaves Google (`AIza…`), tokens GitHub/OpenAI, chaves privadas: **nenhuma**.
- Credenciais de coletor `ehc_…`: só o valor fictício `ehc_mesma-credencial` em `tests/test_collector_windows.py`.
- `.env` versionado: **nunca** (só `backend/.env.example`, sem valores secretos).
- Senhas: só valores de teste em domínios `.example`/`.test` nos testes.
- Bancos SQLite: 4 arquivos `.db` do **protótipo** (ago/2026) foram versionados e removidos em `f2a7dfe` (09/09/2026). Conteúdo: um usuário fictício ("Ana", `teste`, senha "123") e nenhum dado real. Não exige revogação; hoje `*.db` está no `.gitignore`.
- As credenciais do laboratório (`tests/lab/.credenciais-lab.json`, `.coletor-lab.token`) nunca entraram no Git.

## Produção (09/10/2026)

Sem credenciais: `/api/health` 200 `{"status":"ok"}`, `/api/termos` 200, `/` 200 HTML, `/termos.html` e `/privacidade.html` 200, assets JS/CSS 200, `/api/dashboard` e `/api/coletor/configuracao` 401. Cabeçalhos: `Strict-Transport-Security`, `Content-Security-Policy`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`.

Funcionalidades ★, uma chamada cada, com a conta do laboratório (`tests/lab/edgelab.py`, credenciais lidas do arquivo local, nunca exibidas):

| ★ | Chamada | Resultado |
| --- | --- | --- |
| 20 Detecção pelo coletor | `GET /api/coletor/configuracao` (credencial do coletor) e `GET /api/falhas` | 200; 12 dispositivos atribuídos; 43 ocorrências detectadas (INDISPONIBILIDADE e INSTABILIDADE) |
| 22 Diagnóstico | `GET /api/falhas/<id>` | 200; estado DISPONIVEL, causas LOCALIZADA e RECORRENTE, 3 recomendações |
| 24 Prejuízo estimado | mesmo detalhe | R$ 115,91 com a conta aberta (`1 pessoa × R$ 23,18/h × 50% × 10,0 h de expediente`) |
| 25 Explicar com IA | `POST /api/falhas/<id>/explicacao-ia` (única chamada de IA) | 200, `gemini-3.5-flash-lite`, 1.184 caracteres, com aviso |
| 26 Dashboard com ranking de custo | `GET /api/dashboard` | 200; total R$ 956,25; ranking com 5 dispositivos |
| 27 Relatório | `GET /api/relatorios/exportar` | 200; ZIP com `dispositivos.csv`, `metricas.csv`, `falhas.csv`, `diagnosticos.csv`, `leia-me.json` |

## Pontos fracos encontrados

Nenhum afeta a nota estimada, mas um professor exigente pode apontar:

1. ~~**Fórmula do custo/hora repetida no frontend**~~ — ✅ **corrigido**. A prévia em `frontend/src/pages/Empresa.js` agora pergunta ao servidor (`POST /api/empresa/custos/previa` → `EmpresaController.simular_custos` → `SimularCustoHoraService`), que usa a mesma `CalculadoraPrejuizo.custo_hora_de` do restante do sistema e os padrões do Model (`Empresa.FATOR_ENCARGOS_PADRAO`, `Empresa.HORAS_MES_PADRAO`). Nada é salvo. Testes em `tests/test_costs.py` (fórmula, padrões, validação, técnico recebe 403) e no teste de integração do frontend.
2. **Padrões repetidos no frontend** (`Empresa.js`): com o campo vazio, envia fator `1.7` e `220` h, os mesmos padrões do Model `Empresa`. Mudar para "não enviar" alteraria o comportamento (manteria o valor anterior em vez de voltar ao padrão); **não foi feito**.
3. ~~**Controller chamando dois Services**~~ — ✅ **corrigido**. `FalhaController.registrar_impacto` e `explicar_com_ia` agora chamam um único Service, que recebe o id e o corpo JSON, busca a ocorrência primeiro (`ObterFalhaService.buscar`) e só depois valida o payload, mantendo o 404 de outra empresa antes do 400. Regra nova em `tests/test_architecture.py` (`test_each_controller_method_calls_a_single_service`) e regressão da ordem em `tests/test_costs.py`; fluxogramas 3 e 6 atualizados.
4. **Capturas de página inteira**: o menu lateral não acompanha a altura total da página na captura (só na captura; na tela real ele é fixo).

Código morto: nenhum resto de `app/api.py`, `app/models.py` ou `app/services/` (nem `__pycache__` órfão); nenhuma classe ou método de Repository sem uso.

## Corrigido nesta auditoria

- README: seção **"Casos de uso e telas"** (6 casos com as telas) e prova do **cliente-servidor** com comandos.
- `docs/img/telas/`: 12 capturas das telas com dados fictícios, reproduzíveis por `frontend/tests/support/telas.mjs`.
- `backend/tests/test_readme.py`: novo teste que falha se algum link relativo do README apontar para arquivo inexistente.
- Este documento.

## Depende da equipe

- [ ] **Vídeo de até 5 minutos** (obrigatório): pitch (problema, público, solução) + demonstração das ★. Roteiro cronometrado: [docs/ROTEIRO_VIDEO.md](ROTEIRO_VIDEO.md).
- [ ] **Slides e pitch** para 07/11 (as imagens de `docs/img/` servem para os slides).
- [ ] **Ensaio** com cronômetro, incluindo um plano B se a Internet falhar (vídeo gravado).
- [ ] **Renovar o PythonAnywhere antes de 07/11** (aba Web → "Run until 1 month from today").
- [ ] **Entregar as credenciais de demonstração ao professor pelo Classroom** (nunca no repositório).
- [ ] Decidir sobre os pontos fracos 1 e 2 (se quiserem corrigir antes de 23/10).
- [ ] Gravar o vídeo seguindo [docs/ROTEIRO_VIDEO.md](ROTEIRO_VIDEO.md).
