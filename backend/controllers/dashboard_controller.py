from services.dashboard.gerar_dashboard_service import GerarDashboardService
from .base_controller import BaseController


class DashboardController(BaseController):
    def obter(self):
        return self.resposta(GerarDashboardService().executar(
            self.empresa_id(), dispositivo_id=self.parametro('dispositivo_id'),
            inicio=self.parametro('inicio'), fim=self.parametro('fim')))
