"""Repository layer: only the special queries (the plain CRUD lives in models.base.BaseModel)."""
from .transacao import Transacao
from .autenticacao_repository import AutenticacaoRepository
from .banco_repository import BancoRepository
from .coletor_repository import ColetorRepository
from .dashboard_repository import DashboardRepository
from .diagnostico_repository import DiagnosticoRepository
from .dispositivo_repository import DispositivoRepository
from .falha_repository import FalhaRepository
from .legado_repository import LegadoRepository
from .metrica_repository import MetricaRepository
from .ranking_custo_repository import RankingCustoRepository
from .relatorio_repository import RelatorioRepository
from .retencao_repository import RetencaoRepository
from .usuario_repository import UsuarioRepository

__all__ = ['Transacao', 'AutenticacaoRepository', 'BancoRepository', 'ColetorRepository', 'DashboardRepository',
           'DiagnosticoRepository', 'DispositivoRepository', 'FalhaRepository', 'LegadoRepository',
           'MetricaRepository', 'RankingCustoRepository', 'RelatorioRepository', 'RetencaoRepository',
           'UsuarioRepository']
