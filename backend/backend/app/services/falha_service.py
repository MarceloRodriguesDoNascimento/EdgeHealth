from app import db
from app.models import HistoricoFalha


def listar_falhas():
    return HistoricoFalha.query.order_by(HistoricoFalha.id.asc()).all()


def buscar_falha(falha_id):
    return db.session.get(HistoricoFalha, falha_id)


def criar_falha(dados):
    dados = dados or {}
    falha = HistoricoFalha(
        dispositivo_id=dados.get("dispositivo_id"),
        descricao=dados.get("descricao"),
    )
    db.session.add(falha)
    db.session.commit()
    return falha


def atualizar_falha(falha_id, dados):
    dados = dados or {}
    falha = db.session.get(HistoricoFalha, falha_id)
    if not falha:
        return None

    for campo in ["dispositivo_id", "descricao"]:
        if campo in dados:
            setattr(falha, campo, dados[campo])

    db.session.commit()
    return falha


def excluir_falha(falha_id):
    falha = db.session.get(HistoricoFalha, falha_id)
    if not falha:
        return False

    db.session.delete(falha)
    db.session.commit()
    return True
