# Caso de uso: exportar registros em quarentena
import json
from models import RegistroLegado


# Exportação de legado
class ExportarLegadoService:
    # Grava os registros num arquivo
    def executar(self, destino):
        with open(destino, 'x', encoding='utf-8') as stream:
            for record in RegistroLegado.listar_todos():
                stream.write(json.dumps(dict(tabela=record.tabela, chave=record.chave_original,
                    empresa_id=record.empresa_id, resultado=record.resultado, motivo=record.motivo,
                    fonte_sha256=record.fonte_sha256, dados=record.dados), ensure_ascii=False) + '\n')
