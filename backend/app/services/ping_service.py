from datetime import datetime, timezone

from app import db
from app.models import Dispositivo, HistoricoFalha, Metrica


def registrar_ping(dispositivo_id: int, dados: dict):
    dispositivo = db.session.get(Dispositivo, dispositivo_id)
    if not dispositivo:
        return None

    agora = datetime.now(timezone.utc)
    status = dados.get("status", "online")

    dispositivo.status = status
    dispositivo.ultimo_ping = agora

    metrica = None
    metricas = dados.get("metricas", {})
    if metricas:
        metrica = Metrica(
            dispositivo_id=dispositivo.id,
            cpu_percent=metricas.get("cpu_percent"),
            memoria_percent=metricas.get("memoria_percent"),
            disco_percent=metricas.get("disco_percent"),
            temperatura_c=metricas.get("temperatura_c"),
            latencia_ms=metricas.get("latencia_ms"),
            coletada_em=agora,
        )
        db.session.add(metrica)

    falha = None
    if status in {"offline", "falha"}:
        falha = HistoricoFalha(
            dispositivo_id=dispositivo.id,
            tipo=dados.get("tipo_falha", "conectividade"),
            descricao=dados.get("descricao_falha", "Ping sem resposta"),
            ocorreu_em=agora,
        )
        db.session.add(falha)

    db.session.commit()

    return {
        "dispositivo": dispositivo,
        "metrica": metrica,
        "falha": falha,
    }
