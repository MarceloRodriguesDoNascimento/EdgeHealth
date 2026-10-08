from werkzeug.exceptions import Conflict
from models import utcnow
from .obter_dispositivo_service import ObterDispositivoService


class SolicitarColetaService:
    """Brings the next measurement of the device forward (worker or remote collector)."""

    def executar(self, empresa_id, id):
        d = ObterDispositivoService().buscar(empresa_id, id, incluir_arquivados=False)
        if d.em_coleta(utcnow()):
            raise Conflict('Uma coleta já está em andamento.')
        d.atualizar(proxima_coleta=utcnow())
        who = 'O coletor remoto a executará ao sincronizar a configuração.' if d.coletor_id else 'O worker a executará no próximo ciclo.'
        return dict(mensagem='Coleta solicitada. ' + who)
