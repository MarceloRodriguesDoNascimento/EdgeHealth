from app.models import Usuario


def autenticar_usuario(email, senha):
    if not email or not senha:
        return None
    return Usuario.query.filter_by(email=email, senha=senha).first()
