from decimal import Decimal
from app import validation as v
from models import Empresa
from services.custos.calculadora_prejuizo import CalculadoraPrejuizo


class SimularCustoHoraService:
    """Preview of the cost per hour while the administrator types, without saving: the formula lives only here.
    Empty charges factor or hours per month fall back to the defaults of the Empresa model."""

    def executar(self, dados):
        salary = v.optional(dados.get('salario_medio'), v.decimal_value, 'Salário médio')
        factor = dados.get('fator_encargos')
        factor = Empresa.FATOR_ENCARGOS_PADRAO if factor in (None, '') else v.decimal_value(
            factor, 'Fator de encargos', Decimal('1'), Decimal('5'))
        hours = dados.get('horas_mes')
        hours = Empresa.HORAS_MES_PADRAO if hours in (None, '') else v.integer(hours, 'Horas por mês', 1, 744)
        hourly = CalculadoraPrejuizo.custo_hora_de(salary, factor, hours)
        return dict(custo_hora=CalculadoraPrejuizo.dinheiro(hourly), salario_medio=CalculadoraPrejuizo.dinheiro(salary),
                    fator_encargos=str(factor), horas_mes=hours)
