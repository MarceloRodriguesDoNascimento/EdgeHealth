# Controller do inventário de dispositivos
from services.dispositivos.arquivar_dispositivo_service import ArquivarDispositivoService
from services.dispositivos.atualizar_dispositivo_service import AtualizarDispositivoService
from services.dispositivos.cadastrar_dispositivo_service import CadastrarDispositivoService
from services.dispositivos.desarquivar_dispositivo_service import DesarquivarDispositivoService
from services.dispositivos.listar_dispositivos_service import ListarDispositivosService
from services.dispositivos.obter_dispositivo_service import ObterDispositivoService
from services.dispositivos.obter_impacto_padrao_service import ObterImpactoPadraoService
from services.dispositivos.solicitar_coleta_service import SolicitarColetaService
from .base_controller import BaseController


# Rotas de dispositivos
class DispositivoController(BaseController):
    CAMPOS = ['nome', 'ip', 'tipo', 'localizacao', 'coletor_id', 'usuarios_dependentes', 'perda_produtividade_pct',
              'receita_hora_dependente']

    # GET /api/dispositivos: lista o inventário
    def listar(self):
        return self.resposta(ListarDispositivosService().executar(self.empresa_id(), self.parametro('arquivados', '0')))

    # GET /api/dispositivos/<id>: um dispositivo
    def obter(self, id):
        return self.resposta(ObterDispositivoService().executar(self.empresa_id(), id))

    # POST /api/dispositivos: cadastra dispositivo
    def cadastrar(self):
        dados = self.payload(self.CAMPOS, ['nome', 'ip', 'tipo', 'localizacao'])
        return self.resposta(CadastrarDispositivoService().executar(self.empresa_id(), dados), 201)

    # PUT /api/dispositivos/<id>: edita dispositivo
    def atualizar(self, id):
        dados = self.payload(self.CAMPOS)
        return self.resposta(AtualizarDispositivoService().executar(self.empresa_id(), id, dados))

    # GET /api/dispositivos/impacto-padrao: sugestão de impacto pelo tipo
    def impacto_padrao(self):
        return self.resposta(ObterImpactoPadraoService().executar(self.empresa_id(), self.parametro('tipo', '')))

    # DELETE /api/dispositivos/<id>: arquiva (para de monitorar)
    def arquivar(self, id):
        ArquivarDispositivoService().executar(self.empresa_id(), id)
        return '', 204

    # POST /api/dispositivos/<id>/desarquivar: volta a monitorar
    def desarquivar(self, id):
        self.payload([])
        return self.resposta(DesarquivarDispositivoService().executar(self.empresa_id(), id))

    # POST /api/dispositivos/<id>/coletas: pede medição agora
    def solicitar_coleta(self, id):
        self.payload([])
        return self.resposta(SolicitarColetaService().executar(self.empresa_id(), id), 202)
