from flask import send_file
from services.relatorios.exportar_relatorio_service import ExportarRelatorioService
from .base_controller import BaseController


class RelatorioController(BaseController):
    def exportar(self):
        arquivo, nome = ExportarRelatorioService().executar(
            self.empresa_id(), dispositivo_id=self.parametro('dispositivo_id'),
            inicio=self.parametro('inicio'), fim=self.parametro('fim'))
        return send_file(arquivo, mimetype='application/zip', as_attachment=True, download_name=nome, max_age=0)
