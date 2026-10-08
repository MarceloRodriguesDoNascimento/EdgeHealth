from sqlalchemy import CheckConstraint, Index, text
from app.extensions import db
from .base import BaseModel


class Falha(BaseModel):
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

    def encerrar(self, quando, motivo):
        self.estado = 'ENCERRADA'
        self.fim = quando
        self.ultima_observacao = quando
        self.encerramento = motivo
