import uuid
from datetime import datetime, timedelta, timezone
from flask import current_app
from services.monitoramento.resultado_sonda import CollectorError, ProbeResult


class InterpretarAmostraService:
    """Validates one sample sent by a collector. Raises ValueError with the rejection reason."""

    @staticmethod
    def data_utc(raw):
        if not isinstance(raw, str):
            raise ValueError('coletada_em ausente')
        value = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        if not value.tzinfo:
            raise ValueError('coletada_em deve informar o fuso (UTC)')
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def executar(self, item, agora):
        """(sample uid, device id, observed at, ProbeResult)."""
        cfg = current_app.config
        if not isinstance(item, dict):
            raise ValueError('amostra deve ser um objeto')
        unknown = set(item) - {'id', 'dispositivo_id', 'coletada_em', 'enviados', 'recebidos', 'latencia_ms'}
        if unknown:
            raise ValueError('campos não permitidos: ' + ', '.join(sorted(unknown)))
        uid = str(uuid.UUID(str(item.get('id'))))
        device_id = item.get('dispositivo_id')
        if isinstance(device_id, bool) or not isinstance(device_id, int):
            raise ValueError('dispositivo_id inválido')
        observed = self.data_utc(item.get('coletada_em'))
        if observed > agora + timedelta(seconds=cfg['COLLECTOR_MAX_CLOCK_SKEW_SECONDS']):
            raise ValueError('coletada_em no futuro; verifique o relógio do coletor')
        if observed < agora - timedelta(hours=cfg['COLLECTOR_MAX_SAMPLE_AGE_HOURS']):
            raise ValueError('amostra mais antiga que o limite aceito')
        latency = item.get('latencia_ms')
        if latency is not None and (isinstance(latency, bool) or not isinstance(latency, (int, float))):
            raise ValueError('latencia_ms inválida')
        sent = item.get('enviados')
        if isinstance(sent, int) and not isinstance(sent, bool) and sent > 100:
            raise ValueError('enviados acima do limite')
        try:
            result = ProbeResult(sent, item.get('recebidos'), float(latency) if latency is not None else None)
        except CollectorError as error:
            raise ValueError(str(error)) from error
        return uid, device_id, observed, result
