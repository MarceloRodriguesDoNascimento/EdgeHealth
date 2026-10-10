from sqlalchemy import func, select
from app.extensions import db
from models import Dispositivo, Metrica
from .paginacao import filtrar_periodo, paginar


class MetricaRepository:
    """Samples by period, per-device series and idempotency of remote ingestion."""

    @staticmethod
    def buscar_da_empresa(empresa_id, id):
        return db.session.scalar(select(Metrica).join(Dispositivo).where(Metrica.id == id,
                                                                         Dispositivo.empresa_id == empresa_id))

    @staticmethod
    def por_periodo(empresa_id, dispositivo_id, inicio, fim, pagina, limite):
        """Samples of the company (or of one device) in [inicio, fim), oldest first: (rows, total)."""
        query = select(Metrica).join(Dispositivo).where(Dispositivo.empresa_id == empresa_id)
        if dispositivo_id:
            query = query.where(Metrica.dispositivo_id == dispositivo_id)
        query = filtrar_periodo(query, Metrica.coletada_em, inicio, fim)
        return paginar(query.order_by(Metrica.coletada_em, Metrica.id), pagina, limite)

    @staticmethod
    def serie_do_dispositivo(dispositivo_id, inicio, fim, limite=500):
        """(total in the period, latest `limite` samples newest first) of one device."""
        query = filtrar_periodo(select(Metrica).where(Metrica.dispositivo_id == dispositivo_id),
                                Metrica.coletada_em, inicio, fim)
        total = db.session.scalar(select(func.count()).select_from(query.subquery()))
        linhas = db.session.scalars(query.order_by(Metrica.coletada_em.desc(), Metrica.id.desc()).limit(limite)).all()
        return total, linhas

    @staticmethod
    def recentes_na_janela(dispositivo_id, inicio, fim, limite=20):
        return db.session.scalars(select(Metrica).where(
            Metrica.dispositivo_id == dispositivo_id, Metrica.coletada_em >= inicio, Metrica.coletada_em <= fim)
            .order_by(Metrica.coletada_em.desc(), Metrica.id.desc()).limit(limite)).all()

    @staticmethod
    def uids_existentes(coletor_id, uids):
        return set(db.session.scalars(select(Metrica.amostra_uid).where(Metrica.coletor_id == coletor_id,
                                                                        Metrica.amostra_uid.in_(uids))))
