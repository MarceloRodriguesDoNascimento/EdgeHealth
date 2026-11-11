# Model dos dispositivos monitorados
from sqlalchemy import CheckConstraint, Index, text
from app.extensions import db
from .base import BaseModel, DecimalText, utcnow


# Tabela dispositivos
class Dispositivo(BaseModel):
    __tablename__ = 'dispositivos'
    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id', ondelete='RESTRICT'), nullable=False, index=True)
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

    # Diz se o dispositivo está sendo medido agora
    def em_coleta(self, agora):
        return bool(self.lease_until and self.lease_until > agora)

    # Zera o estado atual do dispositivo
    def reiniciar_estado(self):
        self.status = None
        self.ultima_coleta = None
        self.latencia_ms = self.perda_pacotes_pct = None
        self.falhas_consecutivas = self.sucessos_consecutivos = 0
