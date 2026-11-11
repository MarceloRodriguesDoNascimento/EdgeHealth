# Consultas de dispositivos, agenda de coleta e reserva
from sqlalchemy import func, or_, select, update
from app.extensions import db
from models import Dispositivo


# Consultas de dispositivos
class DispositivoRepository:
    # Um dispositivo da empresa
    @staticmethod
    def buscar_da_empresa(empresa_id, id, incluir_arquivados=True):
        query = select(Dispositivo).where(Dispositivo.id == id, Dispositivo.empresa_id == empresa_id)
        if not incluir_arquivados:
            query = query.where(Dispositivo.arquivado_em.is_(None))
        return db.session.scalar(query)

    # Inventário ordenado por nome
    @staticmethod
    def listar_da_empresa(empresa_id, incluir_arquivados):
        query = select(Dispositivo).where(Dispositivo.empresa_id == empresa_id)
        if not incluir_arquivados:
            query = query.where(Dispositivo.arquivado_em.is_(None))
        return db.session.scalars(query.order_by(Dispositivo.nome, Dispositivo.id)).all()

    # Dispositivos não arquivados da empresa
    @staticmethod
    def listar_ativos_da_empresa(empresa_id):
        return db.session.scalars(select(Dispositivo).where(Dispositivo.empresa_id == empresa_id,
                                                            Dispositivo.arquivado_em.is_(None))).all()

    # Verifica se já existe dispositivo ativo com o IP
    @staticmethod
    def existe_ip_ativo(empresa_id, ip):
        return db.session.scalar(select(Dispositivo.id).where(Dispositivo.empresa_id == empresa_id,
                                                              Dispositivo.ip == ip, Dispositivo.arquivado_em.is_(None))) is not None

    # Outros dispositivos medidos na mesma janela de tempo
    @staticmethod
    def pares_com_coleta_na_janela(empresa_id, exceto_id, inicio, fim):
        return db.session.scalars(select(Dispositivo).where(
            Dispositivo.empresa_id == empresa_id, Dispositivo.id != exceto_id, Dispositivo.arquivado_em.is_(None),
            Dispositivo.ultima_coleta >= inicio, Dispositivo.ultima_coleta <= fim)).all()

    # Dispositivos atribuídos a um coletor
    @staticmethod
    def listar_do_coletor(coletor_id, empresa_id):
        return db.session.scalars(select(Dispositivo).where(
            Dispositivo.coletor_id == coletor_id, Dispositivo.empresa_id == empresa_id,
            Dispositivo.arquivado_em.is_(None)).order_by(Dispositivo.id)).all()

    # Quantos dispositivos ativos o coletor mede
    @staticmethod
    def contar_ativos_do_coletor(coletor_id):
        return db.session.scalar(select(func.count()).select_from(Dispositivo).where(
            Dispositivo.coletor_id == coletor_id, Dispositivo.arquivado_em.is_(None)))

    # Dispositivos do worker local com coleta vencida
    @staticmethod
    def ids_devidos_para_coleta(agora, limite=500):
        return list(db.session.scalars(select(Dispositivo.id).where(
            Dispositivo.arquivado_em.is_(None), Dispositivo.coletor_id.is_(None),
            Dispositivo.proxima_coleta <= agora).order_by(Dispositivo.proxima_coleta).limit(limite)))

    # Reserva o dispositivo num único UPDATE
    @staticmethod
    def _reservar(id, dono, ate, agora, *condicoes):
        resultado = db.session.execute(update(Dispositivo).where(
            Dispositivo.id == id, Dispositivo.arquivado_em.is_(None), *condicoes,
            or_(Dispositivo.lease_until.is_(None), Dispositivo.lease_until < agora)).values(
                lease_owner=dono, lease_until=ate))
        return bool(resultado.rowcount)

    # Reserva para o worker local
    @classmethod
    def reservar_para_worker(cls, id, dono, ate, agora, devido_ate):
        return cls._reservar(id, dono, ate, agora, Dispositivo.coletor_id.is_(None),
                             Dispositivo.proxima_coleta <= devido_ate)

    # Reserva para o coletor dono do dispositivo
    @classmethod
    def reservar_para_coletor(cls, id, coletor_id, empresa_id, dono, ate, agora):
        return cls._reservar(id, dono, ate, agora, Dispositivo.coletor_id == coletor_id,
                             Dispositivo.empresa_id == empresa_id)

    # Libera a reserva
    @staticmethod
    def liberar_reserva(id, dono, **valores):
        db.session.execute(update(Dispositivo).where(Dispositivo.id == id, Dispositivo.lease_owner == dono)
                           .values(lease_owner=None, lease_until=None, **valores))
