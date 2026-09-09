# EdgeHealth

Monitoramento e diagnóstico lógico de redes para pequenas e médias empresas. Inventário por empresa, amostras ICMP históricas, ocorrências com ciclo de vida, impacto, diagnóstico por regras, recomendações, dashboard e exportação CSV.

A implementação oficial está em `backend/` e `frontend/`. As cópias divergentes foram consolidadas; o histórico anterior permanece no Git. Não há seed de usuários, dispositivos, métricas ou falhas no produto.

**Validação de 09/09/2026:** regras, persistência, autenticação, isolamento e interface com API HTTP real foram testados. A homologação do ICMP real está pendente em uma máquina com permissão de socket e acesso à LAN. Aqui, o sistema operacional rejeitou o socket ICMP; o coletor registra o erro sem inventar métricas. Consulte [a revisão final](docs/POST_IMPLEMENTATION_REVIEW.md) e [a demonstração](docs/DEMO.md).

## Arquitetura

```mermaid
flowchart TD
  UI["Navegador: JavaScript e Chart.js"] -->|"mesma origem /api"| API["Flask: sessão e autorização"]
  API --> DB["SQLite: cadastros e histórico"]
  WORKER["Worker independente: flask monitor"] -->|"ICMP limitado por timeout"| LAN["Dispositivos autorizados da LAN"]
  WORKER -->|"métricas, status, falhas e diagnóstico"| DB
  DB -->|"inventário e agendamento"| WORKER
```

Backend: Flask, SQLAlchemy e Flask-Migrate/Alembic, com services de autenticação, cadastros, coleta, regras, consultas e relatórios. Frontend: JavaScript em módulos ES, Vite e Chart.js. SQLite é o banco validado para o MVP. Outro banco e operação distribuída não foram homologados.

O worker deve executar onde alcance os IPs cadastrados. Hospedar somente a interface na Internet não fornece acesso à rede privada da empresa.

## Pré-requisitos

- Python 3.12 ou superior; validado em Python 3.12.14/Linux.
- Node.js 22.12 ou superior compatível com Vite 8, e npm.
- Acesso à LAN dos dispositivos e permissão do sistema operacional para ICMP.
- Navegador atual.

## Instalação do backend

Na raiz do repositório, em Linux/macOS:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.lock
cp -n .env.example .env
```

Windows/PowerShell:

```powershell
cd backend
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.lock
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

O lock inclui runtime e ferramentas de teste do ambiente validado. `requirements.txt` contém as dependências diretas de runtime; `requirements-dev.txt`, os extras de desenvolvimento. Preserve um `.env` existente e revise seu banco antes de prosseguir.

## Banco novo e migrations

**Se já existe um banco do protótipo, siga [a importação legada](docs/LEGACY.md) antes de aplicar migrations.** A migration inicial não deve ser aplicada sobre tabelas antigas de mesmo nome. Não use `db stamp` para contornar incompatibilidade de schema.

Dentro de `backend/`, com o ambiente virtual ativo:

```bash
python -m flask --app run.py db upgrade
python -m flask --app run.py seed-catalog
python -m flask --app run.py db current
python -m flask --app run.py db check
```

`DATABASE_URL=sqlite:///edgehealth.db` resolve para `backend/instance/edgehealth.db`. Para caminho absoluto Linux, use quatro barras: `sqlite:////caminho/edgehealth.db`. API e worker devem usar o mesmo banco. O seed cria somente oito ações corretivas e é idempotente.

- `55463d3f0b18`: entidades, sessões, FKs, constraints, índices históricos, IP ativo único por empresa e uma falha aberta por dispositivo.
- `7c7ba005affc`: preservação separada dos registros legados, sem tratá-los como medições reais.

Há integridade referencial SQLite em cada conexão e espera limitada para bloqueio de escrita. Dispositivos são arquivados; seu histórico permanece. API e worker não executam `create_all()` na inicialização.

## Executar em desenvolvimento

Terminal 1, dentro de `backend/`, com o ambiente virtual ativo:

```bash
python run.py
```

Terminal 2, também em `backend/`, com o mesmo ambiente virtual:

```bash
python -m flask --app run.py monitor
```

Terminal 3, a partir da raiz do repositório:

```bash
cd frontend
npm ci
npm run dev
```

Abra `http://localhost:5173`. Vite encaminha `/api` para `http://127.0.0.1:5000`; `API_PROXY_TARGET` ajusta esse destino quando necessário. Cookies e requisições permanecem na mesma origem; não é necessário CORS permissivo.

O botão **Coletar** solicita agendamento e retorna HTTP 202. Quem mede é o worker. Sem ele, o botão não cria amostras nem apresenta resultado fictício.

## Build e execução sem Vite

```bash
cd frontend
npm ci
npm run build
cd ../backend
```

Com o ambiente virtual ativo:

```bash
waitress-serve --listen=127.0.0.1:5000 run:app
```

Flask serve build e API em `http://localhost:5000`. Mantenha `python -m flask --app run.py monitor` em outro processo. Para execução contínua, supervisione ambos. Ao expor a aplicação, use HTTPS e `COOKIE_SECURE=true`; esse valor exige HTTPS para enviar o cookie. HTTP local usa `false`.

## Primeiro acesso e segurança

Na tela de login, escolha **Cadastrar minha empresa**. Informe empresa, CNPJ, nome, e-mail e senha de 10 a 128 caracteres. A primeira conta administra a empresa criada; cadastre a equipe em **Equipe**. Dispositivos exigem nome, IP, tipo e localização; a empresa vem da sessão.

Senhas usam scrypt/Werkzeug. A sessão é opaca e aleatória, com cookie HttpOnly/SameSite e somente hashes dos tokens no banco. Alterações exigem CSRF. Logout, troca de senha, permissão ou desativação revogam sessões. Tentativas de login são limitadas de forma persistida. Não há token em localStorage.

Consultas usam a empresa da sessão e validam IDs relacionados. Um ID de outra empresa retorna 404. O cliente não pode atribuir `empresa_id`, status ou métricas. Recomendações são catálogo global sem dados de empresas. Usuários comuns não administram empresa/equipe.

CNPJ numérico e alfanumérico são normalizados e validados por dígito verificador, conforme o [algoritmo da Receita Federal](https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/perguntas-e-respostas/cnpj/cnpj-alfanumerico.pdf). Isso valida o formato, não a situação cadastral.

## Configuração e coleta

| Variável | Padrão | Comportamento |
|---|---:|---|
| `DATABASE_URL` | `sqlite:///edgehealth.db` | Banco de API e worker |
| `COOKIE_SECURE` | `false` | Use `true` com HTTPS |
| `SESSION_HOURS` | 8 | Validade da sessão |
| `MONITOR_INTERVAL` | 30 s | Intervalo após concluir a coleta anterior |
| `MONITOR_PACKETS` | 4 | Pacotes por amostra, entre 1 e 10 |
| `MONITOR_TIMEOUT` | 1 s | Timeout por pacote, entre 0,1 e 10 s |
| `MONITOR_WORKERS` | 4 | Concorrência, entre 1 e 16 |
| `MONITOR_LEASE_SECONDS` | 120 s | Lease superior ao limite da sondagem com margem |
| `OFFLINE_AFTER` | 3 | Ausências de resposta para confirmar OFFLINE |
| `RECOVERY_AFTER` | 2 | Amostras saudáveis para confirmar recuperação |
| `LATENCY_LIMIT_MS` | 150 ms | Limite de degradação, inclusivo |
| `LOSS_LIMIT_PCT` | 5% | Limite de degradação, inclusivo |
| `DIAGNOSTIC_WINDOW_SECONDS` | 300 s | Janela de correlação |
| `STALE_AFTER_SECONDS` | 180 s | Alerta de observação ausente/desatualizada |

O worker consulta vencimentos a cada até 2 s. Um lease transacional impede coleta simultânea do mesmo dispositivo, inclusive entre processos. A sondagem não mantém transação de banco aberta nem bloqueia a requisição HTTP. O lease expira após interrupção do processo. Não há scheduler iniciado pelo reloader web.

`icmplib.ping` recebe IP validado, quantidade, timeout e intervalo de 0,2 s entre pacotes. Latência vem das respostas recebidas; perda é `(enviados - recebidos) / enviados * 100`. Sem resposta, latência é `null`. Erros de permissão/configuração não equivalem à indisponibilidade do alvo e não criam amostras ou falhas de rede.

O status inicial é desconhecido: **Aguardando coleta**. Depois, ONLINE exige respostas dentro dos limites e confirmação de recuperação quando necessária; INSTAVEL representa degradação, primeiras ausências ou recuperação em confirmação; OFFLINE exige três amostras consecutivas sem resposta por padrão. Cada amostra preserva conectividade bruta, timestamp UTC, latência, contagens, perda e estado resultante.

Sondagem real sem persistência e execução de um único ciclo vencido:

```bash
python -m flask --app run.py probe 127.0.0.1
python -m flask --app run.py monitor --once
```

Erro de permissão ICMP requer adequação pelo operador do ambiente; não há fallback de números fixos. Um equipamento pode bloquear ICMP mesmo operacional, hipótese explicitada pelo diagnóstico.

## Falhas, impacto e diagnóstico

Anomalia abre uma ocorrência; ciclos seguintes atualizam a mesma falha. A confirmação de recuperação a encerra. Queda posterior cria outra. Arquivamento encerra com motivo ARQUIVAMENTO, distinto de RECUPERACAO.

A duração automática é o intervalo observado da **ocorrência**, incluindo instabilidade e confirmação de recuperação, limitado à precisão das sondagens. Não é medição contínua exata de downtime. Usuários afetados começam desconhecidos e podem ser informados na tela, com origem manual e observação.

Severidade usa o maior nível aplicável, com thresholds centralizados em `app/config.py`: BAIXA para instabilidade inicial; MEDIA após 5 minutos ou indisponibilidade confirmada; ALTA após 15 minutos, três dispositivos temporalmente relacionados ou 10 usuários informados; CRITICA após 60 minutos ou 50 usuários. A justificativa e a data de cálculo são persistidas. Coletas e alteração do impacto recalculam o nível.

O diagnóstico considera até 20 amostras recentes, pares da mesma empresa com observação recente e até 20 ocorrências anteriores dos últimos sete dias. Regras: problema localizado, interrupção possivelmente compartilhada, congestionamento/instabilidade, latência e recorrência. Causas são hipóteses; topologia não é presumida. Sem evidência, informa insuficiência. Evidências, versão, momento e recomendações são persistidos. A recuperação conserva a última explicação da anomalia no histórico.

## Dashboard e relatórios

Métricas são paginadas, cronológicas e filtráveis por dispositivo/período/tipo. Histórico filtra dispositivo, período, severidade e estado. Filtros usam UTC; `fim` com apenas data inclui o dia inteiro. Se somente `fim` for informado, o início padrão é relativo a ele.

Dashboard atualiza a cada 15 s: inventário, estados, falhas abertas, severidades, recentes e séries de latência/perda de um dispositivo. Indicadores representam o estado atual; período aplica-se aos gráficos. Exibe até 500 amostras mais recentes e informa o total, mantendo lacunas de latência desconhecida.

Relatórios geram ZIP com `dispositivos.csv`, `metricas.csv`, `falhas.csv`, `diagnosticos.csv` e `leia-me.json`. CSV UTF-8 com BOM, delimitador `;`, datas UTC, proteção contra fórmulas e JSON para evidências/causas/impacto/recomendações. Inclui somente a empresa autenticada. Inventário inclui arquivados; falhas incluem ocorrências sobrepostas ao intervalo; diagnóstico é a última análise disponível. Padrão: 30 dias. Acima de 50.000 registros por seção, reduza o período.

## API

| Método | Rota | Finalidade |
|---|---|---|
| GET | `/api/health` | Banco e migrations; 503 se pendentes |
| POST | `/api/auth/registro`, `/api/auth/login` | Cadastro inicial / sessão |
| GET / POST | `/api/auth/me` / `/api/auth/logout` | Contexto / revogação |
| GET / PUT | `/api/empresa` | Empresa atual; escrita administrativa |
| GET / POST / PUT | `/api/usuarios`, `/api/usuarios/{id}` | Equipe; acesso administrativo |
| GET / POST | `/api/dispositivos` | Inventário / criação |
| GET / PUT / DELETE | `/api/dispositivos/{id}` | Consulta / edição / arquivamento |
| POST | `/api/dispositivos/{id}/coletas` | Agendamento, HTTP 202 |
| GET | `/api/metricas`, `/api/metricas/{id}` | Histórico e amostra |
| GET | `/api/falhas`, `/api/falhas/{id}` | Histórico e detalhe |
| PUT | `/api/falhas/{id}/impacto` | Estimativa e recálculo |
| GET | `/api/diagnosticos/{id}`, `/api/recomendacoes` | Análise e catálogo |
| GET | `/api/dashboard`, `/api/relatorios/exportar` | Dashboard / ZIP |

Exceto health, registro e login, rotas exigem sessão. Não há escrita manual de métricas/status/falhas. Erros comuns retornam JSON e HTTP 400/401/403/404/409/422/429, com rollback das alterações inconsistentes.

## Testes

Em `backend/`, com o ambiente virtual ativo:

```bash
python -m pytest --cov=app --cov-report=term-missing -q
```

Em `frontend/`, após instalar dependências do backend:

```bash
npm ci
npm test
```

`npm test` gera o build e inicia uma API HTTP e SQLite temporários, aplica migrations, envia formulários e verifica respostas reais, datasets dos gráficos, exportação, build servido pelo Flask e proxy Vite. Usa `.venv` do backend; `EDGEHEALTH_PYTHON` pode apontar para outro Python com dependências. Testes DOM usam jsdom, não substituem homologação visual nos navegadores finais.

Probes controlados existem somente nos testes, passando pelo pipeline de persistência. Não há endpoint HTTP ou variável de produção para simular medições.

Teste opcional ICMP real, somente loopback, Linux/macOS:

```bash
EDGEHEALTH_TEST_REAL_NETWORK=1 python -m pytest -m real_network -q
```

PowerShell:

```powershell
$env:EDGEHEALTH_TEST_REAL_NETWORK='1'
python -m pytest -m real_network -q
Remove-Item Env:EDGEHEALTH_TEST_REAL_NETWORK
```

Sem a variável, o teste real é explicitamente pulado. Aqui a tentativa real falhou com `SocketPermissionError`; aprovar sondagens controladas não aprova o ICMP real.

## Limites conhecidos

RF01–RF20 estão cobertos em código; RF08–RF10 têm aceite de campo pendente pela permissão ICMP do ambiente. O restante do fluxo foi exercitado com sondagens determinísticas isoladas. Não há dados simulados em produção.

O MVP mede a partir de um ponto de rede, não descobre topologia nem calcula usuários automaticamente. Histórico cresce sem retenção automática. Escala elevada, LANs isoladas e outro banco exigem planejamento próprio. CSV atende RF20; PDF/XLSX não fazem parte desta entrega. Veja [o roteiro de demonstração](docs/DEMO.md) para homologar na LAN da equipe.
