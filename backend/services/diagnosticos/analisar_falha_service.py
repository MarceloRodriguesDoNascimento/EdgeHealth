# Caso de uso: diagnóstico lógico de uma falha
from datetime import timedelta
from flask import current_app
from models import Diagnostico, DiagnosticoRecomendacao, Dispositivo, iso
from repositories import DiagnosticoRepository, DispositivoRepository, FalhaRepository, MetricaRepository


# Diagnóstico por regras
class AnalisarFalhaService:
    # Aplica as regras e define causas e recomendações
    def executar(self, falha, relacionadas, agora):
        cfg = current_app.config
        device = Dispositivo.buscar_por_id(falha.dispositivo_id)
        window_start = agora - timedelta(seconds=cfg['DIAGNOSTIC_WINDOW_SECONDS'])
        samples = MetricaRepository.recentes_na_janela(device.id, window_start, agora, limite=20)
        diag = Diagnostico.buscar_um_por(falha_id=falha.id)
        if not samples and diag:
            return diag
        latest = samples[0] if samples else None
        recovering = (latest and latest.status == 'INSTAVEL' and latest.respondeu
                      and latest.latencia_ms is not None and latest.latencia_ms < cfg['LATENCY_LIMIT_MS']
                      and latest.perda_pacotes_pct < cfg['LOSS_LIMIT_PCT'])
        if recovering and diag:
            return diag
        peers = DispositivoRepository.pares_com_coleta_na_janela(device.empresa_id, device.id, window_start, agora)
        previous = FalhaRepository.ids_anteriores_do_dispositivo(device.id, falha.id, agora - timedelta(days=7), agora, limite=20)
        causes = []
        if latest and latest.status == 'OFFLINE' and any(p.status == 'ONLINE' for p in peers):
            causes.append(dict(regra='LOCALIZADA', descricao='Possível problema localizado no dispositivo, alimentação, cabo, porta ou política de resposta ICMP; outros dispositivos da empresa responderam.'))
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
