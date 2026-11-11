# Caso de uso: registrar erro do próprio coletor
from datetime import timedelta
from flask import current_app
from werkzeug.exceptions import BadRequest
from app import validation as v
from models import utcnow


# Registro de erro do coletor
class RegistrarErroColetorService:
    TIPOS = ('PERMISSAO_ICMP', 'FALHA_COLETOR')

    # Grava o erro informado
    def executar(self, coletor, item, dispositivos):
        if not isinstance(item, dict) or item.get('tipo') not in self.TIPOS:
            raise BadRequest('Erro do coletor inválido.')
        message = v.string(item.get('mensagem') or item['tipo'], 'Mensagem', 300)
        label = 'Coletor sem permissão para ICMP' if item['tipo'] == 'PERMISSAO_ICMP' else 'Falha no coletor'
        coletor.ultimo_erro = f'{label}: {message}'[:500]
        coletor.ultimo_erro_em = utcnow()
        if dispositivos is not None:
            for device in dispositivos:
                device.erro_coleta = coletor.ultimo_erro
                device.proxima_coleta = utcnow() + timedelta(seconds=current_app.config['MONITOR_INTERVAL'])
