from app import db
from app.models.dispositivo import Dispositivo


class DispositivoRepository:
    @staticmethod
    def listar_todos():
        return Dispositivo.query.order_by(Dispositivo.id.asc()).all()

    @staticmethod
    def buscar_por_id(dispositivo_id):
        return db.session.get(Dispositivo, dispositivo_id)

    @staticmethod
    def salvar(dispositivo):
        db.session.add(dispositivo)
        db.session.commit()
        return dispositivo

    @staticmethod
    def atualizar(dispositivo):
        db.session.commit()
        return dispositivo

    @staticmethod
    def deletar(dispositivo):
        db.session.delete(dispositivo)
        db.session.commit()
        return True
