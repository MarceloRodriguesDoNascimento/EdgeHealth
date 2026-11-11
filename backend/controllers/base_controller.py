# Classe-mãe dos Controllers: lê a requisição HTTP
from flask import g, jsonify, request
from werkzeug.exceptions import BadRequest
from app import validation as v


# Ferramentas comuns para ler a requisição e responder
class BaseController:
    # Lê o corpo JSON com campos permitidos e obrigatórios
    @staticmethod
    def payload(permitidos, obrigatorios=()):
        if not request.is_json:
            raise BadRequest('Envie um objeto JSON.')
        return v.json_object(request.get_json(), permitidos, obrigatorios)

    # Lê o corpo JSON sem validar
    @staticmethod
    def corpo():
        return request.get_json(silent=True) if request.is_json else None

    # Lê um parâmetro da URL
    @staticmethod
    def parametro(nome, padrao=None):
        return request.args.get(nome, padrao)

    # Usuário logado nesta requisição
    @staticmethod
    def usuario():
        return g.user

    # Empresa do usuário logado
    @staticmethod
    def empresa_id():
        return g.user.empresa_id

    # Devolve o dicionário como JSON com o código HTTP
    @staticmethod
    def resposta(dados, status=200):
        return jsonify(dados), status
