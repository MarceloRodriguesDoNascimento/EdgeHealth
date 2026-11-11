# Consultas de coletores de uma empresa
from sqlalchemy import select
from app.extensions import db
from models import Coletor


# Consultas de coletores
class ColetorRepository:
    # Um coletor da empresa
    @staticmethod
    def buscar_da_empresa(empresa_id, id):
        return db.session.scalar(select(Coletor).where(Coletor.id == id, Coletor.empresa_id == empresa_id))

    # Coletores da empresa, ativos primeiro
    @staticmethod
    def listar_da_empresa(empresa_id):
        return db.session.scalars(select(Coletor).where(Coletor.empresa_id == empresa_id)
                                  .order_by(Coletor.revogado_em.isnot(None), Coletor.nome, Coletor.id)).all()

    # Coletores não revogados
    @staticmethod
    def ativos_da_empresa(empresa_id):
        return db.session.scalars(select(Coletor).where(Coletor.empresa_id == empresa_id,
                                                        Coletor.revogado_em.is_(None)).order_by(Coletor.nome)).all()
