from app import db
from app.models import Dispositivo, Empresa


def listar_dispositivos(empresa_id: int | None = None):
    query = Dispositivo.query.order_by(Dispositivo.created_at.desc())

    if empresa_id is not None:
        query = query.filter_by(empresa_id=empresa_id)

    return query.all()


def obter_dispositivo(dispositivo_id: int):
    return db.session.get(Dispositivo, dispositivo_id)


def criar_dispositivo(dados: dict):
    nome = dados.get("nome")
    identificador = dados.get("identificador")

    if not nome or not identificador:
        raise ValueError("nome e identificador sao obrigatorios")

    existente = Dispositivo.query.filter_by(identificador=identificador).first()
    if existente:
        raise ValueError("identificador ja cadastrado")

    empresa_id = dados.get("empresa_id")
    if empresa_id and not db.session.get(Empresa, empresa_id):
        raise ValueError("empresa nao encontrada")

    dispositivo = Dispositivo(
        nome=nome,
        identificador=identificador,
        tipo=dados.get("tipo", "sensor"),
        localizacao=dados.get("localizacao"),
        status=dados.get("status", "offline"),
        empresa_id=empresa_id,
    )

    db.session.add(dispositivo)
    db.session.commit()
    return dispositivo


def atualizar_dispositivo(dispositivo_id: int, dados: dict):
    dispositivo = obter_dispositivo(dispositivo_id)
    if not dispositivo:
        return None

    for campo in ("nome", "tipo", "localizacao", "status", "empresa_id"):
        if campo in dados:
            setattr(dispositivo, campo, dados[campo])

    if "identificador" in dados and dados["identificador"] != dispositivo.identificador:
        existente = Dispositivo.query.filter_by(identificador=dados["identificador"]).first()
        if existente:
            raise ValueError("identificador ja cadastrado")
        dispositivo.identificador = dados["identificador"]

    db.session.commit()
    return dispositivo


def excluir_dispositivo(dispositivo_id: int) -> bool:
    dispositivo = obter_dispositivo(dispositivo_id)
    if not dispositivo:
        return False

    db.session.delete(dispositivo)
    db.session.commit()
    return True
