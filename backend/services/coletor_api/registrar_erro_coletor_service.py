from datetime import timedelta
from flask import current_app
from werkzeug.exceptions import BadRequest
from app import validation as v
from models import utcnow


class RegistrarErroColetorService:
    """A failure of the collector itself (not of the network): shown to the user, never a sample."""

    TIPOS = ('PERMISSAO_ICMP', 'FALHA_COLETOR')

    def executar(self, coletor, item, dispositivos):
        if not isinstance(item, dict) or item.get('tipo') not in self.TIPOS:
            raise BadRequest('Erro do coletor inválido.')
        message = v.string(item.get('mensagem') or item['tipo'], 'Mensagem', 300)
        label = 'Coletor sem permissão para ICMP' if item['tipo'] == 'PERMISSAO_ICMP' else 'Falha no coletor'
        coletor.ultimo_erro = f'{label}: {message}'[:500]
        coletor.ultimo_erro_em = utcnow()
        if dispositivos is not None:
            # The device was NOT measured: no sample, no status change, no incident.
            for device in dispositivos:
                device.erro_coleta = coletor.ultimo_erro
                device.proxima_coleta = utcnow() + timedelta(seconds=current_app.config['MONITOR_INTERVAL'])
