from app import db
from app.models import Dispositivo


def listar_dispositivos():
    return Dispositivo.query.all()


def criar_dispositivo(dados):
    dispositivo = Dispositivo(
        nome=dados["nome"],
        identificador=dados["identificador"],
        status=dados.get("status", "offline"),
        empresa_id=dados.get("empresa_id"),
    )
    db.session.add(dispositivo)
    db.session.commit()
    return dispositivo


def atualizar_dispositivo(dispositivo_id, dados):
    dispositivo = db.session.get(Dispositivo, dispositivo_id)
    if not dispositivo:
        return None

    for campo in ["nome", "identificador", "status", "empresa_id"]:
        if campo in dados:
            setattr(dispositivo, campo, dados[campo])

    db.session.commit()
    return dispositivo


def excluir_dispositivo(dispositivo_id):
    dispositivo = db.session.get(Dispositivo, dispositivo_id)
    if not dispositivo:
        return False

    db.session.delete(dispositivo)
    db.session.commit()
    return True
