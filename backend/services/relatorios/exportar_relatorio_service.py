import io
import json
import zipfile
from werkzeug.exceptions import UnprocessableEntity
from app import validation as v
from models import Empresa, iso, utcnow
from repositories import FalhaRepository, RelatorioRepository
from services.comum.serializador import Serializador
from services.custos.calculadora_prejuizo import CalculadoraPrejuizo
from services.custos.calcular_prejuizo_total_service import CalcularPrejuizoTotalService
from services.dispositivos.obter_dispositivo_service import ObterDispositivoService
from .gerador_csv import GeradorCsv


class ExportarRelatorioService:
    """ZIP with devices, samples, incidents (with loss estimate) and diagnoses of a period
    (default: last 30 days). Returns (file, download name)."""

    LIMITE = 50000

    def _limitado(self, linhas):
        if len(linhas) > self.LIMITE:
            raise UnprocessableEntity('O período contém mais de 50.000 registros. Reduza o intervalo.')
        return linhas

    def executar(self, empresa_id, dispositivo_id=None, inicio=None, fim=None):
        start, end = v.period(inicio, fim, 30)
        device_id = v.query_int(dispositivo_id, 'dispositivo_id')
        if device_id: ObterDispositivoService().buscar(empresa_id, device_id)
        maximo = self.LIMITE + 1
        devices = self._limitado(RelatorioRepository.dispositivos(empresa_id, device_id, maximo))
        metrics = self._limitado(RelatorioRepository.metricas(empresa_id, device_id, start, end, maximo))
        # Include incidents overlapping the selected interval, not only newly opened ones.
        failures = self._limitado(RelatorioRepository.falhas_sobrepostas(empresa_id, device_id, start, end, maximo))
        diagnoses = self._limitado(RelatorioRepository.diagnosticos([f.id for f in failures], maximo))
        company = Empresa.buscar_por_id(empresa_id)
        costs = CalcularPrejuizoTotalService().executar(failures, company)
        estimates = costs.get('individual', {})
        failure_rows = [dict(Serializador.falha(f), prejuizo_estimado=estimates.get(f.id)) for f in failures]
        metadata = dict(empresa=company.nome_fantasia, cnpj=company.cnpj, inicio=iso(start), fim_exclusivo=iso(end),
                        gerado_em=iso(utcnow()), contagens=dict(dispositivos=len(devices), metricas=len(metrics), falhas=len(failures), diagnosticos=len(diagnoses)),
                        prejuizo_estimado=dict(total=costs.get('total'), aviso=CalculadoraPrejuizo.DISCLAIMER if costs['configurado'] else CalculadoraPrejuizo.NOT_CONFIGURED,
                            observacao='Total sem contar duas vezes as pessoas de falhas compartilhadas; a coluna prejuizo_estimado do falhas.csv é a estimativa individual de cada ocorrência (R$, ponto decimal). Falhas abertas: valor parcial até a geração do relatório.'),
                        falhas_por_dispositivo=FalhaRepository.ranking_dispositivos(empresa_id, start, end, limite=10, dispositivo_id=device_id),
                        observacao='Dispositivos: inventário atual, incluindo arquivados. Falhas: ocorrências sobrepostas ao período. Diagnósticos: última análise disponível das falhas selecionadas. Datas em UTC. Métricas: coletor_id vazio indica worker local; fora_de_ordem=True indica amostra atrasada, mantida no histórico sem alterar estado ou ocorrências.')
        csv = GeradorCsv.gerar
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('dispositivos.csv', csv([Serializador.dispositivo(d) for d in devices], ['id', 'nome', 'ip', 'tipo', 'localizacao', 'status', 'ultima_coleta', 'arquivado_em', 'coletor']))
            z.writestr('metricas.csv', csv([Serializador.metrica(m) for m in metrics], ['id', 'dispositivo_id', 'coletada_em', 'respondeu', 'latencia_ms', 'pacotes_enviados', 'pacotes_recebidos', 'perda_pacotes_pct', 'status', 'coletor_id', 'recebida_em', 'fora_de_ordem']))
            z.writestr('falhas.csv', csv(failure_rows, ['id', 'dispositivo_id', 'dispositivo', 'tipo', 'estado', 'inicio', 'fim', 'duracao_segundos', 'severidade', 'justificativa', 'impacto', 'encerramento', 'prejuizo_estimado']))
            z.writestr('diagnosticos.csv', csv([Serializador.diagnostico(d) for d in diagnoses], ['id', 'falha_id', 'estado', 'descricao', 'causas', 'evidencias', 'recomendacoes', 'analisado_em', 'versao_regras']))
            z.writestr('leia-me.json', json.dumps(metadata, ensure_ascii=False, indent=2))
        output.seek(0)
        return output, f'edgehealth-{utcnow().strftime("%Y%m%d-%H%M%S")}.zip'
