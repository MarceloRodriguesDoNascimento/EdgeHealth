from sqlalchemy import func, select
from app.extensions import db
from models import Usuario


class UsuarioRepository:
    """Users limited to one company."""

    @staticmethod
    def listar_da_empresa(empresa_id):
        return db.session.scalars(select(Usuario).where(Usuario.empresa_id == empresa_id).order_by(Usuario.nome)).all()

    @staticmethod
    def buscar_da_empresa(empresa_id, id):
        return db.session.scalar(select(Usuario).where(Usuario.id == id, Usuario.empresa_id == empresa_id))

    @staticmethod
    def contar_admins_ativos(empresa_id):
        return db.session.scalar(select(func.count()).select_from(Usuario).where(
            Usuario.empresa_id == empresa_id, Usuario.papel == 'ADMIN', Usuario.ativo.is_(True)))
