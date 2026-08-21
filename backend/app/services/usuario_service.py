from app import db
from app.models import Usuario


def listar_usuarios():
    return Usuario.query.order_by(Usuario.id.asc()).all()


def buscar_usuario(usuario_id):
    return db.session.get(Usuario, usuario_id)


def criar_usuario(dados):
    dados = dados or {}
    usuario = Usuario(
        nome=dados.get("nome"),
        email=dados.get("email"),
        senha=dados.get("senha"),
        empresa_id=dados.get("empresa_id"),
    )
    db.session.add(usuario)
    db.session.commit()
    return usuario


def atualizar_usuario(usuario_id, dados):
    dados = dados or {}
    usuario = db.session.get(Usuario, usuario_id)
    if not usuario:
        return None

    for campo in ["nome", "email", "senha", "empresa_id"]:
        if campo in dados:
            setattr(usuario, campo, dados[campo])

    db.session.commit()
    return usuario


def excluir_usuario(usuario_id):
    usuario = db.session.get(Usuario, usuario_id)
    if not usuario:
        return False

    db.session.delete(usuario)
    db.session.commit()
    return True