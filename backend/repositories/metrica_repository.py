# Consultas de medições
from sqlalchemy import func, select
from app.extensions import db
from models import Dispositivo, Metrica
from .paginacao import filtrar_periodo, paginar


# Consultas de métricas
class MetricaRepository:
    # Uma medição da empresa
    @staticmethod
    def buscar_da_empresa(empresa_id, id):
        return db.session.scalar(select(Metrica).join(Dispositivo).where(Metrica.id == id,
                                                                         Dispositivo.empresa_id == empresa_id))

    # Medições do período, paginadas
    @staticmethod
    def por_periodo(empresa_id, dispositivo_id, inicio, fim, pagina, limite):
        query = select(Metrica).join(Dispositivo).where(Dispositivo.empresa_id == empresa_id)
        if dispositivo_id:
            query = query.where(Metrica.dispositivo_id == dispositivo_id)
        query = filtrar_periodo(query, Metrica.coletada_em, inicio, fim)
        return paginar(query.order_by(Metrica.coletada_em, Metrica.id), pagina, limite)

    # Últimas medições de um dispositivo para os gráficos
    @staticmethod
    def serie_do_dispositivo(dispositivo_id, inicio, fim, limite=500):
        query = filtrar_periodo(select(Metrica).where(Metrica.dispositivo_id == dispositivo_id),
                                Metrica.coletada_em, inicio, fim)
        total = db.session.scalar(select(func.count()).select_from(query.subquery()))
        linhas = db.session.scalars(query.order_by(Metrica.coletada_em.desc(), Metrica.id.desc()).limit(limite)).all()
        return total, linhas

    # Medições recentes usadas no diagnóstico
    @staticmethod
    def recentes_na_janela(dispositivo_id, inicio, fim, limite=20):
        return db.session.scalars(select(Metrica).where(
            Metrica.dispositivo_id == dispositivo_id, Metrica.coletada_em >= inicio, Metrica.coletada_em <= fim)
            .order_by(Metrica.coletada_em.desc(), Metrica.id.desc()).limit(limite)).all()

    # Amostras do coletor que já foram gravadas
    @staticmethod
    def uids_existentes(coletor_id, uids):
        return set(db.session.scalars(select(Metrica.amostra_uid).where(Metrica.coletor_id == coletor_id,
                                                                        Metrica.amostra_uid.in_(uids))))
