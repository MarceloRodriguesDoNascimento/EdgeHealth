# Caso de uso: achar as falhas da mesma queda compartilhada
from datetime import timedelta
from flask import current_app
from models import Diagnostico, Dispositivo
from repositories import FalhaRepository


# Grupo compartilhado
class IdentificarGrupoCompartilhadoService:
    # Devolve as falhas do mesmo grupo
    def executar(self, falha):
        diag = Diagnostico.buscar_um_por(falha_id=falha.id)
        if not diag or 'COMPARTILHADA' not in {c.get('regra') for c in diag.causas or []}:
            return [falha]
        window = timedelta(seconds=current_app.config['DIAGNOSTIC_WINDOW_SECONDS'])
        empresa_id = Dispositivo.buscar_por_id(falha.dispositivo_id).empresa_id
        members = FalhaRepository.grupo_compartilhado(empresa_id, falha.inicio - window, falha.inicio + window)
        return members if falha in members and len(members) > 1 else [falha]
