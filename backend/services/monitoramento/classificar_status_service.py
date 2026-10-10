from flask import current_app


class ClassificarStatusService:
    """Status state machine: OFFLINE/recovery need confirmations; latency or loss make it INSTAVEL."""

    def executar(self, dispositivo, resultado):
        cfg = current_app.config
        if resultado.received == 0:
            dispositivo.falhas_consecutivas += 1
            dispositivo.sucessos_consecutivos = 0
            return 'OFFLINE' if dispositivo.falhas_consecutivas >= cfg['OFFLINE_AFTER'] else 'INSTAVEL'
        dispositivo.falhas_consecutivas = 0
        degraded = resultado.loss >= cfg['LOSS_LIMIT_PCT'] or resultado.latency_ms >= cfg['LATENCY_LIMIT_MS']
        if degraded:
            dispositivo.sucessos_consecutivos = 0
            return 'INSTAVEL'
        dispositivo.sucessos_consecutivos += 1
        if dispositivo.status in ('OFFLINE', 'INSTAVEL') and dispositivo.sucessos_consecutivos < cfg['RECOVERY_AFTER']:
            return 'INSTAVEL'
        return 'ONLINE'

    @staticmethod
    def instantaneo(resultado):
        """Stateless classification of a single sample, without confirmation counters."""
        cfg = current_app.config
        if resultado.received == 0:
            return 'OFFLINE'
        if resultado.loss >= cfg['LOSS_LIMIT_PCT'] or resultado.latency_ms >= cfg['LATENCY_LIMIT_MS']:
            return 'INSTAVEL'
        return 'ONLINE'
