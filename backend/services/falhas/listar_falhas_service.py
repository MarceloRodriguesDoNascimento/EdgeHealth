from werkzeug.exceptions import BadRequest
from app import validation as v
from repositories import FalhaRepository
from services.comum.serializador import Serializador
from services.dispositivos.obter_dispositivo_service import ObterDispositivoService


class ListarFalhasService:
    """Incident history filtered by device, severity, state and period, newest first, paginated.
    Parameters are the raw query-string texts; they are validated here."""

    SEVERIDADES = ('BAIXA', 'MEDIA', 'ALTA', 'CRITICA')
    ESTADOS = ('ABERTA', 'ENCERRADA')

    def executar(self, empresa_id, dispositivo_id=None, severidade=None, estado=None, inicio=None, fim=None,
                 pagina=None, limite=None):
        device_id = v.query_int(dispositivo_id, 'dispositivo_id')
        if device_id:
            ObterDispositivoService().buscar(empresa_id, device_id)
        for name, value, values in [('severidade', severidade, self.SEVERIDADES), ('estado', estado, self.ESTADOS)]:
            if value and value not in values:
                raise BadRequest(f'{name} inválido.')
        start, end = v.period(inicio, fim)
        page = v.query_int(pagina, 'pagina', 1, 1, 100000)
        limit = v.query_int(limite, 'limite', 50, 1, 500)
        rows, total = FalhaRepository.historico(empresa_id, device_id, severidade or None, estado or None,
                                                start, end, page, limit)
        return dict(items=[Serializador.falha(f) for f in rows], total=total, pagina=page, limite=limit)
