# Caso de uso: gravar uma medição e abrir ou fechar falhas
import logging
from models import Falha, Impacto, Metrica, utcnow
from repositories import FalhaRepository, Transacao
from services.diagnosticos.atualizar_diagnosticos_service import AtualizarDiagnosticosService
from .classificar_status_service import ClassificarStatusService

log = logging.getLogger(__name__)


# Registro de medição
class RegistrarMedicaoService:
    # Grava a métrica, atualiza o status e as falhas
    def executar(self, dispositivo, resultado, observado_em=None, origem=None):
        now = observado_em or utcnow()
        origem = origem or {}
        if dispositivo.ultima_coleta and now <= dispositivo.ultima_coleta:
            return Metrica(dispositivo_id=dispositivo.id, coletada_em=now, respondeu=bool(resultado.received),
                           latencia_ms=resultado.latency_ms, pacotes_enviados=resultado.sent, pacotes_recebidos=resultado.received,
                           perda_pacotes_pct=resultado.loss, status=ClassificarStatusService.instantaneo(resultado),
                           fora_de_ordem=True, **origem).salvar(commit=False)
        dispositivo.status = ClassificarStatusService().executar(dispositivo, resultado)
        dispositivo.ultima_coleta = now
        dispositivo.latencia_ms = resultado.latency_ms
        dispositivo.perda_pacotes_pct = resultado.loss
        dispositivo.erro_coleta = None
        metric = Metrica(dispositivo_id=dispositivo.id, coletada_em=now, respondeu=bool(resultado.received),
                         latencia_ms=resultado.latency_ms, pacotes_enviados=resultado.sent, pacotes_recebidos=resultado.received,
                         perda_pacotes_pct=resultado.loss, status=dispositivo.status, **origem).salvar(commit=False)
        current = FalhaRepository.aberta_do_dispositivo(dispositivo.id)
        if dispositivo.status != 'ONLINE':
            kind = 'INDISPONIBILIDADE' if dispositivo.status == 'OFFLINE' else 'INSTABILIDADE'
            if not current:
                current = Falha(dispositivo_id=dispositivo.id, tipo=kind, estado='ABERTA', inicio=now, ultima_observacao=now,
                                descricao='Anomalia detectada por teste de conectividade.').salvar(commit=False)
                Impacto(falha_id=current.id).salvar(commit=False)
                log.info('Ocorrência aberta dispositivo=%s falha=%s', dispositivo.id, current.id)
            if kind == 'INDISPONIBILIDADE':
                current.tipo = kind
            current.ultima_observacao = now
        elif current:
            current.encerrar(now, 'RECUPERACAO')
            log.info('Ocorrência encerrada dispositivo=%s falha=%s', dispositivo.id, current.id)
        Transacao.enviar()
        AtualizarDiagnosticosService().executar(dispositivo.empresa_id, now, falha_extra=current)
        return metric
