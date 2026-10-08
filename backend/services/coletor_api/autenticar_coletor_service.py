from flask import current_app
from werkzeug.exceptions import TooManyRequests, Unauthorized
from models import Coletor, utcnow
from repositories import Transacao
from services.coletores.credencial_coletor import CredencialColetor
from services.comum.hash_token import HashToken


class AutenticarColetorService:
    """Bearer credential of a collector plus its per-minute request limit."""

    def executar(self, token):
        c = Coletor.buscar_um_por(token_hash=HashToken.sha256(token)) if token.startswith(CredencialColetor.PREFIXO) else None
        if not c or c.revogado_em:
            raise Unauthorized('Credencial de coletor inválida ou revogada.')
        now = utcnow()
        cfg = current_app.config
        if not c.janela_inicio or (now - c.janela_inicio).total_seconds() >= 60:
            c.janela_inicio, c.janela_requisicoes = now, 0
        if c.janela_requisicoes >= cfg['COLLECTOR_MAX_REQUESTS_PER_MINUTE']:
            Transacao.confirmar()
            raise TooManyRequests('Limite de requisições do coletor excedido. Aguarde e tente novamente.')
        c.atualizar(janela_requisicoes=c.janela_requisicoes + 1, ultimo_contato=now)
        return c
