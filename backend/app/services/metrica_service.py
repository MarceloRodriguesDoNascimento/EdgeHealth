from app import db
from app.models import Metrica


def listar_metricas():
    return Metrica.query.order_by(Metrica.id.asc()).all()


def buscar_metrica(metrica_id):
    return db.session.get(Metrica, metrica_id)


def criar_metrica(dados):
    dados = dados or {}
    metrica = Metrica(
        dispositivo_id=dados.get("dispositivo_id"),
        tipo=dados.get("tipo"),
        valor=dados.get("valor"),
    )
    db.session.add(metrica)
    db.session.commit()
    return metrica


def atualizar_metrica(metrica_id, dados):
    dados = dados or {}
    metrica = db.session.get(Metrica, metrica_id)
    if not metrica:
        return None

    for campo in ["dispositivo_id", "tipo", "valor"]:
        if campo in dados:
            setattr(metrica, campo, dados[campo])

    db.session.commit()
    return metrica


def excluir_metrica(metrica_id):
    metrica = db.session.get(Metrica, metrica_id)
    if not metrica:
        return False

    db.session.delete(metrica)
    db.session.commit()
    return True