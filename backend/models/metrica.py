from sqlalchemy import CheckConstraint, Index, text
from app.extensions import db
from .base import BaseModel, utcnow


class Metrica(BaseModel):
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
