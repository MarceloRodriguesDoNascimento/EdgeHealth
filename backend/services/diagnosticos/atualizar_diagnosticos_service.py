from datetime import timedelta
from flask import current_app
from models import utcnow
from repositories import FalhaRepository, Transacao
from .analisar_falha_service import AnalisarFalhaService
from .calcular_severidade_service import CalcularSeveridadeService


class AtualizarDiagnosticosService:
    """Recalculates severity and diagnosis of every open incident of a company (plus `falha_extra`,
    e.g. the incident that has just been closed)."""

    def executar(self, empresa_id, agora=None, falha_extra=None):
        agora = agora or utcnow()
        window = current_app.config['DIAGNOSTIC_WINDOW_SECONDS']
        failures = list(FalhaRepository.abertas_da_empresa(empresa_id))
        if falha_extra and falha_extra.id not in {f.id for f in failures}:
            failures.append(falha_extra)
        # Incidents already closed still belong to the same event: without them, the severity
        # group and the shared-outage hypothesis of the last open incidents would shrink as the
        # other devices recover.
        pool = list(failures)
        if failures:
            earliest = min(f.inicio for f in failures) - timedelta(seconds=window)
            ids = {f.id for f in failures}
            pool += [f for f in FalhaRepository.encerradas_desde(empresa_id, earliest) if f.id not in ids]
        severidade, analise = CalcularSeveridadeService(), AnalisarFalhaService()
        for failure in failures:
            related = [f for f in pool if abs((f.inicio - failure.inicio).total_seconds()) <= window]
            severidade.executar(failure, len({f.dispositivo_id for f in related}), agora)
            # Keep the diagnosis that explained an incident at its last anomalous observation.
            if failure.estado == 'ABERTA':
                analise.executar(failure, related, agora)
        Transacao.enviar()
