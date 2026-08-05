from app.models import Usuario


def autenticar_usuario(email, senha):
    usuario = Usuario.query.filter_by(email=email, senha=senha).first()
    return usuario
