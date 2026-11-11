# Controller da tela Visão da rede
from services.dashboard.gerar_dashboard_service import GerarDashboardService
from .base_controller import BaseController


# Rota do painel principal
class DashboardController(BaseController):
    # GET /api/dashboard: dados do painel com os filtros da URL
    def obter(self):
        return self.resposta(GerarDashboardService().executar(
            self.empresa_id(), dispositivo_id=self.parametro('dispositivo_id'),
            inicio=self.parametro('inicio'), fim=self.parametro('fim')))
