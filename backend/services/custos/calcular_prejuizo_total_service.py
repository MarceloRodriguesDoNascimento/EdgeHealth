from decimal import Decimal
from models import utcnow
from repositories import RankingCustoRepository
from .calculadora_prejuizo import CalculadoraPrejuizo
from .identificar_grupo_compartilhado_service import IdentificarGrupoCompartilhadoService


class CalcularPrejuizoTotalService:
    """Company total without double counting shared outages, and the top 5 devices by loss."""

    def executar(self, falhas, empresa, agora=None):
        calc = CalculadoraPrejuizo
        if calc.custo_hora(empresa) is None:
            return dict(configurado=False, mensagem=calc.NOT_CONFIGURED)
        agora = agora or utcnow()
        grupos = IdentificarGrupoCompartilhadoService()
        individual = {f.id: Decimal(calc.estimar(f, empresa, agora)['valor']) for f in falhas}
        seen, total = set(), Decimal(0)
        for f in falhas:
            if f.id in seen:
                continue
            members = [m for m in grupos.executar(f) if m.id in individual]
            if len(members) > 1:
                total += Decimal(calc.estimar_grupo(members, empresa, agora)['valor'])
                seen.update(m.id for m in members)
            else:
                total += individual[f.id]
                seen.add(f.id)
        by_device = {}
        for f in falhas:
            by_device[f.dispositivo_id] = by_device.get(f.dispositivo_id, Decimal(0)) + individual[f.id]
        # Values are whole cents (sums of amounts rounded to cents): exact integers for the SQL ranking.
        top = RankingCustoRepository.top_dispositivos({k: int(v * 100) for k, v in by_device.items()}, limite=5)
        return dict(configurado=True, total=calc.dinheiro(total), falhas=len(falhas), em_andamento=any(f.estado == 'ABERTA' for f in falhas),
                    individual={k: calc.dinheiro(v) for k, v in individual.items()},
                    top_dispositivos=[dict(dispositivo_id=k, nome=nome, valor=calc.dinheiro(by_device[k])) for k, nome in top],
                    aviso=calc.DISCLAIMER)
