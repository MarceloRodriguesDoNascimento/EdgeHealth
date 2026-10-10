class ValidarConfiguracaoMonitorService:
    """Refuses limits that would make the measurement or the classification untrustworthy."""

    def executar(self, cfg):
        if not 1 <= cfg['MONITOR_PACKETS'] <= 10 or not 0.1 <= cfg['MONITOR_TIMEOUT'] <= 10:
            raise ValueError('MONITOR_PACKETS deve estar entre 1 e 10 e MONITOR_TIMEOUT entre 0.1 e 10.')
        if not 1 <= cfg['MONITOR_INTERVAL'] <= 86400 or not 1 <= cfg['MONITOR_WORKERS'] <= 16:
            raise ValueError('Intervalo ou quantidade de workers inválida.')
        bound = cfg['MONITOR_PACKETS'] * (cfg['MONITOR_TIMEOUT'] + 0.2) + 10
        if cfg['MONITOR_LEASE_SECONDS'] <= bound:
            raise ValueError('MONITOR_LEASE_SECONDS deve superar a duração máxima da coleta com margem de 10 segundos.')
        if cfg['OFFLINE_AFTER'] < 2 or cfg['RECOVERY_AFTER'] < 1 or cfg['LATENCY_LIMIT_MS'] <= 0 or not 0 < cfg['LOSS_LIMIT_PCT'] <= 100:
            raise ValueError('Limites de classificação inválidos.')
