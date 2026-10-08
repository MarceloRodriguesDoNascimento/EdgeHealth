from models import Dispositivo
from services.comum.serializador import Serializador
from .dados_dispositivo import DadosDispositivo


class CadastrarDispositivoService:
    def executar(self, empresa_id, dados):
        device = Dispositivo(empresa_id=empresa_id)
        DadosDispositivo.aplicar(device, dados, empresa_id, criando=True)
        device.salvar()
        return Serializador.dispositivo(device)
