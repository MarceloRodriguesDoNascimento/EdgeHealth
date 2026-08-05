from datetime import datetime, timedelta, timezone

import jwt
from flask import current_app

from app import db
from app.models import Empresa, Usuario


def registrar_usuario(dados: dict):
    nome = dados.get("nome")
    email = dados.get("email")
    senha = dados.get("senha")

    if not nome or not email or not senha:
        raise ValueError("nome, email e senha sao obrigatorios")

    if Usuario.query.filter_by(email=email).first():
        raise ValueError("email ja cadastrado")

    empresa = None
    empresa_id = dados.get("empresa_id")
    empresa_nome = dados.get("empresa_nome")

    if empresa_id:
        empresa = db.session.get(Empresa, empresa_id)
        if not empresa:
            raise ValueError("empresa nao encontrada")
    elif empresa_nome:
        empresa = Empresa(nome=empresa_nome, cnpj=dados.get("cnpj"))
        db.session.add(empresa)

    usuario = Usuario(
        nome=nome,
        email=email,
        perfil=dados.get("perfil", "operador"),
        empresa=empresa,
    )
    usuario.set_password(senha)

    db.session.add(usuario)
    db.session.commit()
    return usuario


def autenticar_usuario(email: str, senha: str):
    usuario = Usuario.query.filter_by(email=email).first()
    if not usuario or not usuario.ativo or not usuario.check_password(senha):
        return None
    return usuario


def gerar_token(usuario: Usuario) -> str:
    payload = {
        "sub": str(usuario.id),
        "email": usuario.email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=8),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")
