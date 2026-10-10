from decimal import Decimal
from app.extensions import db
from .base import BaseModel, DecimalText, utcnow


class Empresa(BaseModel):
    __tablename__ = 'empresas'
    FATOR_ENCARGOS_PADRAO = Decimal('1.7')  # typical charges and benefits (INSS, FGTS, vacation, 13th)
    HORAS_MES_PADRAO = 220  # 44 h a week
    id = db.Column(db.Integer, primary_key=True)
    nome_fantasia = db.Column(db.String(150), nullable=False)
    cnpj = db.Column(db.String(14), nullable=False, unique=True)
    email = db.Column(db.String(254))
    telefone = db.Column(db.String(30))
    criada_em = db.Column(db.DateTime, nullable=False, default=utcnow)
    # Costs for the financial loss estimate (services/custos). NULL salary: not configured.
    salario_medio = db.Column(DecimalText())
    fator_encargos = db.Column(DecimalText(), nullable=False, default=FATOR_ENCARGOS_PADRAO, server_default='1.7')
    horas_mes = db.Column(db.Integer, nullable=False, default=HORAS_MES_PADRAO, server_default='220')
    total_funcionarios = db.Column(db.Integer)
    expediente_dias = db.Column(db.String(7), nullable=False, default='12345', server_default='12345')  # ISO weekdays
    expediente_inicio = db.Column(db.String(5), nullable=False, default='08:00', server_default='08:00')
    expediente_fim = db.Column(db.String(5), nullable=False, default='18:00', server_default='18:00')
    fuso = db.Column(db.String(50), nullable=False, default='America/Sao_Paulo', server_default='America/Sao_Paulo')
    assistente_custos = db.Column(db.String(10))  # NULL: not offered yet; PULADO or CONCLUIDO
