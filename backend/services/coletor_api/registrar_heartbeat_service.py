from app import validation as v
from models import iso, utcnow
from repositories import Transacao
from services.coletores.estado_coletor import EstadoColetor
from .registrar_erro_coletor_service import RegistrarErroColetorService


class RegistrarHeartbeatService:
    """Version, pending queue and last error reported by the collector."""

    def executar(self, coletor, dados):
        if 'versao' in dados:
            coletor.versao = v.string(dados['versao'], 'Versão', 30)
        if 'fila_pendente' in dados:
            coletor.fila_pendente = v.integer(dados['fila_pendente'], 'Fila pendente', 0, 1000000)
        if dados.get('erro'):
            RegistrarErroColetorService().executar(coletor, dados['erro'], None)
        elif 'erro' in dados:
            coletor.ultimo_erro = None
        Transacao.confirmar()
        return dict(estado=EstadoColetor.calcular(coletor), servidor_em=iso(utcnow()))
