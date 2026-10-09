"""The only class that talks to the Gemini API (Google). REST generateContent with urllib: no extra
dependency. The key comes from GEMINI_API_KEY (.env) and travels in a header, never in the URL,
a log or an error message."""
import json
import logging
import socket
import urllib.error
import urllib.request
from flask import current_app
from werkzeug.exceptions import BadGateway, ServiceUnavailable

log = logging.getLogger(__name__)
URL = 'https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent'


class RespostaHttp:
    """Status and body returned by a transport (also used by the tests' fake transport)."""

    def __init__(self, status, corpo):
        self.status, self.corpo = status, corpo


def transporte_urllib(url, cabecalhos, corpo, timeout):
    request = urllib.request.Request(url, data=corpo, headers=cabecalhos, method='POST')
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return RespostaHttp(response.status, response.read())
    except urllib.error.HTTPError as error:
        return RespostaHttp(error.code, error.read())


class GeminiService:
    SEM_CHAVE = 'IA não configurada neste servidor.'

    def __init__(self, transporte=None):
        self.transporte = transporte or transporte_urllib

    @staticmethod
    def disponivel():
        return bool(current_app.config.get('GEMINI_API_KEY'))

    def executar(self, instrucao, prompt, max_tokens=2048):
        """Generated text; 503 when unavailable (no key, quota, network), 502 for an unusable answer."""
        cfg = current_app.config
        if not self.disponivel():
            raise ServiceUnavailable(self.SEM_CHAVE)
        corpo = json.dumps({
            'systemInstruction': {'parts': [{'text': instrucao}]},
            'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
            'generationConfig': {'temperature': 0.3, 'maxOutputTokens': max_tokens},
        }).encode('utf-8')
        cabecalhos = {'Content-Type': 'application/json', 'x-goog-api-key': cfg['GEMINI_API_KEY']}
        try:
            resposta = self.transporte(URL.format(modelo=cfg['GEMINI_MODEL']), cabecalhos, corpo, cfg['GEMINI_TIMEOUT_SECONDS'])
        except (TimeoutError, socket.timeout):
            raise ServiceUnavailable('A IA demorou demais para responder. Tente novamente em instantes.') from None
        except (urllib.error.URLError, OSError):
            raise ServiceUnavailable('Não foi possível conectar ao serviço de IA. Tente novamente mais tarde.') from None
        return self._texto(resposta)

    @staticmethod
    def _texto(resposta):
        try:
            dados = json.loads(resposta.corpo or b'{}')
        except ValueError:
            dados = {}
        if resposta.status == 429:
            raise ServiceUnavailable('A cota gratuita da IA foi atingida. Tente novamente mais tarde.')
        if resposta.status in (401, 403) or (resposta.status == 400 and 'API_KEY' in json.dumps(dados)):
            log.error('Gemini recusou a credencial (HTTP %s). Verifique GEMINI_API_KEY.', resposta.status)
            raise BadGateway('O serviço de IA recusou a credencial configurada neste servidor.')
        if resposta.status == 404:
            log.error('Modelo Gemini não encontrado (HTTP 404). Verifique GEMINI_MODEL.')
            raise BadGateway('O modelo de IA configurado neste servidor não está disponível.')
        if resposta.status >= 500:
            raise ServiceUnavailable('O serviço de IA está indisponível no momento. Tente novamente mais tarde.')
        if resposta.status != 200:
            log.error('Gemini respondeu HTTP %s.', resposta.status)
            raise BadGateway('O serviço de IA não conseguiu processar o pedido.')
        candidatos = dados.get('candidates') or []
        partes = ((candidatos[0].get('content') or {}).get('parts') or []) if candidatos else []
        texto = '\n'.join(p.get('text', '') for p in partes if not p.get('thought')).strip()
        if not texto:
            motivo = (dados.get('promptFeedback') or {}).get('blockReason') or (candidatos[0].get('finishReason') if candidatos else None)
            log.warning('Gemini sem texto na resposta (motivo=%s).', motivo)
            raise BadGateway('A IA não devolveu uma explicação. Tente novamente.')
        return texto
