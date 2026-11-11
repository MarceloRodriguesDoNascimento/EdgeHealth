# Consultas dos dados do relatório exportado
from sqlalchemy import select
from app.extensions import db
from models import Diagnostico, Dispositivo, Falha, Metrica
from .paginacao import filtrar_periodo


# Consultas do relatório
class RelatorioRepository:
    # Limita a consulta à empresa e ao dispositivo
    @staticmethod
    def _escopo(query, empresa_id, dispositivo_id):
        query = query.where(Dispositivo.empresa_id == empresa_id)
        return query.where(Dispositivo.id == dispositivo_id) if dispositivo_id else query

    # Inventário, inclusive arquivados
    @classmethod
    def dispositivos(cls, empresa_id, dispositivo_id, limite):
        return db.session.scalars(cls._escopo(select(Dispositivo), empresa_id, dispositivo_id)
                                  .order_by(Dispositivo.id).limit(limite)).all()

    # Medições do período
    @classmethod
    def metricas(cls, empresa_id, dispositivo_id, inicio, fim, limite):
        query = cls._escopo(select(Metrica).join(Dispositivo, Dispositivo.id == Metrica.dispositivo_id),
                            empresa_id, dispositivo_id)
        query = filtrar_periodo(query, Metrica.coletada_em, inicio, fim)
        return db.session.scalars(query.order_by(Metrica.coletada_em, Metrica.id).limit(limite)).all()

    # Falhas que tocam o período
    @classmethod
    def falhas_sobrepostas(cls, empresa_id, dispositivo_id, inicio, fim, limite):
        query = cls._escopo(select(Falha).join(Dispositivo, Dispositivo.id == Falha.dispositivo_id),
                            empresa_id, dispositivo_id)
        if inicio:
            query = query.where((Falha.fim.is_(None)) | (Falha.fim >= inicio))
        if fim:
            query = query.where(Falha.inicio < fim)
        return db.session.scalars(query.order_by(Falha.inicio, Falha.id).limit(limite)).all()

    # Diagnósticos das falhas
    @staticmethod
    def diagnosticos(falha_ids, limite):
        return db.session.scalars(select(Diagnostico).where(Diagnostico.falha_id.in_(falha_ids))
                                  .order_by(Diagnostico.id).limit(limite)).all()
