from werkzeug.exceptions import BadRequest
from app import validation as v
from repositories import MetricaRepository
from services.comum.serializador import Serializador
from services.dispositivos.obter_dispositivo_service import ObterDispositivoService


class ListarMetricasService:
    """Samples by period (default: last 7 days), optionally of one device and one metric type.
    Parameters are the raw query-string texts; they are validated here."""

    TIPOS = ('latencia', 'perda_pacotes', 'disponibilidade')

    def executar(self, empresa_id, dispositivo_id=None, tipo=None, inicio=None, fim=None, pagina=None, limite=None):
        device_id = v.query_int(dispositivo_id, 'dispositivo_id')
        if device_id:
            ObterDispositivoService().buscar(empresa_id, device_id)
        if tipo and tipo not in self.TIPOS:
            raise BadRequest('Tipo de métrica inválido.')
        start, end = v.period(inicio, fim, 7)
        page = v.query_int(pagina, 'pagina', 1, 1, 100000)
        limit = v.query_int(limite, 'limite', 50, 1, 500)
        rows, total = MetricaRepository.por_periodo(empresa_id, device_id, start, end, page, limit)
        return dict(items=[self._selecionar(m, tipo) for m in rows], total=total, pagina=page, limite=limit)

    @staticmethod
    def _selecionar(metrica, tipo):
        result = Serializador.metrica(metrica)
        if tipo in ('perda_pacotes', 'disponibilidade'): result.pop('latencia_ms')
        if tipo in ('latencia', 'disponibilidade'): result.pop('perda_pacotes_pct')
        return result
