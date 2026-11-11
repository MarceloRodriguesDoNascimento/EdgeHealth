# Controle de transação usado pelos Services
from app.extensions import db


# Operações de transação
class Transacao:
    # Grava as alterações (commit)
    @staticmethod
    def confirmar():
        db.session.commit()

    # Desfaz as alterações (rollback)
    @staticmethod
    def desfazer():
        db.session.rollback()

    # Envia as alterações sem confirmar (flush)
    @staticmethod
    def enviar():
        db.session.flush()

    # Libera a sessão do banco
    @staticmethod
    def encerrar():
        db.session.remove()
