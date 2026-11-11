# Caso de uso: recalcular severidade e diagnóstico das falhas abertas
from datetime import timedelta
from flask import current_app
from models import utcnow
from repositories import FalhaRepository, Transacao
from .analisar_falha_service import AnalisarFalhaService
from .calcular_severidade_service import CalcularSeveridadeService


# Atualização de diagnósticos
class AtualizarDiagnosticosService:
    # Recalcula todas as falhas abertas da empresa
    def executar(self, empresa_id, agora=None, falha_extra=None):
        agora = agora or utcnow()
        window = current_app.config['DIAGNOSTIC_WINDOW_SECONDS']
        failures = list(FalhaRepository.abertas_da_empresa(empresa_id))
        if falha_extra and falha_extra.id not in {f.id for f in failures}:
            failures.append(falha_extra)
        pool = list(failures)
        if failures:
            earliest = min(f.inicio for f in failures) - timedelta(seconds=window)
            ids = {f.id for f in failures}
            pool += [f for f in FalhaRepository.encerradas_desde(empresa_id, earliest) if f.id not in ids]
        severidade, analise = CalcularSeveridadeService(), AnalisarFalhaService()
        for failure in failures:
            related = [f for f in pool if abs((f.inicio - failure.inicio).total_seconds()) <= window]
            severidade.executar(failure, len({f.dispositivo_id for f in related}), agora)
            if failure.estado == 'ABERTA':
                analise.executar(failure, related, agora)
        Transacao.enviar()
