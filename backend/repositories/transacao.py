from app.extensions import db


class Transacao:
    """Transaction boundary used by the services (they never touch the session directly)."""

    @staticmethod
    def confirmar():
        db.session.commit()

    @staticmethod
    def desfazer():
        db.session.rollback()

    @staticmethod
    def enviar():
        """Sends pending changes (flush) so generated ids are available inside the transaction."""
        db.session.flush()

    @staticmethod
    def encerrar():
        """Releases the session/connection, e.g. before a network probe."""
        db.session.remove()
