from app import db
from app.models.empresa import Empresa


def listar_empresas():
    return Empresa.query.order_by(Empresa.id.asc()).all()


def buscar_empresa(empresa_id):
    return db.session.get(Empresa, empresa_id)


def criar_empresa(dados):
    dados = dados or {}
    empresa = Empresa(
        nome_fantasia=dados.get('nome_fantasia'),
        cnpj=dados.get('cnpj')
    )
    db.session.add(empresa)
    db.session.commit()
    return empresa


def atualizar_empresa(empresa_id, dados):
    dados = dados or {}
    empresa = db.session.get(Empresa, empresa_id)
    if not empresa:
        return None

    empresa.nome_fantasia = dados.get('nome_fantasia', empresa.nome_fantasia)
    empresa.cnpj = dados.get('cnpj', empresa.cnpj)

    db.session.commit()
    return empresa


def excluir_empresa(empresa_id):
    empresa = db.session.get(Empresa, empresa_id)
    if not empresa:
        return False

    db.session.delete(empresa)
    db.session.commit()
    return True