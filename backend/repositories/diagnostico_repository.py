# Consultas de diagnósticos e recomendações
from sqlalchemy import delete, select
from app.extensions import db
from models import Diagnostico, DiagnosticoRecomendacao, Dispositivo, Falha, Recomendacao


# Consultas de diagnóstico
class DiagnosticoRepository:
    # Um diagnóstico, só se for da empresa
    @staticmethod
    def buscar_da_empresa(empresa_id, id):
        return db.session.scalar(select(Diagnostico).join(Falha).join(Dispositivo).where(
            Diagnostico.id == id, Dispositivo.empresa_id == empresa_id))

    # Recomendações ligadas ao diagnóstico
    @staticmethod
    def recomendacoes_do_diagnostico(diagnostico_id):
        return db.session.scalars(select(Recomendacao).join(
            DiagnosticoRecomendacao, DiagnosticoRecomendacao.recomendacao_id == Recomendacao.id).where(
            DiagnosticoRecomendacao.diagnostico_id == diagnostico_id).order_by(Recomendacao.id)).all()

    # Apaga as ligações antes de recalcular
    @staticmethod
    def limpar_recomendacoes(diagnostico_id):
        db.session.execute(delete(DiagnosticoRecomendacao).where(DiagnosticoRecomendacao.diagnostico_id == diagnostico_id))

    # Recomendações das regras encontradas
    @staticmethod
    def recomendacoes_das_regras(regras):
        return db.session.scalars(select(Recomendacao).where(Recomendacao.regra.in_(regras))).all()

    # Catálogo completo de recomendações
    @staticmethod
    def catalogo():
        return db.session.scalars(select(Recomendacao).order_by(Recomendacao.regra, Recomendacao.id)).all()

    # Códigos já cadastrados no catálogo
    @staticmethod
    def codigos_do_catalogo():
        return set(db.session.scalars(select(Recomendacao.codigo)))
