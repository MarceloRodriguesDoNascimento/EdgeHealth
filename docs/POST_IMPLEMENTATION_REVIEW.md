# EdgeHealth — revisão pós-implementação

Data: **09/09/2026**. Branch local: `feat/edgehealth-mvp`. Base: `fc60d981e783270e3d6caeed72f88bd1d9e91029`.

## Resultado e escopo

A execução foi retomada após inspecionar `git status`, `git diff`, alterações existentes e testes. Foram preservados os services, entidades, migração inicial e telas já desenvolvidos. Na retomada, havia 23 testes backend aprovados e um teste ICMP opcional pulado; o fechamento acrescentou validação de banco novo, importação legada, regressões e integração HTTP da interface.

O produto implementa o fluxo: scheduler independente → ICMP real → amostra histórica → status com confirmação → uma ocorrência aberta por dispositivo → impacto/severidade → diagnóstico explicável → causas/recomendações → histórico/dashboard/exportação. Não contém gerador de métricas fictícias. O adaptador controlado existe apenas nas suítes de teste.

**Aceite final: 17 RF completos, 3 com homologação de campo pendente, nenhum ausente.** RF08–RF10 possuem código e testes controlados, mas o socket ICMP real foi rejeitado pelo ambiente. Não foram contabilizados como integralmente homologados. Os requisitos posteriores foram validados com entradas determinísticas no pipeline, não com uma campanha de medição real nesta máquina.

## TASK-001–TASK-032

A rastreabilidade abaixo usa os agrupamentos de tarefas definidos na instrução de implementação aprovada. Não renumera o backlog nem atribui títulos individuais não recuperados da auditoria anterior.

| TASKs | Entrega do escopo aprovado | Situação e evidência |
|---|---|---|
| TASK-001 | Consolidar a versão oficial | ✅ Somente `backend/` e `frontend/`; cópias antigas removidas da árvore ativa, preservadas no Git |
| TASK-002 | Entrada frontend e HTTP | ✅ `frontend/index.html`, `vite.config.js`, `src/services/api.js`; 204, erros, proxy e build verificados |
| TASK-003 | Configuração, dependências e execução | ✅ `app/config.py`, `.env.example`, manifests/locks, testes isolados e README |
| TASK-004 | Modelo, migrations e integridade | ✅ `models.py`, `extensions.py`, duas revisões Alembic, importação conservadora e teste de banco vazio |
| TASK-005 | Hash de senha | ✅ scrypt, ausência de senha em respostas, regressão de espaços na senha |
| TASK-006 | Login, sessão e logout | ✅ Sessões revogáveis, cookies, CSRF e expiração em `services/auth.py` |
| TASK-007 | Isolamento entre empresas | ✅ Filtros e validação de IDs em APIs, agregações, detalhes e ZIP; testes A/B |
| TASK-008 | Validação e erros | ✅ E-mail, CNPJ numérico/alfanumérico, IP, payload, duplicidades e rollback |
| TASK-009–TASK-013 | Cadastros RF01–RF07 | ✅ API/banco/telas de empresa, equipe, login e dispositivos; testes DOM com HTTP real |
| TASK-014 | Contrato de amostra histórica | ✅ `Metrica`: dispositivo, timestamp, resposta, latência, contagens, perda e status |
| TASK-015–TASK-018 | Coleta real, persistência, periodicidade e classificação | 🟡 Implementados e validados com adaptador injetado; homologação do ICMP real bloqueada pelo SO. Classificação da TASK-017 e exclusão de coleta simultânea verificadas |
| TASK-019–TASK-020 | Ciclo de vida de falhas | ✅ Abre/atualiza/encerra/reabre, índice único e histórico preservado |
| TASK-021 | Histórico | ✅ API filtrada/paginada e `Historico.js` |
| TASK-022 | Impacto | ✅ Duração automática da ocorrência e estimativa manual identificada |
| TASK-023 | Severidade | ✅ Tempo, grupo, usuários, condição e justificativa; limites testados |
| TASK-024 | Diagnóstico gerado | ✅ Evidências, causas, versão/momento e vínculo com falha persistidos |
| TASK-025 | Causas por regras | ✅ Localizada, compartilhada, congestionamento, latência, recorrência e insuficiência |
| TASK-026 | Catálogo e recomendações | ✅ Oito ações persistidas por seed idempotente e vínculo com diagnóstico |
| TASK-027 | Detalhe da ocorrência | ✅ `Falha.js`: timeline, impacto, severidade, diagnóstico, causas, recomendações e evidências |
| TASK-028 | Séries históricas | ✅ Filtros de dispositivo/período/tipo, paginação, ordem cronológica e índice |
| TASK-029 | Dashboard | ✅ Indicadores e dois gráficos a partir da API, atualização periódica e contagem total de amostras |
| TASK-030–TASK-031 | Exportação e tela | ✅ ZIP com quatro CSVs, metadados, filtros, conteúdo conferido e download real pela tela |
| TASK-032 | Testes de aceite e regressão | 🟡 Suítes determinísticas/HTTP aprovadas; único teste real de ICMP falhou por permissão externa |

Nenhum bloco ficou sem implementação. A situação parcial refere-se ao aceite de campo, sem maquiar o teste que falhou.

## Arquivos criados, alterados e consolidados

A lista completa está em [CHANGE_MANIFEST.md](CHANGE_MANIFEST.md). Núcleo adicionado: `app/api.py`, `cli.py`, `extensions.py`, `models.py`, `validation.py` e services de autenticação, cadastros, coleta, diagnóstico, catálogo, consultas, serialização, relatórios e importação legada. Foram acrescentadas migrations, fixtures e testes de domínio, isolamento, migrations e interface HTTP.

Arquivos existentes completados: fábrica Flask, configuração, dependências, ponto de execução, entrada do frontend, aplicação, cliente HTTP, login, dispositivos e dashboard. Novas telas: empresa, usuários, histórico, detalhe e relatórios. Estilos e utilitários DOM cobrem loading, erro, confirmação, feedback e layout responsivo.

As antigas cópias `backend/backend/` e `0.1/EdgeHealth/`, bytecode e bancos versionados deixaram a árvore ativa. O banco operacional novo não é versionado. A importação não apaga a origem antiga nem a transforma em métricas reais; consulte [LEGACY.md](LEGACY.md).

## Banco e arquitetura

| Relação | Implementação |
|---|---|
| Empresa → Usuário | FK obrigatória, índice, exclusão restrita |
| Empresa → Dispositivo | FK obrigatória; IP ativo único na empresa |
| Dispositivo → Métrica | FK obrigatória, índice dispositivo/data, histórico separado do cache atual |
| Dispositivo → Falha | FK, índice de início, uma aberta por dispositivo |
| Falha → Diagnóstico | FK única; atualização da análise e preservação na recuperação |
| Falha → Impacto | FK única; quantidade desconhecida ou informada, origem e observação |
| Diagnóstico → Recomendações | Associação N:N com PK composta e catálogo persistido |

Enums são restringidos por checks; há validações de contagens, perda, latência, estado e datas. Sessões armazenam hashes de tokens. `registros_legados` preserva referências e dados anteriores, removendo credenciais e isolando observações não verificáveis. Somente operadores locais podem exportar esse arquivo de revisão; não há API desse conteúdo.

Migrations `55463d3f0b18` e `7c7ba005affc` foram aplicadas do zero em SQLite temporário. Segunda aplicação idempotente, `db check` sem divergências, FKs ativadas e `PRAGMA foreign_key_check` vazio. O endpoint de health compara schema/revisões com a versão atual.

## Segurança

Hash scrypt, sessão HttpOnly/SameSite, CSRF, validade, revogação e limitação de login foram exercitados. E-mail e senha não concedem acesso a uma empresa escolhida pelo cliente: o vínculo vem da sessão. Testes verificam leitura/edição/arquivamento/coleta, métricas, falhas, diagnóstico, impacto, dashboard, relatórios e payloads adulterados entre empresas A e B.

Não há senha/token em JSON público ou localStorage. Elementos de interface usam texto seguro; exportação protege contra fórmulas de planilha. Usuários técnicos não gerenciam empresa/equipe. O catálogo global não contém dados de clientes. O comando administrativo local de recuperação de conta pressupõe acesso confiável ao servidor; não é endpoint web.

## Monitoramento e regra de negócio

`real_probe()` valida IP, executa `icmplib.ping` com timeout e produz contagens/latência reais. `collect_device()` reserva lease, libera a transação durante ICMP e persiste o pipeline de forma transacional. `run_cycle()` limita concorrência; `flask monitor` funciona sem navegador. Não há scheduler no reloader da API.

`ProbeResult` diferencia falta de resposta de impossibilidade do coletor executar a medição. Ausência de resposta gera perda baseada nas contagens e latência desconhecida. Erro de socket não altera o dispositivo para OFFLINE nem cria métricas fictícias.

`classify()` aplica thresholds e confirmações. `record_result()` mantém uma ocorrência aberta, encerra na recuperação e abre outra numa nova queda. Impacto começa desconhecido; a duração é da ocorrência observada, incluindo instabilidade/confirmação, e não downtime contínuo de precisão maior que a sondagem.

`recalculate_severity()` usa duração, grupo e usuários informados. `analyze()` considera métricas recentes, pares da mesma empresa e histórico; não presume topologia. Evidência insuficiente é um estado válido. Causas são hipóteses explicáveis e recomendações são recuperadas do catálogo. Dados de pares desatualizados não sustentam a hipótese de indisponibilidade compartilhada.

## Correções da retomada

- Preservação dos espaços significativos da senha no login.
- Confirmação de arquivamento permanece utilizável após erro assíncrono.
- Recuperação não apaga o diagnóstico que será apresentado na ocorrência encerrada.
- Importação legada somente em destino vazio, origem somente leitura e observações não verificáveis separadas.
- Filtros contendo apenas data final calculam início relativo à data escolhida.
- Métricas paginadas na interface e seleção de campos conforme tipo solicitado.
- Dashboard ignora respostas antigas de requisições concorrentes.
- Health verifica migrations atuais; configuração Alembic sem API depreciada.
- Validação de CNPJ aceita o padrão numérico e o alfanumérico, com teste do exemplo oficial.

## Dependências

| Dependência direta | Versão | Uso |
|---|---:|---|
| Flask | 3.1.3 | API/fábrica/CLI |
| Flask-SQLAlchemy | 3.1.1 | Sessão do ORM |
| SQLAlchemy | 2.0.52 | Persistência, transações e constraints |
| Flask-Migrate | 4.1.0 | Alembic/migrations |
| python-dotenv | 1.2.3 | Configuração por ambiente |
| icmplib | 3.0.4 | Sondagem ICMP real |
| waitress | 3.0.2 | Servidor WSGI |
| pytest | 9.1.1 | Testes backend |
| pytest-cov | 7.0.0 | Cobertura de linhas |
| Vite | 8.2.2 | Dev server, proxy e build |
| Chart.js | 4.5.1 | Gráficos |
| jsdom | 26.1.0 | Testes DOM da interface |

`requirements-dev.lock` fixa 24 dependências, incluindo transitivas do ambiente validado. `package-lock.json` fixa a árvore npm. Relatórios usam CSV/ZIP da biblioteca padrão Python, sem biblioteca extra de PDF.

## Testes executados e resultados reais

| Verificação | Resultado |
|---|---|
| Backend: `python -m pytest --cov=app --cov-report=term-missing -q` | **30 aprovados, 1 pulado**; **93%** de cobertura de linhas |
| Frontend: `npm test` | **15 aprovados**, incluindo oito cenários HTTP integrados, sua suíte e seis testes DOM/unitários |
| Build: `npm run build` (também pretest) | Aprovado; 19 módulos, bundle JS ≈226,45 kB e CSS ≈12,19 kB |
| `npm ci --no-audit --no-fund` | Instalação limpa aprovada, 58 pacotes |
| Backend em ambiente virtual novo, lock com 24 pacotes | Reinstalação offline dos wheels disponíveis aprovada após interrupção da tentativa de rede |
| `python -m pip check` | Sem dependências quebradas |
| Migrations em SQLite vazio e reaplicação | Aprovadas; sem diferenças entre modelos e schema |
| Importação do protótipo | Origem SHA-256 inalterada, credenciais removidas, histórico em quarentena, contas desativadas e recuperação testada |
| Interface → API HTTP → SQLite migrado | Cadastros, sessão, equipe, CRUD, pipeline, histórico, impacto, gráficos e ZIP aprovados |
| Vite → API e Flask → build | Proxy e assets do build aprovados |
| ICMP real habilitado explicitamente | **1 falhou, 30 desmarcados**: `PermissionError` / `SocketPermissionError` ao abrir socket |
| Revisão visual | Login e cadastro inspecionados no navegador; demais fluxos exercitados por DOM/HTTP |
| `git diff --check` | Sem erros de whitespace |

A instalação de validação foi separada da `.venv` de desenvolvimento, em `edgehealth-validation-venv`. A suíte frontend também usou esse Python via `EDGEHEALTH_PYTHON`. Os wheels usados offline vieram do cache de instalação; não houve substituição por implementações falsas das dependências.

Cobertura de linhas não mede a completude funcional nem prova comportamento de ICMP no ambiente de destino. A coleta da integração é injetada por stdin no runner de testes, sem endpoint de simulação em produção. O canvas do jsdom é uma superfície controlada de desenho; os datasets dos gráficos são verificados contra a API real. Não se afirma aprovação visual completa de todos os navegadores.

### Evidências principais por suíte

- `test_auth_and_crud.py`: hash, login/logout, CSRF, expiração, papéis, desativação, payloads, duplicidades, CRUD, FKs, CNPJ e senha com espaços.
- `test_isolation_reports.py` e `test_tenants_reports.py`: limites entre empresas, agregações, filtros, ordem, conteúdo dos CSVs e proteção contra fórmulas.
- `test_monitoring.py`: contrato do adaptador, erros/timeouts, persistência, scheduler, lease concorrente, status, falha sem duplicação, recuperação e histórico.
- `test_diagnostic_rules.py`: regras localizada/compartilhada/latência/recorrência, evidência recente, preservação na recuperação e limites de severidade/grupo.
- `test_legacy_and_migrations.py`: instalação do zero, comparação Alembic/modelos, catálogo idempotente, integridade e migração de dados legados.
- `frontend/tests/integration.test.js`: todas as telas de negócio com API HTTP e SQLite migrado, sem respostas HTTP mockadas.
- `frontend/tests/ui.test.js`: XSS, submissão, erros, CSRF, 204, sessão expirada e confirmação com falha.

## Matriz RF01–RF20

✅ completo no código e nas verificações aplicáveis; 🟡 aceite parcial por limitação explicitada; N/A quando não há tela própria. Em RF08–RF10, backend/banco existentes não significam homologação ICMP concluída.

| RF | Requisito | Backend | Banco | Frontend | Integração | Testes | Status | Evidência |
|---|---|---|---|---|---|---|---|---|
| RF01 | Cadastro de empresas | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | `management.create_company_account`, `Empresa`, `Login.js`, `Empresa.js` |
| RF02 | Cadastro de usuários | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | `management.save_user`, `Usuario`, `Usuarios.js` |
| RF03 | Login | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | `auth.login/issue_session/require_auth`, `AuthSession`, `Login.js` |
| RF04 | Cadastro de dispositivos | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | `management.save_device`, `Dispositivo`, `Dispositivos.js` |
| RF05 | Edição de dispositivos | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | `PUT /dispositivos/{id}`, validação de IP/lease/vínculo |
| RF06 | Exclusão/arquivamento | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | `archive_device`, soft delete, confirmação e histórico preservado |
| RF07 | Listagem | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | `GET /dispositivos`, tabela e status/ausência/desatualização |
| RF08 | Disponibilidade real | ✅ | ✅ | ✅ | 🟡 | 🟡 | 🟡 | `real_probe`, `collect_device`; ICMP bloqueado pelo SO |
| RF09 | Latência real histórica | ✅ | ✅ | ✅ | 🟡 | 🟡 | 🟡 | `ProbeResult.latency_ms`, `Metrica`; sem sondagem real aprovada |
| RF10 | Perda real de pacotes | ✅ | ✅ | ✅ | 🟡 | 🟡 | 🟡 | Contagens e `ProbeResult.loss`; falta aceite em rede acessível |
| RF11 | ONLINE/INSTAVEL/OFFLINE | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | `classify`, confirmação/recuperação e API/UI |
| RF12 | Falhas automáticas | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | `record_result`, índice de ocorrência aberta e teste de ciclo |
| RF13 | Histórico de falhas | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | `failure_query/paginate`, `Historico.js` |
| RF14 | Severidade | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | `recalculate_severity`, justificativa e cenários de limites |
| RF15 | Diagnóstico lógico | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | `analyze`, evidências persistidas e `Falha.js` |
| RF16 | Possíveis causas | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Cinco regras e estado de insuficiência |
| RF17 | Recomendações | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | `seed_catalog`, N:N e exibição no detalhe |
| RF18 | Impacto | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | `Impacto`, duração derivada, `PUT /falhas/{id}/impacto` |
| RF19 | Dashboard | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | `queries.dashboard`, `Dashboard.js`, datasets/indicadores conferidos |
| RF20 | Relatórios | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | `export_report`, ZIP/CSV filtrado e `Relatorios.js` |

## Pendências externas e limites

1. **RF08–RF10 / aceite de rede:** executar o teste real e o roteiro na máquina/LAN da equipe. Exige permissão ICMP do SO e conectividade aos alvos. O teste real deste ambiente falhou na criação do socket, antes de enviar pacotes; não há alteração de regra de negócio que transforme esse resultado em medição confiável.
2. **Homologação de navegação final:** validar os navegadores usados pela equipe. Os fluxos autenticados foram testados em DOM/HTTP; o ambiente de visualização não compartilha a rede do processo Flask externo, limitando a inspeção visual autenticada. O proxy Vite foi validado separadamente no teste HTTP real.
3. **Publicação no GitHub:** o código está no commit local `f2a7dfe`, branch `feat/edgehealth-mvp`, e o usuário autorizou explicitamente a publicação. O plugin GitHub foi conectado: leitura do repositório e permissão de escrita da conta foram confirmadas. A criação da árvore Git pela integração retornou `403: Resource not accessible by integration`; não foi criada branch nem commit remoto. O terminal continua sem credenciais (`could not read Username for 'https://github.com'`). O próximo passo é autenticar o GitHub CLI pelo fluxo oficial no navegador para enviar os commits locais preservados. A autorização de envio permanece concedida. Isso não altera os resultados dos testes ou o código local.

CSV atende ao formato autorizado. Impacto manual identificado, ausência de descoberta de topologia, um ponto coletor e ausência de retenção automática são decisões de escopo documentadas; não foram substituídas por estimativas inventadas. A duração é da ocorrência observada, não uma medida contínua exata de downtime.

## Execução e demonstração

Os comandos completos para Linux/macOS e Windows, configuração, criação/aplicação do banco, worker e build estão no [README](../README.md). O [roteiro de demonstração](DEMO.md) cobre cadastro, coleta contínua sem navegador, queda, ausência de duplicação, recuperação, diagnóstico, impacto, dashboard, relatório e isolamento por empresa. O MVP da turma está marcado para 23/10/2026, 44 dias após esta revisão.
