from sqlalchemy import func, or_, select, update
from app.extensions import db
from models import Dispositivo


class DispositivoRepository:
    """Device queries limited to one company, collection scheduling and the exclusive lease."""

    @staticmethod
    def buscar_da_empresa(empresa_id, id, incluir_arquivados=True):
        query = select(Dispositivo).where(Dispositivo.id == id, Dispositivo.empresa_id == empresa_id)
        if not incluir_arquivados:
            query = query.where(Dispositivo.arquivado_em.is_(None))
        return db.session.scalar(query)

    @staticmethod
    def listar_da_empresa(empresa_id, incluir_arquivados):
        query = select(Dispositivo).where(Dispositivo.empresa_id == empresa_id)
        if not incluir_arquivados:
            query = query.where(Dispositivo.arquivado_em.is_(None))
        return db.session.scalars(query.order_by(Dispositivo.nome, Dispositivo.id)).all()

    @staticmethod
    def listar_ativos_da_empresa(empresa_id):
        return db.session.scalars(select(Dispositivo).where(Dispositivo.empresa_id == empresa_id,
                                                            Dispositivo.arquivado_em.is_(None))).all()

    @staticmethod
    def existe_ip_ativo(empresa_id, ip):
        return db.session.scalar(select(Dispositivo.id).where(Dispositivo.empresa_id == empresa_id,
                                                              Dispositivo.ip == ip, Dispositivo.arquivado_em.is_(None))) is not None

    @staticmethod
    def pares_com_coleta_na_janela(empresa_id, exceto_id, inicio, fim):
        """Other active devices of the company measured inside [inicio, fim]."""
        return db.session.scalars(select(Dispositivo).where(
            Dispositivo.empresa_id == empresa_id, Dispositivo.id != exceto_id, Dispositivo.arquivado_em.is_(None),
            Dispositivo.ultima_coleta >= inicio, Dispositivo.ultima_coleta <= fim)).all()

    # --- Remote collector ------------------------------------------------------------------------
    @staticmethod
    def listar_do_coletor(coletor_id, empresa_id):
        return db.session.scalars(select(Dispositivo).where(
            Dispositivo.coletor_id == coletor_id, Dispositivo.empresa_id == empresa_id,
            Dispositivo.arquivado_em.is_(None)).order_by(Dispositivo.id)).all()

    @staticmethod
    def contar_ativos_do_coletor(coletor_id):
        return db.session.scalar(select(func.count()).select_from(Dispositivo).where(
            Dispositivo.coletor_id == coletor_id, Dispositivo.arquivado_em.is_(None)))

    # --- Local worker scheduling and lease -------------------------------------------------------
    @staticmethod
    def ids_devidos_para_coleta(agora, limite=500):
        """Active devices of the local worker whose next collection is due (oldest first)."""
        return list(db.session.scalars(select(Dispositivo.id).where(
            Dispositivo.arquivado_em.is_(None), Dispositivo.coletor_id.is_(None),
            Dispositivo.proxima_coleta <= agora).order_by(Dispositivo.proxima_coleta).limit(limite)))

    @staticmethod
    def _reservar(id, dono, ate, agora, *condicoes):
        resultado = db.session.execute(update(Dispositivo).where(
            Dispositivo.id == id, Dispositivo.arquivado_em.is_(None), *condicoes,
            or_(Dispositivo.lease_until.is_(None), Dispositivo.lease_until < agora)).values(
                lease_owner=dono, lease_until=ate))
        return bool(resultado.rowcount)

    @classmethod
    def reservar_para_worker(cls, id, dono, ate, agora, devido_ate):
        """Atomic lease for the local worker: never a device assigned to a remote collector."""
        return cls._reservar(id, dono, ate, agora, Dispositivo.coletor_id.is_(None),
                             Dispositivo.proxima_coleta <= devido_ate)

    @classmethod
    def reservar_para_coletor(cls, id, coletor_id, empresa_id, dono, ate, agora):
        """Atomic lease for an ingestion request of the collector that owns the device."""
        return cls._reservar(id, dono, ate, agora, Dispositivo.coletor_id == coletor_id,
                             Dispositivo.empresa_id == empresa_id)

    @staticmethod
    def liberar_reserva(id, dono, **valores):
        """Releases the lease only if it still belongs to `dono`, writing `valores` with it."""
        db.session.execute(update(Dispositivo).where(Dispositivo.id == id, Dispositivo.lease_owner == dono)
                           .values(lease_owner=None, lease_until=None, **valores))
