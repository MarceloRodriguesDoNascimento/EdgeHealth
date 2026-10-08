from flask import current_app
from models import Impacto, iso


class CalcularSeveridadeService:
    """Severity from unavailability, duration, correlated devices and informed affected users."""

    def executar(self, falha, dispositivos_relacionados, agora):
        cfg = current_app.config
        impact = Impacto.buscar_um_por(falha_id=falha.id)
        minutes = max(0, ((falha.fim or agora) - falha.inicio).total_seconds() / 60)
        users = impact.usuarios_afetados if impact else None
        level, reasons = 0, []
        if falha.tipo == 'INDISPONIBILIDADE':
            level = 1
            reasons.append('Dispositivo sem resposta após confirmação de indisponibilidade.')
        for threshold, target in [(cfg['SEVERITY_MEDIUM_MINUTES'], 1), (cfg['SEVERITY_HIGH_MINUTES'], 2), (cfg['SEVERITY_CRITICAL_MINUTES'], 3)]:
            if minutes >= threshold:
                level = max(level, target)
                reasons.append(f'Duração de pelo menos {threshold} minutos.')
        if dispositivos_relacionados >= cfg['SEVERITY_GROUP_SIZE']:
            level = max(level, 2)
            reasons.append(f'{dispositivos_relacionados} dispositivos com ocorrências temporalmente relacionadas.')
        if users is not None:
            if users >= cfg['SEVERITY_HIGH_USERS']:
                level = max(level, 2)
                reasons.append(f'Estimativa informada de {users} usuários afetados.')
            if users >= cfg['SEVERITY_CRITICAL_USERS']:
                level = 3
        if not reasons:
            reasons.append('Instabilidade observada, abaixo dos limites de escalonamento.')
        falha.severidade = ['BAIXA', 'MEDIA', 'ALTA', 'CRITICA'][level]
        falha.justificativa = dict(motivos=reasons, duracao_minutos=round(minutes, 2),
                                   dispositivos_afetados=dispositivos_relacionados, usuarios_afetados=users,
                                   calculada_em=iso(agora), versao_regras='1.0')
