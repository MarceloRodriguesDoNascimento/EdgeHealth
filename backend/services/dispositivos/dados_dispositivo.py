from app import validation as v
from models import Empresa, utcnow
from services.coletores.validar_coletor_atribuivel_service import ValidarColetorAtribuivelService
from services.custos.categoria_dispositivo import CategoriaDispositivo


class DadosDispositivo:
    """Validates and applies the fields of the device form (shared by create and update)."""

    @classmethod
    def aplicar(cls, dispositivo, dados, empresa_id, criando):
        if 'nome' in dados: dispositivo.nome = v.string(dados['nome'], 'Nome', 100)
        if 'ip' in dados: dispositivo.ip = v.ip(dados['ip'])
        if 'tipo' in dados: dispositivo.tipo = v.string(dados['tipo'], 'Tipo', 50)
        if 'localizacao' in dados: dispositivo.localizacao = v.string(dados['localizacao'], 'Localização', 150)
        if 'coletor_id' in dados:
            collector_id = ValidarColetorAtribuivelService().executar(empresa_id, dados['coletor_id'])
            if collector_id != dispositivo.coletor_id:
                # A different measurement point: the next cycle collects from the new origin.
                dispositivo.coletor_id = collector_id
                dispositivo.erro_coleta = None
                dispositivo.proxima_coleta = utcnow()
        cls.impacto_negocio(dispositivo, dados, criando)

    @staticmethod
    def impacto_negocio(dispositivo, dados, criando):
        """People, productivity loss and direct revenue that depend on the device. A new device without
        these fields gets the defaults for its type (editable); explicit null clears a value."""
        if 'usuarios_dependentes' in dados:
            dispositivo.usuarios_dependentes = v.optional(dados['usuarios_dependentes'], v.integer, 'Pessoas que usam o aparelho')
        if 'perda_produtividade_pct' in dados:
            dispositivo.perda_produtividade_pct = v.optional(dados['perda_produtividade_pct'], v.integer, 'Perda de produtividade (%)', 0, 100)
        if 'receita_hora_dependente' in dados:
            dispositivo.receita_hora_dependente = v.optional(dados['receita_hora_dependente'], v.decimal_value, 'Receita por hora')
        if criando:
            default = CategoriaDispositivo.padroes(dispositivo.tipo, Empresa.buscar_por_id(dispositivo.empresa_id))
            if 'usuarios_dependentes' not in dados: dispositivo.usuarios_dependentes = default['usuarios']
            if 'perda_produtividade_pct' not in dados: dispositivo.perda_produtividade_pct = default['perda_pct']
