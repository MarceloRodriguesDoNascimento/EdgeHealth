from decimal import Decimal
from werkzeug.exceptions import BadRequest
from app import validation as v
from models import Empresa
from services.comum.serializador import Serializador


class ConfigurarCustosService:
    """Average salary, charges, hours per month, staff, working hours and time zone of the company."""

    def executar(self, empresa_id, dados):
        company = Empresa.buscar_por_id(empresa_id)
        if 'salario_medio' in dados: company.salario_medio = v.optional(dados['salario_medio'], v.decimal_value, 'Salário médio')
        if 'fator_encargos' in dados: company.fator_encargos = v.decimal_value(dados['fator_encargos'], 'Fator de encargos', Decimal('1'), Decimal('5'))
        if 'horas_mes' in dados: company.horas_mes = v.integer(dados['horas_mes'], 'Horas por mês', 1, 744)
        if 'total_funcionarios' in dados: company.total_funcionarios = v.optional(dados['total_funcionarios'], v.integer, 'Total de funcionários')
        if 'expediente' in dados:
            shift = dados['expediente']
            if not isinstance(shift, dict) or set(shift) - {'dias', 'inicio', 'fim'}:
                raise BadRequest('Expediente: informe dias, inicio e fim.')
            days = v.weekdays(shift.get('dias', [int(d) for d in company.expediente_dias]))
            start = v.clock(shift.get('inicio', company.expediente_inicio), 'Início do expediente')
            end = v.clock(shift.get('fim', company.expediente_fim), 'Fim do expediente')
            if start >= end: raise BadRequest('O fim do expediente deve ser depois do início.')
            company.expediente_dias, company.expediente_inicio, company.expediente_fim = days, start, end
        if 'fuso' in dados: company.fuso = v.timezone_name(dados['fuso'])
        company.atualizar(assistente_custos='CONCLUIDO')
        return Serializador.empresa(company)
