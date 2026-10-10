-- =====================================================================================
-- EdgeHealth: criação do banco de dados SQLite e de todas as tabelas
-- =====================================================================================
-- Arquivo GERADO a partir das migrations Alembic (backend/migrations/versions); não edite
-- à mão. Para regenerar depois de criar uma migration:
--     cd backend && python database/gerar_create_database.py
-- (tests/test_database_script.py falha se este script ficar diferente das migrations.)
--
-- Uso, em um arquivo de banco NOVO e vazio:
--     cd backend
--     sqlite3 instance/edgehealth.db < database/create_database.sql
--
-- O banco criado já registra a revisão atual em alembic_version, então
-- "flask db upgrade" o reconhece e aplicará somente migrations futuras.
-- Tipos: SQLite usa afinidade de tipo; VARCHAR(n) documenta o limite validado pela
-- aplicação. Valores monetários são texto decimal exato (ex.: '3000.00'), nunca float.
-- Datas são UTC no formato 'AAAA-MM-DD HH:MM:SS.ffffff'.
-- =====================================================================================

PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

-- empresas
CREATE TABLE empresas (
    id INTEGER NOT NULL,
    nome_fantasia VARCHAR(150) NOT NULL,
    cnpj VARCHAR(14) NOT NULL,
    email VARCHAR(254),
    telefone VARCHAR(30),
    criada_em DATETIME NOT NULL,
    salario_medio VARCHAR(24),
    fator_encargos VARCHAR(24) DEFAULT '1.7' NOT NULL,
    horas_mes INTEGER DEFAULT '220' NOT NULL,
    total_funcionarios INTEGER,
    expediente_dias VARCHAR(7) DEFAULT '12345' NOT NULL,
    expediente_inicio VARCHAR(5) DEFAULT '08:00' NOT NULL,
    expediente_fim VARCHAR(5) DEFAULT '18:00' NOT NULL,
    fuso VARCHAR(50) DEFAULT 'America/Sao_Paulo' NOT NULL,
    assistente_custos VARCHAR(10),
    CONSTRAINT pk_empresas PRIMARY KEY (id),
    CONSTRAINT uq_empresas_cnpj UNIQUE (cnpj)
);

-- usuarios
CREATE TABLE usuarios (
    id INTEGER NOT NULL,
    empresa_id INTEGER NOT NULL,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(254) NOT NULL,
    senha_hash VARCHAR(512) NOT NULL,
    papel VARCHAR(20) NOT NULL,
    ativo BOOLEAN NOT NULL,
    criada_em DATETIME NOT NULL,
    termos_versao VARCHAR(20),
    termos_aceitos_em DATETIME,
    anonimizado_em DATETIME,
    CONSTRAINT pk_usuarios PRIMARY KEY (id),
    CONSTRAINT ck_usuarios_papel CHECK (papel IN ('ADMIN','TECNICO')),
    CONSTRAINT fk_usuarios_empresa_id_empresas FOREIGN KEY(empresa_id) REFERENCES empresas (id) ON DELETE RESTRICT,
    CONSTRAINT uq_usuarios_email UNIQUE (email)
);
CREATE INDEX ix_usuarios_empresa_id ON usuarios (empresa_id);

-- auth_sessions
CREATE TABLE auth_sessions (
    id VARCHAR(64) NOT NULL,
    usuario_id INTEGER NOT NULL,
    csrf_hash VARCHAR(64) NOT NULL,
    expires_at DATETIME NOT NULL,
    CONSTRAINT pk_auth_sessions PRIMARY KEY (id),
    CONSTRAINT fk_auth_sessions_usuario_id_usuarios FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
);
CREATE INDEX ix_auth_sessions_expires_at ON auth_sessions (expires_at);
CREATE INDEX ix_auth_sessions_usuario_id ON auth_sessions (usuario_id);

-- login_attempts
CREATE TABLE login_attempts (
    id INTEGER NOT NULL,
    "key" VARCHAR(64) NOT NULL,
    created_at DATETIME NOT NULL,
    CONSTRAINT pk_login_attempts PRIMARY KEY (id)
);
CREATE INDEX ix_login_attempts_created_at ON login_attempts (created_at);
CREATE INDEX ix_login_attempts_key ON login_attempts ("key");

-- coletores
CREATE TABLE coletores (
    id INTEGER NOT NULL,
    empresa_id INTEGER NOT NULL,
    nome VARCHAR(100) NOT NULL,
    token_hash VARCHAR(64) NOT NULL,
    token_prefixo VARCHAR(12) NOT NULL,
    criado_em DATETIME NOT NULL,
    rotacionado_em DATETIME,
    revogado_em DATETIME,
    ultimo_contato DATETIME,
    versao VARCHAR(30),
    fila_pendente INTEGER,
    ultimo_erro VARCHAR(500),
    ultimo_erro_em DATETIME,
    janela_inicio DATETIME,
    janela_requisicoes INTEGER NOT NULL,
    CONSTRAINT pk_coletores PRIMARY KEY (id),
    CONSTRAINT fk_coletores_empresa_id_empresas FOREIGN KEY(empresa_id) REFERENCES empresas (id) ON DELETE RESTRICT,
    CONSTRAINT uq_coletores_token_hash UNIQUE (token_hash)
);
CREATE INDEX ix_coletores_empresa_id ON coletores (empresa_id);

-- dispositivos
CREATE TABLE dispositivos (
    id INTEGER NOT NULL,
    empresa_id INTEGER NOT NULL,
    nome VARCHAR(100) NOT NULL,
    ip VARCHAR(45) NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    localizacao VARCHAR(150) NOT NULL,
    status VARCHAR(10),
    ultima_coleta DATETIME,
    latencia_ms FLOAT,
    perda_pacotes_pct FLOAT,
    falhas_consecutivas INTEGER NOT NULL,
    sucessos_consecutivos INTEGER NOT NULL,
    arquivado_em DATETIME,
    criado_em DATETIME NOT NULL,
    erro_coleta VARCHAR(500),
    lease_owner VARCHAR(64),
    lease_until DATETIME,
    proxima_coleta DATETIME NOT NULL,
    coletor_id INTEGER CONSTRAINT fk_dispositivos_coletor_id_coletores REFERENCES coletores (id),
    usuarios_dependentes INTEGER,
    perda_produtividade_pct INTEGER,
    receita_hora_dependente VARCHAR(24),
    CONSTRAINT pk_dispositivos PRIMARY KEY (id),
    CONSTRAINT ck_dispositivos_status CHECK (status IS NULL OR status IN ('ONLINE','INSTAVEL','OFFLINE')),
    CONSTRAINT ck_dispositivos_counters CHECK (falhas_consecutivas >= 0 AND sucessos_consecutivos >= 0),
    CONSTRAINT ck_dispositivos_latencia CHECK (latencia_ms IS NULL OR latencia_ms >= 0),
    CONSTRAINT ck_dispositivos_perda CHECK (perda_pacotes_pct IS NULL OR perda_pacotes_pct BETWEEN 0 AND 100),
    CONSTRAINT fk_dispositivos_empresa_id_empresas FOREIGN KEY(empresa_id) REFERENCES empresas (id) ON DELETE RESTRICT
);
CREATE INDEX ix_dispositivos_coletor_id ON dispositivos (coletor_id);
CREATE INDEX ix_dispositivos_empresa_id ON dispositivos (empresa_id);
CREATE INDEX ix_dispositivos_proxima_coleta ON dispositivos (proxima_coleta);
CREATE UNIQUE INDEX uq_dispositivo_ip_ativo ON dispositivos (empresa_id, ip) WHERE arquivado_em IS NULL;

-- metricas
CREATE TABLE metricas (
    id INTEGER NOT NULL,
    dispositivo_id INTEGER NOT NULL,
    coletada_em DATETIME NOT NULL,
    respondeu BOOLEAN NOT NULL,
    latencia_ms FLOAT,
    pacotes_enviados INTEGER NOT NULL,
    pacotes_recebidos INTEGER NOT NULL,
    perda_pacotes_pct FLOAT NOT NULL,
    status VARCHAR(10) NOT NULL,
    coletor_id INTEGER CONSTRAINT fk_metricas_coletor_id_coletores REFERENCES coletores (id),
    amostra_uid VARCHAR(36),
    recebida_em DATETIME,
    fora_de_ordem BOOLEAN DEFAULT 0 NOT NULL,
    CONSTRAINT pk_metricas PRIMARY KEY (id),
    CONSTRAINT ck_metricas_status CHECK (status IN ('ONLINE','INSTAVEL','OFFLINE')),
    CONSTRAINT ck_metricas_latencia CHECK (latencia_ms IS NULL OR latencia_ms >= 0),
    CONSTRAINT ck_metricas_pacotes CHECK (pacotes_enviados > 0 AND pacotes_recebidos >= 0 AND pacotes_recebidos <= pacotes_enviados),
    CONSTRAINT ck_metricas_perda CHECK (perda_pacotes_pct BETWEEN 0 AND 100),
    CONSTRAINT fk_metricas_dispositivo_id_dispositivos FOREIGN KEY(dispositivo_id) REFERENCES dispositivos (id) ON DELETE RESTRICT
);
CREATE INDEX ix_metricas_dispositivo_data ON metricas (dispositivo_id, coletada_em);
CREATE UNIQUE INDEX uq_metrica_coletor_amostra ON metricas (coletor_id, amostra_uid);

-- falhas
CREATE TABLE falhas (
    id INTEGER NOT NULL,
    dispositivo_id INTEGER NOT NULL,
    tipo VARCHAR(30) NOT NULL,
    estado VARCHAR(15) NOT NULL,
    inicio DATETIME NOT NULL,
    fim DATETIME,
    ultima_observacao DATETIME NOT NULL,
    descricao VARCHAR(500) NOT NULL,
    severidade VARCHAR(10) NOT NULL,
    justificativa JSON NOT NULL,
    encerramento VARCHAR(30),
    CONSTRAINT pk_falhas PRIMARY KEY (id),
    CONSTRAINT ck_falhas_ciclo CHECK ((estado='ABERTA' AND fim IS NULL) OR (estado='ENCERRADA' AND fim IS NOT NULL)),
    CONSTRAINT ck_falhas_estado CHECK (estado IN ('ABERTA','ENCERRADA')),
    CONSTRAINT ck_falhas_severidade CHECK (severidade IN ('BAIXA','MEDIA','ALTA','CRITICA')),
    CONSTRAINT ck_falhas_tipo CHECK (tipo IN ('INSTABILIDADE','INDISPONIBILIDADE')),
    CONSTRAINT ck_falhas_datas CHECK (fim IS NULL OR fim >= inicio),
    CONSTRAINT fk_falhas_dispositivo_id_dispositivos FOREIGN KEY(dispositivo_id) REFERENCES dispositivos (id) ON DELETE RESTRICT
);
CREATE INDEX ix_falhas_dispositivo_inicio ON falhas (dispositivo_id, inicio);
CREATE UNIQUE INDEX uq_falha_aberta_dispositivo ON falhas (dispositivo_id) WHERE estado = 'ABERTA';

-- impactos
CREATE TABLE impactos (
    id INTEGER NOT NULL,
    falha_id INTEGER NOT NULL,
    usuarios_afetados INTEGER,
    origem VARCHAR(30) NOT NULL,
    observacao VARCHAR(500),
    atualizado_em DATETIME NOT NULL,
    custos_diretos VARCHAR(24),
    CONSTRAINT pk_impactos PRIMARY KEY (id),
    CONSTRAINT ck_impactos_usuarios CHECK (usuarios_afetados IS NULL OR usuarios_afetados >= 0),
    CONSTRAINT fk_impactos_falha_id_falhas FOREIGN KEY(falha_id) REFERENCES falhas (id) ON DELETE RESTRICT,
    CONSTRAINT uq_impactos_falha_id UNIQUE (falha_id)
);

-- diagnosticos
CREATE TABLE diagnosticos (
    id INTEGER NOT NULL,
    falha_id INTEGER NOT NULL,
    descricao TEXT NOT NULL,
    causas JSON NOT NULL,
    evidencias JSON NOT NULL,
    estado VARCHAR(30) NOT NULL,
    analisado_em DATETIME NOT NULL,
    versao_regras VARCHAR(20) NOT NULL,
    CONSTRAINT pk_diagnosticos PRIMARY KEY (id),
    CONSTRAINT ck_diagnosticos_estado CHECK (estado IN ('DISPONIVEL','EVIDENCIA_INSUFICIENTE')),
    CONSTRAINT fk_diagnosticos_falha_id_falhas FOREIGN KEY(falha_id) REFERENCES falhas (id) ON DELETE RESTRICT,
    CONSTRAINT uq_diagnosticos_falha_id UNIQUE (falha_id)
);

-- recomendacoes
CREATE TABLE recomendacoes (
    id INTEGER NOT NULL,
    regra VARCHAR(50) NOT NULL,
    codigo VARCHAR(50) NOT NULL,
    titulo VARCHAR(150) NOT NULL,
    acao TEXT NOT NULL,
    CONSTRAINT pk_recomendacoes PRIMARY KEY (id),
    CONSTRAINT uq_recomendacoes_codigo UNIQUE (codigo)
);

-- diagnostico_recomendacoes
CREATE TABLE diagnostico_recomendacoes (
    diagnostico_id INTEGER NOT NULL,
    recomendacao_id INTEGER NOT NULL,
    CONSTRAINT pk_diagnostico_recomendacoes PRIMARY KEY (diagnostico_id, recomendacao_id),
    CONSTRAINT fk_diagnostico_recomendacoes_diagnostico_id_diagnosticos FOREIGN KEY(diagnostico_id) REFERENCES diagnosticos (id) ON DELETE CASCADE,
    CONSTRAINT fk_diagnostico_recomendacoes_recomendacao_id_recomendacoes FOREIGN KEY(recomendacao_id) REFERENCES recomendacoes (id) ON DELETE RESTRICT
);

-- registros_legados
CREATE TABLE registros_legados (
    id INTEGER NOT NULL,
    fonte_sha256 VARCHAR(64) NOT NULL,
    tabela VARCHAR(100) NOT NULL,
    chave_original VARCHAR(100) NOT NULL,
    empresa_id INTEGER,
    dados JSON NOT NULL,
    resultado VARCHAR(30) NOT NULL,
    motivo VARCHAR(500) NOT NULL,
    importado_em DATETIME NOT NULL,
    CONSTRAINT pk_registros_legados PRIMARY KEY (id),
    CONSTRAINT ck_registros_legados_resultado CHECK (resultado IN ('IMPORTADO','QUARENTENA')),
    CONSTRAINT fk_registros_legados_empresa_id_empresas FOREIGN KEY(empresa_id) REFERENCES empresas (id) ON DELETE RESTRICT,
    CONSTRAINT uq_registro_legado_origem UNIQUE (fonte_sha256, tabela, chave_original)
);
CREATE INDEX ix_registros_legados_empresa_id ON registros_legados (empresa_id);

-- alembic_version
CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Revisão Alembic deste esquema: "flask db upgrade" parte daqui.
INSERT INTO alembic_version (version_num) VALUES ('d41f0c2a9b7e');

-- =====================================================================================
-- Dados iniciais: catálogo de ações corretivas (o mesmo de PopularCatalogoService e do
-- comando "flask seed-catalog"). São recomendações, não medições de rede.
-- =====================================================================================
INSERT INTO recomendacoes (regra, codigo, titulo, acao) VALUES ('LOCALIZADA', 'local-cabo', 'Verificar conexão e alimentação', 'Verifique alimentação, cabo e porta do dispositivo. Compare com um equipamento que esteja respondendo.');
INSERT INTO recomendacoes (regra, codigo, titulo, acao) VALUES ('LOCALIZADA', 'local-config', 'Validar configuração', 'Confira IP, máscara e políticas de resposta ICMP do equipamento antes de concluir que há defeito físico.');
INSERT INTO recomendacoes (regra, codigo, titulo, acao) VALUES ('COMPARTILHADA', 'shared-link', 'Inspecionar infraestrutura compartilhada', 'Verifique os enlaces e equipamentos compartilhados pelos dispositivos afetados. A topologia não é conhecida automaticamente.');
INSERT INTO recomendacoes (regra, codigo, titulo, acao) VALUES ('COMPARTILHADA', 'shared-gateway', 'Comparar pontos de conectividade', 'Teste pontos intermediários autorizados e o gateway conhecido pela equipe para delimitar a interrupção.');
INSERT INTO recomendacoes (regra, codigo, titulo, acao) VALUES ('CONGESTIONAMENTO', 'loss-traffic', 'Verificar tráfego e interfaces', 'Analise utilização e erros das interfaces e procure tráfego intenso no intervalo da falha.');
INSERT INTO recomendacoes (regra, codigo, titulo, acao) VALUES ('CONGESTIONAMENTO', 'loss-link', 'Verificar enlaces', 'Compare perda e latência em pontos intermediários e inspecione os enlaces envolvidos.');
INSERT INTO recomendacoes (regra, codigo, titulo, acao) VALUES ('LATENCIA', 'latency-path', 'Investigar atraso', 'Compare a latência com o histórico e verifique utilização do equipamento e do caminho de rede.');
INSERT INTO recomendacoes (regra, codigo, titulo, acao) VALUES ('RECORRENTE', 'recurring-check', 'Investigar recorrência', 'Compare horários das ocorrências anteriores, conexões físicas e mudanças de configuração.');

COMMIT;
