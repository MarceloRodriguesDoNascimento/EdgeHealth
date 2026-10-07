from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import CheckConstraint, Index, text
from sqlalchemy.types import String, TypeDecorator
from .extensions import db


class DecimalText(TypeDecorator):
    """Exact decimal stored as canonical text ("3000.00"): SQLite has no native decimal and
    Numeric would round-trip through float. Money is never a float in this application."""
    impl = String(24)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else str(Decimal(value))

    def process_result_value(self, value, dialect):
        return None if value is None else Decimal(value)

def utcnow():
    # SQLite stores naive UTC; all external dates explicitly include Z.
    return datetime.now(timezone.utc).replace(tzinfo=None)

def iso(value):
    return value.isoformat(timespec='milliseconds') + 'Z' if value else None

class Empresa(db.Model):
    __tablename__ = 'empresas'
    id = db.Column(db.Integer, primary_key=True)
    nome_fantasia = db.Column(db.String(150), nullable=False)
    cnpj = db.Column(db.String(14), nullable=False, unique=True)
    email = db.Column(db.String(254))
    telefone = db.Column(db.String(30))
    criada_em = db.Column(db.DateTime, nullable=False, default=utcnow)
    # Costs for the financial loss estimate (services/costs.py). NULL salary: not configured.
    salario_medio = db.Column(DecimalText())
    fator_encargos = db.Column(DecimalText(), nullable=False, default=Decimal('1.7'), server_default='1.7')
    horas_mes = db.Column(db.Integer, nullable=False, default=220, server_default='220')
    total_funcionarios = db.Column(db.Integer)
    expediente_dias = db.Column(db.String(7), nullable=False, default='12345', server_default='12345')  # ISO weekdays
    expediente_inicio = db.Column(db.String(5), nullable=False, default='08:00', server_default='08:00')
    expediente_fim = db.Column(db.String(5), nullable=False, default='18:00', server_default='18:00')
    fuso = db.Column(db.String(50), nullable=False, default='America/Sao_Paulo', server_default='America/Sao_Paulo')
    assistente_custos = db.Column(db.String(10))  # NULL: not offered yet; PULADO or CONCLUIDO

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id', ondelete='RESTRICT'), nullable=False, index=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(254), nullable=False, unique=True)
    senha_hash = db.Column(db.String(512), nullable=False)
    papel = db.Column(db.String(20), nullable=False, default='TECNICO')
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criada_em = db.Column(db.DateTime, nullable=False, default=utcnow)
    # Acceptance of the Terms of Use and acknowledgement of the Privacy Notice (not consent).
    termos_versao = db.Column(db.String(20))
    termos_aceitos_em = db.Column(db.DateTime)
    anonimizado_em = db.Column(db.DateTime)
    __table_args__ = (CheckConstraint("papel IN ('ADMIN','TECNICO')", name='papel'),)

class AuthSession(db.Model):
    __tablename__ = 'auth_sessions'
    id = db.Column(db.String(64), primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False, index=True)
    csrf_hash = db.Column(db.String(64), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)

class LoginAttempt(db.Model):
    __tablename__ = 'login_attempts'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)

class Coletor(db.Model):
    """Remote measurement agent running inside a company network. Never a user."""
    __tablename__ = 'coletores'
    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id', ondelete='RESTRICT'), nullable=False, index=True)
    nome = db.Column(db.String(100), nullable=False)
    token_hash = db.Column(db.String(64), nullable=False, unique=True)
    token_prefixo = db.Column(db.String(12), nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False, default=utcnow)
    rotacionado_em = db.Column(db.DateTime)
    revogado_em = db.Column(db.DateTime)
    ultimo_contato = db.Column(db.DateTime)
    versao = db.Column(db.String(30))
    fila_pendente = db.Column(db.Integer)
    ultimo_erro = db.Column(db.String(500))
    ultimo_erro_em = db.Column(db.DateTime)
    janela_inicio = db.Column(db.DateTime)
    janela_requisicoes = db.Column(db.Integer, nullable=False, default=0)

class Dispositivo(db.Model):
    __tablename__ = 'dispositivos'
    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id', ondelete='RESTRICT'), nullable=False, index=True)
    # NULL: measured by the local worker. Otherwise only this remote collector may measure it.
    coletor_id = db.Column(db.Integer, db.ForeignKey('coletores.id'), index=True)
    nome = db.Column(db.String(100), nullable=False)
    ip = db.Column(db.String(45), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)
    localizacao = db.Column(db.String(150), nullable=False)
    status = db.Column(db.String(10))
    ultima_coleta = db.Column(db.DateTime)
    latencia_ms = db.Column(db.Float)
    perda_pacotes_pct = db.Column(db.Float)
    falhas_consecutivas = db.Column(db.Integer, nullable=False, default=0)
    sucessos_consecutivos = db.Column(db.Integer, nullable=False, default=0)
    arquivado_em = db.Column(db.DateTime)
    criado_em = db.Column(db.DateTime, nullable=False, default=utcnow)
    erro_coleta = db.Column(db.String(500))
    lease_owner = db.Column(db.String(64))
    lease_until = db.Column(db.DateTime)
    proxima_coleta = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
    # Business impact (services/costs.py). NULL: fall back to the default for the device type.
    usuarios_dependentes = db.Column(db.Integer)
    perda_produtividade_pct = db.Column(db.Integer)
    receita_hora_dependente = db.Column(DecimalText())
    __table_args__ = (
        CheckConstraint("status IS NULL OR status IN ('ONLINE','INSTAVEL','OFFLINE')", name='status'),
        CheckConstraint('falhas_consecutivas >= 0 AND sucessos_consecutivos >= 0', name='counters'),
        CheckConstraint('latencia_ms IS NULL OR latencia_ms >= 0', name='latencia'),
        CheckConstraint('perda_pacotes_pct IS NULL OR perda_pacotes_pct BETWEEN 0 AND 100', name='perda'),
        Index('uq_dispositivo_ip_ativo', 'empresa_id', 'ip', unique=True,
              sqlite_where=text('arquivado_em IS NULL'), postgresql_where=text('arquivado_em IS NULL')),
    )

class Metrica(db.Model):
    __tablename__ = 'metricas'
    id = db.Column(db.Integer, primary_key=True)
    dispositivo_id = db.Column(db.Integer, db.ForeignKey('dispositivos.id', ondelete='RESTRICT'), nullable=False)
    coletada_em = db.Column(db.DateTime, nullable=False, default=utcnow)
    respondeu = db.Column(db.Boolean, nullable=False)
    latencia_ms = db.Column(db.Float)
    pacotes_enviados = db.Column(db.Integer, nullable=False)
    pacotes_recebidos = db.Column(db.Integer, nullable=False)
    perda_pacotes_pct = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(10), nullable=False)
    # Remote ingestion metadata. Local worker samples keep these NULL/False.
    coletor_id = db.Column(db.Integer, db.ForeignKey('coletores.id'))
    amostra_uid = db.Column(db.String(36))
    recebida_em = db.Column(db.DateTime)
    # Older than the device's last processed sample: kept as history, never drives the state machine.
    fora_de_ordem = db.Column(db.Boolean, nullable=False, default=False, server_default=text('0'))
    __table_args__ = (
        Index('ix_metricas_dispositivo_data', 'dispositivo_id', 'coletada_em'),
        Index('uq_metrica_coletor_amostra', 'coletor_id', 'amostra_uid', unique=True),
        CheckConstraint('pacotes_enviados > 0 AND pacotes_recebidos >= 0 AND pacotes_recebidos <= pacotes_enviados', name='pacotes'),
        CheckConstraint('perda_pacotes_pct BETWEEN 0 AND 100', name='perda'),
        CheckConstraint('latencia_ms IS NULL OR latencia_ms >= 0', name='latencia'),
        CheckConstraint("status IN ('ONLINE','INSTAVEL','OFFLINE')", name='status'),
    )

class Falha(db.Model):
    __tablename__ = 'falhas'
    id = db.Column(db.Integer, primary_key=True)
    dispositivo_id = db.Column(db.Integer, db.ForeignKey('dispositivos.id', ondelete='RESTRICT'), nullable=False)
    tipo = db.Column(db.String(30), nullable=False)
    estado = db.Column(db.String(15), nullable=False, default='ABERTA')
    inicio = db.Column(db.DateTime, nullable=False)
    fim = db.Column(db.DateTime)
    ultima_observacao = db.Column(db.DateTime, nullable=False)
    descricao = db.Column(db.String(500), nullable=False)
    severidade = db.Column(db.String(10), nullable=False, default='BAIXA')
    justificativa = db.Column(db.JSON, nullable=False, default=dict)
    encerramento = db.Column(db.String(30))
    __table_args__ = (
        Index('ix_falhas_dispositivo_inicio', 'dispositivo_id', 'inicio'),
        Index('uq_falha_aberta_dispositivo', 'dispositivo_id', unique=True,
              sqlite_where=text("estado = 'ABERTA'"), postgresql_where=text("estado = 'ABERTA'")),
        CheckConstraint("estado IN ('ABERTA','ENCERRADA')", name='estado'),
        CheckConstraint("tipo IN ('INSTABILIDADE','INDISPONIBILIDADE')", name='tipo'),
        CheckConstraint("severidade IN ('BAIXA','MEDIA','ALTA','CRITICA')", name='severidade'),
        CheckConstraint("(estado='ABERTA' AND fim IS NULL) OR (estado='ENCERRADA' AND fim IS NOT NULL)", name='ciclo'),
        CheckConstraint('fim IS NULL OR fim >= inicio', name='datas'),
    )

class Impacto(db.Model):
    __tablename__ = 'impactos'
    id = db.Column(db.Integer, primary_key=True)
    falha_id = db.Column(db.Integer, db.ForeignKey('falhas.id', ondelete='RESTRICT'), nullable=False, unique=True)
    usuarios_afetados = db.Column(db.Integer)
    origem = db.Column(db.String(30), nullable=False, default='NAO_INFORMADO')
    observacao = db.Column(db.String(500))
    atualizado_em = db.Column(db.DateTime, nullable=False, default=utcnow)
    custos_diretos = db.Column(DecimalText())  # technician, parts, penalties (R$)
    __table_args__ = (CheckConstraint('usuarios_afetados IS NULL OR usuarios_afetados >= 0', name='usuarios'),)

class Diagnostico(db.Model):
    __tablename__ = 'diagnosticos'
    id = db.Column(db.Integer, primary_key=True)
    falha_id = db.Column(db.Integer, db.ForeignKey('falhas.id', ondelete='RESTRICT'), nullable=False, unique=True)
    descricao = db.Column(db.Text, nullable=False)
    causas = db.Column(db.JSON, nullable=False, default=list)
    evidencias = db.Column(db.JSON, nullable=False, default=dict)
    estado = db.Column(db.String(30), nullable=False)
    analisado_em = db.Column(db.DateTime, nullable=False, default=utcnow)
    versao_regras = db.Column(db.String(20), nullable=False, default='1.0')
    __table_args__ = (CheckConstraint("estado IN ('DISPONIVEL','EVIDENCIA_INSUFICIENTE')", name='estado'),)

class Recomendacao(db.Model):
    __tablename__ = 'recomendacoes'
    id = db.Column(db.Integer, primary_key=True)
    regra = db.Column(db.String(50), nullable=False)
    codigo = db.Column(db.String(50), nullable=False, unique=True)
    titulo = db.Column(db.String(150), nullable=False)
    acao = db.Column(db.Text, nullable=False)

class DiagnosticoRecomendacao(db.Model):
    __tablename__ = 'diagnostico_recomendacoes'
    diagnostico_id = db.Column(db.Integer, db.ForeignKey('diagnosticos.id', ondelete='CASCADE'), primary_key=True)
    recomendacao_id = db.Column(db.Integer, db.ForeignKey('recomendacoes.id', ondelete='RESTRICT'), primary_key=True)

class RegistroLegado(db.Model):
    """Quarantined source records, never mixed with measured monitoring history."""
    __tablename__ = 'registros_legados'
    id = db.Column(db.Integer, primary_key=True)
    fonte_sha256 = db.Column(db.String(64), nullable=False)
    tabela = db.Column(db.String(100), nullable=False)
    chave_original = db.Column(db.String(100), nullable=False)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id', ondelete='RESTRICT'), index=True)
    dados = db.Column(db.JSON, nullable=False)
    resultado = db.Column(db.String(30), nullable=False)
    motivo = db.Column(db.String(500), nullable=False)
    importado_em = db.Column(db.DateTime, nullable=False, default=utcnow)
    __table_args__ = (
        db.UniqueConstraint('fonte_sha256', 'tabela', 'chave_original', name='uq_registro_legado_origem'),
        CheckConstraint("resultado IN ('IMPORTADO','QUARENTENA')", name='resultado'),
    )
