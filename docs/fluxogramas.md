# Fluxogramas dos casos de uso

Seis casos de uso principais, passo a passo pelas camadas da API, com os **nomes reais** das classes e métodos
(`backend/tests/test_flowcharts.py` falha se algum Controller, Service ou Repository citado deixar de existir).
Imagens para slides em [`docs/img/`](img/).

Cada cor é uma camada:

```mermaid
flowchart LR
    T["Tela (frontend)"]:::tela --> C["Controller"]:::ctrl --> S["Service"]:::svc --> M["Model"]:::model
    S --> R["Repository (SQL)"]:::repo
    M --> B[("Banco SQLite")]:::banco
    R --> B
    E["Resposta de erro"]:::erro
    classDef tela fill:#e3f2fd,stroke:#1e88e5,color:#0d2b45
    classDef ctrl fill:#ede7f6,stroke:#5e35b1,color:#1f1147
    classDef svc fill:#e8f5e9,stroke:#2e7d32,color:#0f2e12
    classDef model fill:#fff8e1,stroke:#f9a825,color:#3d2c00
    classDef repo fill:#fce4ec,stroke:#c2185b,color:#45091f
    classDef banco fill:#eceff1,stroke:#455a64,color:#1c262b
    classDef erro fill:#ffebee,stroke:#c62828,color:#5a0d0d
```

Em todas as rotas com sessão, antes do Controller, o decorator `require_auth` (`backend/app/security.py`) chama o
`ValidarSessaoService`: sem sessão válida responde **401**; sem o token CSRF (em POST/PUT/DELETE) ou com os Termos de
Uso pendentes, **403**; rota de administrador para técnico, **403**. Toda busca por ID é limitada à empresa do usuário:
registro de outra empresa responde **404**, sem revelar que existe.

---

## 1. Entrada de dados: cadastrar dispositivo

**Objetivo:** incluir um equipamento no monitoramento, já com o impacto no negócio sugerido pelo tipo.
**Ator:** administrador ou técnico da empresa. **Tela:** `frontend/src/pages/Dispositivos.js` → "Cadastrar dispositivo".

Imagem para slides: [SVG](img/fluxo-1-cadastrar-dispositivo.svg) · [PNG](img/fluxo-1-cadastrar-dispositivo.png)

```mermaid
flowchart TD
    T1["Dispositivos.js: ao digitar o tipo"]:::tela -->|"GET /api/dispositivos/impacto-padrao?tipo="| C1["DispositivoController.impacto_padrao"]:::ctrl
    C1 --> S1["ObterImpactoPadraoService.executar<br/>CategoriaDispositivo.padroes: pessoas e perda% do tipo"]:::svc
    S1 --> T2["Formulário preenchido com os padrões<br/>(editáveis)"]:::tela
    T2 -->|"POST /api/dispositivos (JSON)"| C2["DispositivoController.cadastrar<br/>payload: campos permitidos e obrigatórios"]:::ctrl
    C2 -->|"campo faltando ou não permitido"| E400a["400"]:::erro
    C2 --> S2["CadastrarDispositivoService.executar"]:::svc
    S2 --> S3["DadosDispositivo.aplicar<br/>valida nome, IP, tipo, localização e impacto"]:::svc
    S3 -->|"valor inválido ou negativo"| E400b["400 com a mensagem do campo"]:::erro
    S3 -->|"coletor_id informado"| S4["ValidarColetorAtribuivelService.executar"]:::svc
    S4 --> R1["ColetorRepository.buscar_da_empresa"]:::repo
    R1 -->|"coletor de outra empresa"| E404["404"]:::erro
    R1 -->|"coletor revogado"| E409a["409"]:::erro
    S3 -->|"impacto não enviado"| S5["CategoriaDispositivo.padroes<br/>preenche pessoas e perda% pelo tipo"]:::svc
    S3 --> M1["Dispositivo.salvar()"]:::model
    S5 --> M1
    M1 --> B1[("INSERT INTO dispositivos")]:::banco
    B1 -->|"IP já ativo na empresa (índice único)"| E409b["409"]:::erro
    B1 --> OK["201 + JSON do dispositivo<br/>Serializador.dispositivo"]:::tela
    classDef tela fill:#e3f2fd,stroke:#1e88e5,color:#0d2b45
    classDef ctrl fill:#ede7f6,stroke:#5e35b1,color:#1f1147
    classDef svc fill:#e8f5e9,stroke:#2e7d32,color:#0f2e12
    classDef model fill:#fff8e1,stroke:#f9a825,color:#3d2c00
    classDef repo fill:#fce4ec,stroke:#c2185b,color:#45091f
    classDef banco fill:#eceff1,stroke:#455a64,color:#1c262b
    classDef erro fill:#ffebee,stroke:#c62828,color:#5a0d0d
```

---

## 2. Entrada de dados: coletor envia amostras e o sistema detecta a falha

**Objetivo:** registrar as medições (ping) feitas dentro da rede do cliente e, a partir delas, abrir ou encerrar
ocorrências, diagnosticar e calcular a severidade. **Ator:** coletor remoto (`collector/edgehealth_collector.py` ou
`EdgeHealthColetor.exe`), autenticado por credencial própria. **Tela:** o resultado aparece na Visão da rede e no Histórico.

Imagem para slides: [SVG](img/fluxo-2-receber-amostras.svg) · [PNG](img/fluxo-2-receber-amostras.png)

```mermaid
flowchart TD
    T["Coletor: Collector.flush<br/>lote de amostras com UUID"]:::tela -->|"POST /api/coletor/amostras<br/>Authorization: Bearer ehc_..."| A["require_collector<br/>AutenticarColetorService.executar"]:::svc
    A -->|"credencial inválida ou revogada"| E401["401"]:::erro
    A -->|"acima do limite de requisições por minuto"| E429["429"]:::erro
    A --> C["ColetorApiController.amostras<br/>payload: amostras e erros"]:::ctrl
    C --> S["ReceberAmostrasService.executar"]:::svc
    S -->|"lote acima do limite"| E400["400"]:::erro
    S --> R1["DispositivoRepository.listar_do_coletor"]:::repo
    S --> I["InterpretarAmostraService.executar<br/>UUID, horário, pacotes, latência"]:::svc
    I -->|"inválida, futura ou de dispositivo não atribuído"| REJ["resultado REJEITADA"]:::erro
    I --> L["ReservarDispositivoService.executar"]:::svc
    L --> R2["DispositivoRepository.reservar_para_coletor<br/>UPDATE com lease exclusivo"]:::repo
    R2 -->|"lease ocupado"| TR["resultado TENTAR_NOVAMENTE"]:::erro
    R2 --> R3["MetricaRepository.uids_existentes"]:::repo
    R3 -->|"UUID já gravado"| DUP["resultado DUPLICADA"]:::tela
    R3 --> M["RegistrarMedicaoService.executar"]:::svc
    M --> K["ClassificarStatusService.executar<br/>ONLINE, INSTAVEL ou OFFLINE com confirmações"]:::svc
    K --> MM["Metrica.salvar(commit=False)"]:::model
    MM --> R4["FalhaRepository.aberta_do_dispositivo"]:::repo
    R4 -->|"anomalia e nenhuma aberta"| AB["Falha.salvar + Impacto.salvar<br/>abre a ocorrência"]:::model
    R4 -->|"ONLINE e havia ocorrência aberta"| EN["Falha.encerrar(RECUPERACAO)"]:::model
    AB --> D["AtualizarDiagnosticosService.executar"]:::svc
    EN --> D
    R4 -->|"sem mudança de ocorrência"| D
    D --> R5["FalhaRepository.abertas_da_empresa<br/>FalhaRepository.encerradas_desde"]:::repo
    D --> SV["CalcularSeveridadeService.executar<br/>duração, dispositivos relacionados, usuários"]:::svc
    D --> AN["AnalisarFalhaService.executar<br/>LOCALIZADA, COMPARTILHADA, CONGESTIONAMENTO, LATENCIA, RECORRENTE"]:::svc
    AN --> R6["MetricaRepository.recentes_na_janela<br/>DispositivoRepository.pares_com_coleta_na_janela<br/>FalhaRepository.ids_anteriores_do_dispositivo<br/>DiagnosticoRepository.recomendacoes_das_regras"]:::repo
    AN --> MD["Diagnostico e DiagnosticoRecomendacao"]:::model
    SV --> B
    MD --> B[("metricas, falhas, impactos,<br/>diagnosticos, diagnostico_recomendacoes")]:::banco
    MM --> B
    B --> LIB["Dispositivo.atualizar<br/>libera o lease e agenda a próxima coleta"]:::model
    LIB --> OK["200 + resultado por amostra:<br/>ACEITA ou ATRASADA"]:::tela
    classDef tela fill:#e3f2fd,stroke:#1e88e5,color:#0d2b45
    classDef ctrl fill:#ede7f6,stroke:#5e35b1,color:#1f1147
    classDef svc fill:#e8f5e9,stroke:#2e7d32,color:#0f2e12
    classDef model fill:#fff8e1,stroke:#f9a825,color:#3d2c00
    classDef repo fill:#fce4ec,stroke:#c2185b,color:#45091f
    classDef banco fill:#eceff1,stroke:#455a64,color:#1c262b
    classDef erro fill:#ffebee,stroke:#c62828,color:#5a0d0d
```

O worker local do servidor usa o mesmo `RegistrarMedicaoService` (via `ColetarDispositivoService`), então as regras de
status, ocorrência, severidade e diagnóstico são uma só.

---

## 3. Entrada de dados: registrar o impacto de uma ocorrência

**Objetivo:** informar quantas pessoas foram afetadas e os custos diretos (técnico, peças, multas); a severidade e o
prejuízo estimado são recalculados na hora. **Ator:** administrador ou técnico. **Tela:**
`frontend/src/pages/Falha.js` → card "Impacto operacional".

Imagem para slides: [SVG](img/fluxo-3-registrar-impacto.svg) · [PNG](img/fluxo-3-registrar-impacto.png)

```mermaid
flowchart TD
    T["Falha.js: Usuários afetados, Custos diretos (R$), Observação"]:::tela -->|"PUT /api/falhas/{id}/impacto"| C["FalhaController.registrar_impacto"]:::ctrl
    C -->|"id + corpo JSON"| S["RegistrarImpactoService.executar"]:::svc
    S --> O["ObterFalhaService.buscar"]:::svc
    O --> R1["FalhaRepository.buscar_da_empresa<br/>JOIN dispositivos WHERE empresa_id"]:::repo
    R1 -->|"ocorrência de outra empresa ou inexistente"| E404["404"]:::erro
    R1 --> P["payload: usuarios_afetados, custos_diretos, observacao<br/>(validado só depois da busca)"]:::svc
    P -->|"campo não permitido, número negativo ou valor inválido"| E400a["400"]:::erro
    P --> M1["Impacto.buscar_um_por + Impacto.salvar(commit=False)<br/>dinheiro em Decimal exato"]:::model
    M1 --> D["AtualizarDiagnosticosService.executar"]:::svc
    D --> SV["CalcularSeveridadeService.executar<br/>10+ usuários: ALTA; 50+ usuários: CRITICA"]:::svc
    D --> R2["FalhaRepository.abertas_da_empresa<br/>FalhaRepository.encerradas_desde"]:::repo
    SV --> TX["Transacao.confirmar"]:::repo
    TX --> B[("UPDATE impactos, falhas")]:::banco
    B --> J["Serializador.falha com detalhe"]:::svc
    J --> PR["EstimarPrejuizoFalhaService.executar<br/>CalculadoraPrejuizo.estimar:<br/>horas de expediente × pessoas × custo/hora × perda% + custos diretos"]:::svc
    PR --> G["IdentificarGrupoCompartilhadoService.executar"]:::svc
    G --> R3["FalhaRepository.grupo_compartilhado<br/>falhas na mesma janela de correlação"]:::repo
    R3 -->|"falha compartilhada"| GR["total do grupo sem contar as mesmas pessoas duas vezes"]:::svc
    R3 --> OK["200 + ocorrência com severidade,<br/>diagnóstico e prejuízo estimado"]:::tela
    GR --> OK
    classDef tela fill:#e3f2fd,stroke:#1e88e5,color:#0d2b45
    classDef ctrl fill:#ede7f6,stroke:#5e35b1,color:#1f1147
    classDef svc fill:#e8f5e9,stroke:#2e7d32,color:#0f2e12
    classDef model fill:#fff8e1,stroke:#f9a825,color:#3d2c00
    classDef repo fill:#fce4ec,stroke:#c2185b,color:#45091f
    classDef banco fill:#eceff1,stroke:#455a64,color:#1c262b
    classDef erro fill:#ffebee,stroke:#c62828,color:#5a0d0d
```

---

## 4. Recuperação de dados: histórico de falhas com filtros e paginação

**Objetivo:** investigar ocorrências abertas e encerradas por dispositivo, situação, severidade e período, inclusive de
dispositivos arquivados. **Ator:** administrador ou técnico. **Tela:** `frontend/src/pages/Historico.js` → "Filtrar".

Imagem para slides: [SVG](img/fluxo-4-historico-falhas.svg) · [PNG](img/fluxo-4-historico-falhas.png)

```mermaid
flowchart TD
    T["Historico.js: dispositivo, situação, severidade, início, fim"]:::tela -->|"GET /api/falhas?dispositivo_id&estado&severidade<br/>&inicio&fim&pagina&limite=25"| C["FalhaController.listar<br/>lê a query string"]:::ctrl
    C --> S["ListarFalhasService.executar"]:::svc
    S -->|"severidade ou situação inválida"| E400a["400"]:::erro
    S -->|"data inválida ou início depois do fim"| E400b["400"]:::erro
    S -->|"dispositivo_id informado"| O["ObterDispositivoService.buscar"]:::svc
    O --> R0["DispositivoRepository.buscar_da_empresa"]:::repo
    R0 -->|"dispositivo de outra empresa"| E404["404"]:::erro
    S --> R["FalhaRepository.historico"]:::repo
    R --> Q["SQL: SELECT falhas JOIN dispositivos<br/>WHERE empresa_id = ? AND filtros<br/>AND inicio >= ? AND inicio < ?<br/>ORDER BY inicio DESC, id DESC LIMIT ? OFFSET ?<br/>+ SELECT COUNT(*) para o total"]:::repo
    Q --> B[("falhas, dispositivos")]:::banco
    B --> J["Serializador.falha<br/>duração, severidade, impacto"]:::svc
    J --> OK["200 + items, total, pagina, limite"]:::tela
    OK --> T2["Historico.js: tabela (cards no celular)<br/>e paginação Anterior / Próxima"]:::tela
    classDef tela fill:#e3f2fd,stroke:#1e88e5,color:#0d2b45
    classDef ctrl fill:#ede7f6,stroke:#5e35b1,color:#1f1147
    classDef svc fill:#e8f5e9,stroke:#2e7d32,color:#0f2e12
    classDef model fill:#fff8e1,stroke:#f9a825,color:#3d2c00
    classDef repo fill:#fce4ec,stroke:#c2185b,color:#45091f
    classDef banco fill:#eceff1,stroke:#455a64,color:#1c262b
    classDef erro fill:#ffebee,stroke:#c62828,color:#5a0d0d
```

---

## 5. Recuperação de dados: visão da rede (dashboard)

**Objetivo:** mostrar o estado atual da rede, as ocorrências recentes, o desempenho no tempo e o custo estimado das
falhas dos últimos 30 dias com os 5 dispositivos que mais custaram. **Ator:** administrador ou técnico. **Tela:**
`frontend/src/pages/Dashboard.js` (atualiza sozinha a cada 15 s).

Imagem para slides: [SVG](img/fluxo-5-dashboard.svg) · [PNG](img/fluxo-5-dashboard.png)

```mermaid
flowchart TD
    T["Dashboard.js: a cada 15 s ou ao aplicar o filtro"]:::tela -->|"GET /api/dashboard?dispositivo_id&inicio&fim"| C["DashboardController.obter"]:::ctrl
    C --> S["GerarDashboardService.executar"]:::svc
    S -->|"dispositivo de outra empresa"| E404["404"]:::erro
    S --> R1["DispositivoRepository.listar_ativos_da_empresa"]:::repo
    S --> R2["DashboardRepository.contagem_por_status<br/>SQL: SELECT status, COUNT(*) ... GROUP BY status"]:::repo
    S --> R3["DashboardRepository.contagem_por_severidade<br/>SQL: ... WHERE estado = ABERTA GROUP BY severidade"]:::repo
    S --> R4["FalhaRepository.recentes_da_empresa<br/>MetricaRepository.serie_do_dispositivo<br/>ColetorRepository.ativos_da_empresa"]:::repo
    S --> R5["FalhaRepository.ranking_dispositivos<br/>SQL: COUNT ... GROUP BY dispositivo ORDER BY falhas DESC LIMIT 5"]:::repo
    S --> P["ResumirPrejuizoService.executar"]:::svc
    P --> R6["FalhaRepository.iniciadas_desde<br/>falhas dos últimos 30 dias"]:::repo
    P --> T5["CalcularPrejuizoTotalService.executar<br/>CalculadoraPrejuizo.estimar por falha<br/>IdentificarGrupoCompartilhadoService: sem dupla contagem"]:::svc
    T5 --> R7["RankingCustoRepository.top_dispositivos<br/>SQL: ORDER BY valor DESC LIMIT 5"]:::repo
    P -->|"empresa sem custos configurados"| NC["custos.configurado = false:<br/>a tela pede para configurar"]:::tela
    R1 --> B[("dispositivos, falhas, metricas, coletores")]:::banco
    R2 --> B
    R3 --> B
    R4 --> B
    R5 --> B
    R6 --> B
    R7 --> B
    B --> OK["200 + indicadores, severidades, recentes, série,<br/>coletores, custos (total e top 5)"]:::tela
    OK --> T2["Dashboard.js: cartões, gráficos de latência e perda,<br/>Custo estimado das falhas (30 dias)"]:::tela
    classDef tela fill:#e3f2fd,stroke:#1e88e5,color:#0d2b45
    classDef ctrl fill:#ede7f6,stroke:#5e35b1,color:#1f1147
    classDef svc fill:#e8f5e9,stroke:#2e7d32,color:#0f2e12
    classDef model fill:#fff8e1,stroke:#f9a825,color:#3d2c00
    classDef repo fill:#fce4ec,stroke:#c2185b,color:#45091f
    classDef banco fill:#eceff1,stroke:#455a64,color:#1c262b
    classDef erro fill:#ffebee,stroke:#c62828,color:#5a0d0d
```

---

## 6. Recuperação de dados com IA: explicar ocorrência com IA

**Objetivo:** gerar, em português simples para um gestor não técnico, o que aconteceu, o impacto provável e os
próximos passos, a partir do diagnóstico e das recomendações que o sistema já calculou. A IA **explica**; ela não
substitui nem altera o diagnóstico por regras. **Ator:** administrador ou técnico. **Tela:**
`frontend/src/pages/Falha.js` → card "Explicação com IA" → "Explicar com IA".

Imagem para slides: [SVG](img/fluxo-6-explicar-com-ia.svg) · [PNG](img/fluxo-6-explicar-com-ia.png)

```mermaid
flowchart TD
    T["Falha.js: botão Explicar com IA<br/>(desabilitado se ia_disponivel = false)"]:::tela -->|"POST /api/falhas/{id}/explicacao-ia"| C["FalhaController.explicar_com_ia"]:::ctrl
    C -->|"id + corpo JSON"| S["ExplicarFalhaComIaService.executar"]:::svc
    S --> O["ObterFalhaService.buscar"]:::svc
    O --> R1["FalhaRepository.buscar_da_empresa"]:::repo
    R1 -->|"ocorrência de outra empresa"| E404["404"]:::erro
    R1 --> P["payload vazio<br/>(o prompt nunca vem do cliente)"]:::svc
    P -->|"campo extra no pedido"| E400["400"]:::erro
    P -->|"GEMINI_API_KEY não configurada"| E503a["503 IA não configurada neste servidor"]:::erro
    P --> L["LimiteUsoIa.registrar<br/>limite por empresa por hora"]:::svc
    L -->|"limite atingido"| E429["429"]:::erro
    L --> CT["ExplicarFalhaComIaService.contexto<br/>somente dados técnicos (lista de permitidos)"]:::svc
    CT --> M["Dispositivo.buscar_por_id, Impacto.buscar_um_por,<br/>Diagnostico.buscar_um_por: tipo, localização,<br/>horários, severidade, causas e recomendações"]:::model
    CT --> PR["EstimarPrejuizoFalhaService.executar<br/>prejuízo estimado"]:::svc
    M --> B[("falhas, dispositivos, impactos,<br/>diagnosticos, recomendacoes")]:::banco
    CT --> G["GeminiService.executar<br/>única classe que fala com a API do Gemini<br/>chave no cabeçalho, timeout de 20 s"]:::svc
    G -->|"HTTPS generateContent"| API[("Gemini API (Google)")]:::banco
    API -->|"cota esgotada, rede ou timeout"| E503b["503 com mensagem clara"]:::erro
    API -->|"chave inválida ou resposta vazia"| E502["502"]:::erro
    API --> OK["200 + texto, modelo, gerado_em e aviso"]:::tela
    OK --> T2["Falha.js: parágrafos e o aviso<br/>Texto gerado por IA a partir do diagnóstico do sistema;<br/>confira antes de agir"]:::tela
    classDef tela fill:#e3f2fd,stroke:#1e88e5,color:#0d2b45
    classDef ctrl fill:#ede7f6,stroke:#5e35b1,color:#1f1147
    classDef svc fill:#e8f5e9,stroke:#2e7d32,color:#0f2e12
    classDef model fill:#fff8e1,stroke:#f9a825,color:#3d2c00
    classDef repo fill:#fce4ec,stroke:#c2185b,color:#45091f
    classDef banco fill:#eceff1,stroke:#455a64,color:#1c262b
    classDef erro fill:#ffebee,stroke:#c62828,color:#5a0d0d
```
