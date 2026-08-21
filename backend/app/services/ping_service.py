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
    elif status in {"online", "instavel"}:
        dispositivo.latencia = 12.5 if status == "online" else 200.0
        dispositivo.perda_pacotes = 0.0 if status == "online" else 15.0

    db.session.commit()
    return dispositivo
