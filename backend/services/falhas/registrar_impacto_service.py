from app import validation as v
from models import Impacto, utcnow
from repositories import Transacao
from services.comum.serializador import Serializador
from services.diagnosticos.atualizar_diagnosticos_service import AtualizarDiagnosticosService
from services.falhas.obter_falha_service import ObterFalhaService


class RegistrarImpactoService:
    """Affected users, direct costs and notes of an incident; severity is recalculated with them.
    usuarios_afetados empty/null: the device's people are used in the estimate."""

    CAMPOS = ('usuarios_afetados', 'observacao', 'custos_diretos')

    def executar(self, empresa_id, id, dados):
        falha = ObterFalhaService().buscar(empresa_id, id)  # 404 of another company before payload errors
        dados = v.json_object(dados, self.CAMPOS)
        impact = Impacto.buscar_um_por(falha_id=falha.id) or Impacto(falha_id=falha.id)
        if 'usuarios_afetados' in dados:
            impact.usuarios_afetados = v.optional(dados['usuarios_afetados'], v.integer, 'Usuários afetados')
            impact.origem = 'INFORMADO_PELO_USUARIO' if impact.usuarios_afetados is not None else 'NAO_INFORMADO'
        if 'custos_diretos' in dados:
            impact.custos_diretos = v.optional(dados['custos_diretos'], v.decimal_value, 'Custos diretos')
        if 'observacao' in dados:
            impact.observacao = v.string(dados.get('observacao') or '', 'Observação', 500, 0)
        impact.atualizado_em = utcnow()
        impact.salvar(commit=False)
        AtualizarDiagnosticosService().executar(empresa_id, falha_extra=falha)
        Transacao.confirmar()
        return Serializador.falha(falha, True)
