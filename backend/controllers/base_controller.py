from flask import g, jsonify, request
from werkzeug.exceptions import BadRequest
from app import validation as v


class BaseController:
    """Reads the HTTP request (JSON body, query string, authenticated user) for the controllers."""

    @staticmethod
    def payload(permitidos, obrigatorios=()):
        """JSON object with only the allowed fields and every required one filled."""
        if not request.is_json:
            raise BadRequest('Envie um objeto JSON.')
        return v.json_object(request.get_json(), permitidos, obrigatorios)

    @staticmethod
    def corpo():
        """Raw JSON body (None if absent or invalid), for a service that must look the resource up
        before validating the payload (404 of another company comes before 400)."""
        return request.get_json(silent=True) if request.is_json else None

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
