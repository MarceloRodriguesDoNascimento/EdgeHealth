from sqlalchemy import select
from app.extensions import db
from models import Coletor


class ColetorRepository:
    """Remote collectors limited to one company."""

    @staticmethod
    def buscar_da_empresa(empresa_id, id):
        return db.session.scalar(select(Coletor).where(Coletor.id == id, Coletor.empresa_id == empresa_id))

    @staticmethod
    def listar_da_empresa(empresa_id):
        """Active collectors first, then by name."""
        return db.session.scalars(select(Coletor).where(Coletor.empresa_id == empresa_id)
                                  .order_by(Coletor.revogado_em.isnot(None), Coletor.nome, Coletor.id)).all()

    @staticmethod
    def ativos_da_empresa(empresa_id):
        return db.session.scalars(select(Coletor).where(Coletor.empresa_id == empresa_id,
                                                        Coletor.revogado_em.is_(None)).order_by(Coletor.nome)).all()
