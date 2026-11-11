# Calcula o prejuízo estimado de uma falha em R$
from decimal import Decimal, ROUND_HALF_UP
from models import Dispositivo, Empresa, Impacto, utcnow
from .categoria_dispositivo import CategoriaDispositivo
from .expediente import Expediente


# Cálculos de custo e prejuízo
class CalculadoraPrejuizo:
    CENT = Decimal('0.01')
    HOUR = Decimal(3600)
    NOT_CONFIGURED = 'Configure os custos da empresa para ver a estimativa.'
    DISCLAIMER = 'Estimativa baseada nos custos informados pela empresa.'

    # Arredonda para centavos
    @classmethod
    def dinheiro(cls, value):
        return None if value is None else str(Decimal(value).quantize(cls.CENT, rounding=ROUND_HALF_UP))

    # Fórmula do custo por hora
    @staticmethod
    def custo_hora_de(salario, fator, horas):
        if salario is None or not horas:
            return None
        return salario * fator / Decimal(horas)

    # Custo por hora da empresa
    @classmethod
    def custo_hora(cls, empresa):
        return cls.custo_hora_de(empresa.salario_medio, empresa.fator_encargos, empresa.horas_mes)

    # Resumo dos custos para a tela Empresa
    @classmethod
    def resumo_empresa(cls, empresa):
        hourly = cls.custo_hora(empresa)
        return dict(configurado=hourly is not None, salario_medio=cls.dinheiro(empresa.salario_medio),
                    fator_encargos=str(empresa.fator_encargos), horas_mes=empresa.horas_mes,
                    total_funcionarios=empresa.total_funcionarios,
                    expediente=dict(dias=[int(d) for d in empresa.expediente_dias], inicio=empresa.expediente_inicio,
                                    fim=empresa.expediente_fim),
                    fuso=empresa.fuso, custo_hora=cls.dinheiro(hourly), assistente=empresa.assistente_custos)

    # Pessoas, % de perda, receita e custos usados na falha
    @staticmethod
    def parametros(falha, empresa):
        device = Dispositivo.buscar_por_id(falha.dispositivo_id)
        impact = Impacto.buscar_um_por(falha_id=falha.id)
        default = CategoriaDispositivo.padroes(device.tipo, empresa)
        if impact and impact.usuarios_afetados is not None:
            users, users_source = impact.usuarios_afetados, 'informado na ocorrência'
        elif device.usuarios_dependentes is not None:
            users, users_source = device.usuarios_dependentes, 'cadastro do dispositivo'
        else:
            users, users_source = default['usuarios'] or 0, f'padrão para {default["rotulo"]}'
        loss = device.perda_produtividade_pct if device.perda_produtividade_pct is not None else default['perda_pct']
        return dict(device=device, users=users, users_source=users_source, loss=Decimal(loss),
                    revenue=device.receita_hora_dependente or Decimal(0),
                    direct=(impact.custos_diretos if impact and impact.custos_diretos is not None else Decimal(0)))

    # Formata valor em reais
    @classmethod
    def brl(cls, value):
        q = Decimal(value).quantize(cls.CENT, rounding=ROUND_HALF_UP)
        whole, cents = f'{q:,.2f}'.split('.')
        return 'R$ ' + whole.replace(',', '.') + ',' + cents

    # Formata número com vírgula
    @staticmethod
    def num(value, places=1):
        return f'{Decimal(value):.{places}f}'.replace('.', ',')

    # Prejuízo de uma falha
    @classmethod
    def estimar(cls, falha, empresa=None, agora=None):
        empresa = empresa or Empresa.buscar_por_id(Dispositivo.buscar_por_id(falha.dispositivo_id).empresa_id)
        hourly = cls.custo_hora(empresa)
        if hourly is None:
            return dict(configurado=False, mensagem=cls.NOT_CONFIGURED)
        agora = agora or utcnow()
        end = falha.fim or agora
        p = cls.parametros(falha, empresa)
        hours = Expediente.segundos_uteis([(falha.inicio, end)], empresa) / cls.HOUR
        productivity = hours * p['users'] * hourly * p['loss'] / 100
        revenue = hours * p['revenue']
        total = (productivity + revenue + p['direct']).quantize(cls.CENT, rounding=ROUND_HALF_UP)
        parts = [f'{p["users"]} pessoa{"" if p["users"] == 1 else "s"} × {cls.brl(hourly)}/h × {p["loss"]:.0f}% × {cls.num(hours)} h de expediente']
        if p['revenue']:
            parts.append(f'{cls.brl(p["revenue"])}/h de receita × {cls.num(hours)} h')
        if p['direct']:
            parts.append(f'{cls.brl(p["direct"])} de custos diretos')
        return dict(configurado=True, valor=cls.dinheiro(total), em_andamento=falha.estado == 'ABERTA',
                    conta=' + '.join(parts), aviso=cls.DISCLAIMER,
                    detalhe=dict(formula='horas de expediente × (pessoas × custo/hora × perda% + receita/hora) + custos diretos',
                                 horas_expediente=str(hours.quantize(Decimal('0.01'))), pessoas=p['users'],
                                 origem_pessoas=p['users_source'], custo_hora=cls.dinheiro(hourly), perda_pct=int(p['loss']),
                                 receita_hora=cls.dinheiro(p['revenue']), custos_diretos=cls.dinheiro(p['direct']),
                                 produtividade=cls.dinheiro(productivity), receita=cls.dinheiro(revenue),
                                 calculado_ate=end.isoformat(timespec='seconds') + 'Z'))

    # Prejuízo de uma queda compartilhada, sem contar pessoas duas vezes
    @classmethod
    def estimar_grupo(cls, membros, empresa, agora=None):
        hourly = cls.custo_hora(empresa)
        agora = agora or utcnow()
        params = {f.id: cls.parametros(f, empresa) for f in membros}
        largest = max(membros, key=lambda f: (params[f.id]['users'] * params[f.id]['loss'], params[f.id]['users']))
        lp = params[largest.id]
        hours = Expediente.segundos_uteis([(f.inicio, f.fim or agora) for f in membros], empresa) / cls.HOUR
        productivity = hours * lp['users'] * hourly * lp['loss'] / 100
        revenue = sum((Expediente.segundos_uteis([(f.inicio, f.fim or agora)], empresa) / cls.HOUR * params[f.id]['revenue'] for f in membros), Decimal(0))
        direct = sum((params[f.id]['direct'] for f in membros), Decimal(0))
        total = (productivity + revenue + direct).quantize(cls.CENT, rounding=ROUND_HALF_UP)
        summed = sum(params[f.id]['users'] for f in membros)
        return dict(valor=cls.dinheiro(total), falhas=[f.id for f in membros], dispositivos=len({f.dispositivo_id for f in membros}),
                    pessoas_consideradas=lp['users'], pessoas_somadas=summed, horas_expediente=str(hours.quantize(cls.CENT)),
                    explicacao=(f'Falha compartilhada por {len(membros)} dispositivos na mesma janela. No total do grupo '
                                f'contamos o maior grupo de pessoas afetadas ({lp["users"]}), e não a soma ({summed}), '
                                'para não contar as mesmas pessoas duas vezes. Receitas e custos diretos de cada '
                                'dispositivo são somados.'))
