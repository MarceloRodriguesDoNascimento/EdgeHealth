from werkzeug.exceptions import NotFound
from repositories import DiagnosticoRepository
from services.comum.serializador import Serializador


class ObterDiagnosticoService:
    def executar(self, empresa_id, id):
        diag = DiagnosticoRepository.buscar_da_empresa(empresa_id, id)
        if not diag:
            raise NotFound('Diagnóstico não encontrado.')
        return Serializador.diagnostico(diag)
