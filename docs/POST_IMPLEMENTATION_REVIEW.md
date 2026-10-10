# EdgeHealth — revisão pós-implementação

# Revisão de 06/10/2026 (atual)

Branch `feat/edgehealth-mvp`, publicada em `origin`, ponto de partida no commit `4320fb6`. A PR #1 (`feat/edgehealth-mvp` → `main`) está aberta. Ambiente: Windows 11, Python 3.12.10, Node 22. O trabalho de 09/09 foi preservado; nenhuma migration aplicada foi alterada.

## O que esta etapa acrescentou

| Bloco | Entrega | Evidência |
|---|---|---|
| Coletor remoto e ingestão HTTPS | Entidade `Coletor` por empresa; credencial `ehc_` exibida uma vez e guardada como hash SHA-256; rotação e revogação; `GET /api/coletor/configuracao` só com os dispositivos atribuídos; `POST /api/coletor/amostras` com UUID por amostra (índice único `coletor_id, amostra_uid`), timestamps de coleta e recebimento, rejeição de horário futuro (mais de 120 s) e de amostras antigas (mais de 24 h), lote de até 200 itens e 512 KB, 120 requisições/min, heartbeat e estado ATIVO/DESATUALIZADO/NUNCA_CONECTADO/REVOGADO | `services/collectors.py`, `api.py`, `test_collectors.py` |
| Regras únicas | A ingestão usa o mesmo `claim_device` (lease) e o mesmo `record_result` do worker. O cliente não envia status, severidade nem empresa: campos extras são rejeitados | `services/monitoring.py` |
| Coordenação worker × coletor | `Dispositivo.coletor_id`: o worker local ignora dispositivos atribuídos a um coletor | `run_cycle`, `collect_device`, `test_local_worker_never_probes_remote_devices` |
| Fora de ordem | Amostra mais antiga que a última processada é gravada com `fora_de_ordem=True` e status instantâneo, sem mexer em contadores, estado ou ocorrências | `record_result`, teste de amostra atrasada |
| Problemas do coletor | `PERMISSAO_ICMP`/`FALHA_COLETOR` registram o erro, sem amostra nem falha. O coletor parado aparece como DESATUALIZADO, sem gerar OFFLINE | `test_collector_problems_are_not_device_failures` |
| Cliente coletor | `collector/edgehealth_collector.py` (stdlib + icmplib): fila em disco limitada, backoff exponencial com jitter, idempotência, heartbeat, aviso de relógio, HTTPS obrigatório, saída com código 2 se a credencial for revogada, logs sem segredo | `test_collector_client.py` (servidor HTTP real) |
| Termos e privacidade | Aceite com versão e data (separado de consentimento), bloqueio 403 até o aceite, minutas públicas, retenção (`purge-history`), anonimização (`anonymize-user`), backup verificado (`backup`) | `test_privacy_operations.py`, `docs/LGPD.md` |
| Hospedagem | `ProxyFix` configurável (`TRUST_PROXY`), HSTS com `COOKIE_SECURE`, Dockerfile, compose e entrypoint com migrations | `docs/DEPLOY.md` |
| Interface | Tela **Coletores** (cadastro, credencial única, rotação, revogação), origem da medição no dispositivo, estado do coletor na lista e no dashboard, aceite dos Termos no cadastro e no primeiro acesso | `Coletores.js`, `Dispositivos.js`, `Dashboard.js`, `Login.js`, `app.js` |
| Relatórios | `metricas.csv` com `coletor_id`, `recebida_em` e `fora_de_ordem`; `dispositivos.csv` com o coletor | `reports.py` |

**Problema encontrado e corrigido:** a migration gerada automaticamente usava *batch mode*, que recria `dispositivos` e `metricas`. Em um banco com histórico, o SQLite recusa `DROP TABLE dispositivos` (FOREIGN KEY constraint failed). Trocado por `ALTER TABLE ADD COLUMN ... REFERENCES` no SQLite, sem recriar tabelas. O teste `test_upgrade_from_previous_release_preserves_history` reproduz a falha e comprova a correção.

## Testes e resultados reais desta execução

| Verificação | Resultado |
|---|---|
| `python -m pytest --cov=app -q` (backend) | **46 aprovados, 2 pulados** (rede real opcional); cobertura **94%** |
| `EDGEHEALTH_TEST_REAL_NETWORK=1 python -m pytest -m real_network` | **2 aprovados**: ICMP de loopback e coletor remoto real → HTTP → servidor |
| `npm test` (inclui `npm run build`) | Build aprovado (20 módulos); **16 aprovados**, incluindo o fluxo da tela Coletores e as páginas legais servidas pelo Flask |
| Migrations | Banco vazio → `bc4dfbaec175`; reaplicação; `db check` sem divergências; downgrade/upgrade em banco vazio; **atualização de `7c7ba005affc` com dados** sem perda e `foreign_key_check` vazio |
| Ponta a ponta sem mocks (Waitress + processo coletor + ICMP real) | Loopback e gateway da LAN de teste ONLINE (0,958 ms, 0% perda); `192.0.2.1` (RFC 5737) OFFLINE após 3 ciclos, **1** falha, diagnóstico LOCALIZADA, 2 recomendações; dashboard e ZIP coerentes (`DEPLOY.md` §7) |
| `flask probe` no gateway | 4/4 pacotes; o `ping` do sistema confirma <1 ms. A granularidade do relógio no Windows é de cerca de 0,5 ms |
| Busca por TODO/mock/fake/random no produto | Só usos legítimos: placeholders de formulário, jitter de backoff e o hash de comparação de tempo constante no login |
| Docker | **Não executado**: Docker não instalado nesta máquina |

## Matriz RF01–RF20 (06/10/2026)

✅ completo e testado de ponta a ponta no escopo validado · 🟡 parcial · ⚠️ implementado com problema importante · ❌ ausente.

| RF | Status | Backend / persistência / API | Frontend | Testes e evidência | Limitação restante |
|---|---|---|---|---|---|
| RF01 Empresa | ✅ | `create_company_account`, `Empresa`, `POST /auth/registro` (exige aceite) | `Login.js`, `Empresa.js` | `test_auth_and_crud`, integração UI | — |
| RF02 Usuários | ✅ | `save_user`, empresa da sessão, papéis | `Usuarios.js` | `test_auth_and_crud`, `test_tenants_reports` | — |
| RF03 Login | ✅ | scrypt, sessão hash, expiração, revogação, CSRF, limite, cookie `Secure` com HTTPS | `Login.js`, logout | `test_auth_and_crud`, `test_proxy_and_secure_cookie_configuration` | — |
| RF04 Cadastro dispositivo | ✅ | `save_device`, validação de IP, origem da medição validada por empresa | `Dispositivos.js` | testes CRUD e coletor | — |
| RF05 Edição | ✅ | troca de IP reinicia o estado; bloqueada com ocorrência aberta; troca de origem reagenda | `Dispositivos.js` | testes CRUD/coletor, UI | — |
| RF06 Exclusão | ✅ | arquivamento preserva histórico, encerra ocorrência (ARQUIVAMENTO) e para a coleta (worker e configuração do coletor) | confirmação na UI | `test_monitoring`, UI | — |
| RF07 Listagem | ✅ | estados auxiliares: aguardando coleta, desatualizado, erro de coleta, estado do coletor | tabela | UI | — |
| RF08 Disponibilidade real | 🟡 | `real_probe` e cliente coletor; distingue sem resposta de erro do coletor | status | ICMP real aprovado em loopback, no gateway e em endereço inalcançável | Falta homologar na rede de demonstração com queda e recuperação de equipamento autorizado |
| RF09 Latência real | 🟡 | `latencia_ms` nula sem resposta; timestamps de coleta e recebimento | métricas e gráfico | real: 0,958 ms no gateway | Idem RF08; granularidade de cerca de 0,5 ms no Windows |
| RF10 Perda real | 🟡 | `(enviados-recebidos)/enviados` com consistência validada no servidor | métricas e gráfico | real: 0% e 100% | Idem RF08 |
| RF11 Status | ✅ | `classify` com confirmações; limites em `config.py` | badges | `test_monitoring`, `test_collectors` | ICMP bloqueado ≠ desligado (documentado) |
| RF12 Falhas automáticas | ✅ | índice único de ocorrência aberta + lease; reenvio idempotente | histórico | ingestão concorrente, reenvio, ciclo completo via coletor | Recuperação real pendente (RF08) |
| RF13 Histórico | ✅ | filtros e paginação | `Historico.js` | UI | — |
| RF14 Severidade | ✅ | duração, grupo e usuários informados, com justificativa persistida | detalhe | `test_diagnostic_rules` | — |
| RF15 Diagnóstico | ✅ | `analyze` com janela, pares, histórico e atualidade | `Falha.js` | testes de regras; real: LOCALIZADA | — |
| RF16 Causas | ✅ | 5 regras e insuficiência, como hipóteses | detalhe | idem | Sem topologia (por escopo) |
| RF17 Recomendações | ✅ | catálogo com seed idempotente e associação N:N | detalhe | real: 2 recomendações | — |
| RF18 Impacto | ✅ | duração calculada × estimativa manual × desconhecido | formulário | `test_monitoring`, UI | — |
| RF19 Dashboard | ✅ | indicadores, séries, desatualização e coletores | `Dashboard.js` | UI (datasets), `test_collectors` | — |
| RF20 Relatórios | ✅ | ZIP com 4 CSV + metadados, filtros, empresa, BOM UTF-8, anti-fórmula | `Relatorios.js` | `test_isolation_reports`, UI, ponta a ponta | — |

**Estados distintos:** código preparado ✅ · testes automatizados ✅ · ICMP real em laboratório ✅ · homologação na rede da demonstração com queda e recuperação **pendente** · implantado **não** · acessível publicamente **não**.

## Backlog TASK-001–TASK-032

Os títulos individuais não foram recuperados; a documentação anterior só guarda os **agrupamentos** reproduzidos na seção de 09/09, abaixo. Situação atual por grupo:

- TASK-001–TASK-014 e TASK-019–TASK-031: concluídas na revisão anterior. Foram revalidadas pela suíte desta execução e não houve regressão.
- TASK-015–TASK-018 (coleta real, persistência, periodicidade, classificação): passam de 🟡 para **✅ em laboratório**, com ICMP real nesta máquina. O aceite de campo segue no roteiro de RF08.
- TASK-032 (aceite e regressão): **✅ automatizado**; o teste real, que antes falhava por permissão, agora passa. Pendente apenas o roteiro de demonstração em campo.

## Novas tarefas

| ID | Tarefa | Estado |
|---|---|---|
| CLOUD-001 | Modelo e migration de coletor, origem por dispositivo e metadados de ingestão | ✅ |
| CLOUD-002 | Credencial do coletor: hash, rotação, revogação e exibição única | ✅ |
| CLOUD-003 | API de configuração, ingestão idempotente e heartbeat | ✅ |
| CLOUD-004 | Amostras atrasadas ou fora de ordem e limites de tempo | ✅ |
| CLOUD-005 | Coordenação worker × coletor (lease compartilhado) | ✅ |
| CLOUD-006 | Cliente coletor com fila, backoff, HTTPS e logs sem segredo | ✅ |
| CLOUD-007 | Telas Coletores, origem da medição e estado no dashboard | ✅ |
| CLOUD-008 | Dockerfile, compose, entrypoint com migrations e health | 🟡 escrito; não construído (sem Docker) |
| CLOUD-009 | Implantação em provedor | ❌ depende de decisão e autorização da equipe |
| CLOUD-010 | PostgreSQL (somente se o provedor exigir) | ❌ não iniciado; justificativa em `DEPLOY.md` §2 |
| LGPD-001 | Inventário de dados, bases sugeridas e retenção | ✅ minuta |
| LGPD-002 | Termos de Uso e Aviso de Privacidade públicos | ✅ minutas; revisão humana pendente |
| LGPD-003 | Registro de aceite e ciência por versão, separado de consentimento | ✅ |
| LGPD-004 | Retenção (`purge-history`) e anonimização (`anonymize-user`) | ✅ |
| LGPD-005 | Procedimentos de titulares e de incidentes | ✅ minuta |
| LGPD-006 | Definir controlador, encarregado, contatos e provedores | ❌ informação externa |
| HARDENING-001 | ProxyFix, HSTS, cookie `Secure` com HTTPS | ✅ |
| HARDENING-002 | Migration segura em SQLite com histórico | ✅ |
| HARDENING-003 | Backup verificado e procedimento de restauração | ✅ |
| HARDENING-004 | Rate limit e tamanho de lote do coletor | ✅ |

## Estimativa de conclusão por área (pelo comportamento validado)

| Área | Estimativa | Fundamento |
|---|---:|---|
| Monitoramento e coleta | 90% | ICMP real e pipeline de ponta a ponta validados em laboratório; falta a queda e recuperação real na rede da demonstração |
| Persistência e histórico | 95% | Migrations do zero e de atualização com dados; retenção. Sem PostgreSQL |
| Falhas, severidade, diagnóstico e recomendações | 95% | Regras testadas e exercitadas com dados reais; recuperação real pendente |
| Segurança e isolamento | 95% | Sessão, coletor, CSRF, isolamento e limites testados. Sem pentest externo, por escopo |
| Interface | 90% | Fluxos testados por DOM/HTTP; falta homologação visual nos navegadores da apresentação |
| Arquitetura hospedada | 70% | Caminho funcional validado sem contêiner; imagem não construída; nada implantado |
| Privacidade / LGPD | 70% | Medidas técnicas implementadas; documentos são minutas sem responsáveis definidos |

---

# Revisão anterior (09/09/2026), mantida como histórico

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
3. **Publicação no GitHub** (*superado em 06/10/2026: a branch foi publicada em `origin` e a PR #1 foi aberta; texto original abaixo*): o código está no commit local `f2a7dfe`, branch `feat/edgehealth-mvp`, e o usuário autorizou explicitamente a publicação. O plugin GitHub foi conectado: leitura do repositório e permissão de escrita da conta foram confirmadas. A criação da árvore Git pela integração retornou `403: Resource not accessible by integration`; não foi criada branch nem commit remoto. O usuário concluiu o fluxo do GitHub CLI no navegador, mas o ambiente bloqueou `https://api.github.com:443` antes de salvar a sessão. A política também recusou a ampliação de permissões de execução/rede. `gh auth status` confirmou ausência de sessão salva. O envio exige um ambiente com acesso autorizado à API do GitHub; foi preparado um bundle dos commits para publicação no computador da equipe. Repetir o login aqui sem resolver o bloqueio não conclui a autenticação. A autorização de envio permanece concedida. Isso não altera os resultados dos testes ou o código local.

CSV atende ao formato autorizado. Impacto manual identificado, ausência de descoberta de topologia, um ponto coletor e ausência de retenção automática são decisões de escopo documentadas; não foram substituídas por estimativas inventadas. A duração é da ocorrência observada, não uma medida contínua exata de downtime.

## Execução e demonstração

Os comandos completos para Linux/macOS e Windows, configuração, criação/aplicação do banco, worker e build estão no [README](../README.md). O [roteiro de demonstração](DEMO.md) cobre cadastro, coleta contínua sem navegador, queda, ausência de duplicação, recuperação, diagnóstico, impacto, dashboard, relatório e isolamento por empresa. O MVP da turma está marcado para 23/10/2026, 44 dias após esta revisão.
