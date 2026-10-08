from flask import g, jsonify, request
from werkzeug.exceptions import BadRequest


class BaseController:
    """Reads the HTTP request (JSON body, query string, authenticated user) for the controllers."""

    @staticmethod
    def payload(permitidos, obrigatorios=()):
        """JSON object with only the allowed fields and every required one filled."""
        if not request.is_json:
            raise BadRequest('Envie um objeto JSON.')
        data = request.get_json()
        if not isinstance(data, dict):
            raise BadRequest('Envie um objeto JSON.')
        unknown = set(data) - set(permitidos)
        if unknown:
            raise BadRequest('Campos não permitidos: ' + ', '.join(sorted(unknown)))
        for field in obrigatorios:
            if field not in data or data[field] is None or data[field] == '':
                raise BadRequest(f'O campo {field} é obrigatório.')
        return data

    @staticmethod
    def parametro(nome, padrao=None):
        """Raw query-string value (validated by the service)."""
        return request.args.get(nome, padrao)

    @staticmethod
    def usuario():
        return g.user

    @staticmethod
    def empresa_id():
        return g.user.empresa_id

    @staticmethod
    def resposta(dados, status=200):
        return jsonify(dados), status
