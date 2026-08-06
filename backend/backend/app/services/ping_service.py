from app import db
from app.models import Dispositivo, HistoricoFalha


def registrar_ping(dispositivo_id, status="online"):
    dispositivo = db.session.get(Dispositivo, dispositivo_id)
    if not dispositivo:
        return None

    dispositivo.status = status

    if status == "falha":
        db.session.add(
            HistoricoFalha(
                dispositivo_id=dispositivo.id,
                descricao="Falha registrada pelo ping",
            )
        )

    db.session.commit()
    return dispositivo
