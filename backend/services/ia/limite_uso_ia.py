# Limita as explicações com IA por empresa por hora
import threading
import time
from werkzeug.exceptions import TooManyRequests


# Limite de uso
class LimiteUsoIa:
    _janela = 3600
    _usos = {}
    _trava = threading.Lock()

    # Conta um uso ou recusa se passou do limite
    @classmethod
    def registrar(cls, empresa_id, limite, agora=None):
        agora = time.monotonic() if agora is None else agora
        with cls._trava:
            recentes = [t for t in cls._usos.get(empresa_id, []) if agora - t < cls._janela]
            if len(recentes) >= limite:
                cls._usos[empresa_id] = recentes
                minutos = max(1, round((cls._janela - (agora - recentes[0])) / 60))
                raise TooManyRequests(f'Limite de {limite} explicações por hora atingido. Tente novamente em cerca de {minutos} min.')
            cls._usos[empresa_id] = recentes + [agora]

    # Devolve um uso que falhou antes da IA
    @classmethod
    def devolver(cls, empresa_id):
        with cls._trava:
            if cls._usos.get(empresa_id):
                cls._usos[empresa_id].pop()

    # Zera os contadores
    @classmethod
    def limpar(cls):
        with cls._trava:
            cls._usos.clear()
