from datetime import timedelta
from flask import current_app
from models import Diagnostico, DiagnosticoRecomendacao, Dispositivo, iso
from repositories import DiagnosticoRepository, DispositivoRepository, FalhaRepository, MetricaRepository


class AnalisarFalhaService:
    """Rule-based probable causes of an open incident, with the evidence used and the actions."""

    def executar(self, falha, relacionadas, agora):
        cfg = current_app.config
        device = Dispositivo.buscar_por_id(falha.dispositivo_id)
        window_start = agora - timedelta(seconds=cfg['DIAGNOSTIC_WINDOW_SECONDS'])
        samples = MetricaRepository.recentes_na_janela(device.id, window_start, agora, limite=20)
        diag = Diagnostico.buscar_um_por(falha_id=falha.id)
        # Re-analysis triggered by another device's sample (e.g. a collector catching up after an
        # outage) may find no sample of this device in the window: that is missing data, not new
        # evidence, so it must not replace the existing explanation with EVIDENCIA_INSUFICIENTE.
        if not samples and diag:
            return diag
        latest = samples[0] if samples else None
        recovering = (latest and latest.status == 'INSTAVEL' and latest.respondeu
                      and latest.latencia_ms is not None and latest.latencia_ms < cfg['LATENCY_LIMIT_MS']
                      and latest.perda_pacotes_pct < cfg['LOSS_LIMIT_PCT'])
        # The first healthy sample confirms recovery but must not erase the last
        # explanation of the anomaly that will be shown in the closed incident.
        if recovering and diag:
            return diag
        peers = DispositivoRepository.pares_com_coleta_na_janela(device.empresa_id, device.id, window_start, agora)
        previous = FalhaRepository.ids_anteriores_do_dispositivo(device.id, falha.id, agora - timedelta(days=7), agora, limite=20)
        causes = []
        if latest and latest.status == 'OFFLINE' and any(p.status == 'ONLINE' for p in peers):
            causes.append(dict(regra='LOCALIZADA', descricao='Possível problema localizado no dispositivo, alimentação, cabo, porta ou política de resposta ICMP; outros dispositivos da empresa responderam.'))
        # Correlation uses the incidents, not the peers' status at this instant: in a group outage
        # the peers recover in collector/batch order, and an analysis between two recoveries must
        # not drop COMPARTILHADA from the device still offline. A peer counts when its confirmed
        # unavailability overlapped this one and either already ended (observed outage) or is
        # still open with a current observation (stale peers are not evidence).
        current_peers = {p.id for p in peers}
        shared = {device.id} | {f.dispositivo_id for f in relacionadas
                                if f.tipo == 'INDISPONIBILIDADE' and f.dispositivo_id != device.id
                                and ((f.estado == 'ABERTA' and f.dispositivo_id in current_peers)
                                     or (f.estado == 'ENCERRADA' and f.fim and f.fim >= falha.inicio))}
        if latest and latest.status == 'OFFLINE' and len(shared) >= 2:
            causes.append(dict(regra='COMPARTILHADA', descricao='Possível interrupção de infraestrutura compartilhada: vários dispositivos ficaram indisponíveis em uma janela semelhante. A topologia não foi determinada.'))
        if latest and latest.respondeu and latest.latencia_ms is not None:
            if latest.latencia_ms >= cfg['LATENCY_LIMIT_MS'] and latest.perda_pacotes_pct >= cfg['LOSS_LIMIT_PCT']:
                causes.append(dict(regra='CONGESTIONAMENTO', descricao='Possível congestionamento ou enlace instável: latência e perda de pacotes elevadas na amostra recente.'))
            elif latest.latencia_ms >= cfg['LATENCY_LIMIT_MS']:
                causes.append(dict(regra='LATENCIA', descricao='Possível saturação ou caminho de rede degradado: latência elevada com perda abaixo do limite.'))
        if latest and len(previous) >= 2:
            causes.append(dict(regra='RECORRENTE', descricao='Possível instabilidade recorrente de conectividade: há pelo menos duas outras ocorrências nos últimos sete dias.'))
        if not diag:
            diag = Diagnostico(falha_id=falha.id)
        diag.causas = causes
        diag.estado = 'DISPONIVEL' if causes else 'EVIDENCIA_INSUFICIENTE'
        diag.descricao = ('Análise por regras a partir das medições e ocorrências relacionadas. As causas são hipóteses.'
                          if causes else 'Não há evidências suficientes para determinar uma causa provável.')
        diag.analisado_em = agora
        diag.evidencias = dict(dispositivo_id=device.id, status=device.status,
            amostras=[dict(id=m.id, coletada_em=iso(m.coletada_em), latencia_ms=m.latencia_ms, perda_pacotes_pct=m.perda_pacotes_pct, status=m.status) for m in samples],
            outros_dispositivos=[dict(id=p.id, status=p.status, ultima_coleta=iso(p.ultima_coleta)) for p in peers],
            falhas_relacionadas=[f.id for f in relacionadas], ocorrencias_anteriores=previous,
            janela_segundos=cfg['DIAGNOSTIC_WINDOW_SECONDS'],
            limites=dict(latencia_ms=cfg['LATENCY_LIMIT_MS'], perda_pacotes_pct=cfg['LOSS_LIMIT_PCT']))
        diag.salvar(commit=False)
        DiagnosticoRepository.limpar_recomendacoes(diag.id)
        rules = [c['regra'] for c in causes]
        if rules:
            for rec in DiagnosticoRepository.recomendacoes_das_regras(rules):
                DiagnosticoRecomendacao(diagnostico_id=diag.id, recomendacao_id=rec.id).salvar(commit=False)
        return diag
