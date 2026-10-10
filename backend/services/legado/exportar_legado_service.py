import json
from models import RegistroLegado


class ExportarLegadoService:
    """Local operator-only export (JSON lines) of quarantined/converted source records."""

    def executar(self, destino):
        # Exclusive creation avoids overwriting an existing file or backup.
        with open(destino, 'x', encoding='utf-8') as stream:
            for record in RegistroLegado.listar_todos():
                stream.write(json.dumps(dict(tabela=record.tabela, chave=record.chave_original,
                    empresa_id=record.empresa_id, resultado=record.resultado, motivo=record.motivo,
                    fonte_sha256=record.fonte_sha256, dados=record.dados), ensure_ascii=False) + '\n')
