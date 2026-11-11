# Caso de uso: montar os dados da Visão da rede
from datetime import timedelta
from app import validation as v
from models import iso, utcnow
from repositories import ColetorRepository, DashboardRepository, DispositivoRepository, FalhaRepository, MetricaRepository
from services.coletores.estado_coletor import EstadoColetor
from services.comum.serializador import Serializador
from services.custos.resumir_prejuizo_service import ResumirPrejuizoService
from services.dispositivos.obter_dispositivo_service import ObterDispositivoService


# Dados do painel
class GerarDashboardService:
    # Junta contagens, gráficos, falhas, coletores e prejuízo
    def executar(self, empresa_id, dispositivo_id=None, inicio=None, fim=None):
        now = utcnow()
        devices = DispositivoRepository.listar_ativos_da_empresa(empresa_id)
        status = DashboardRepository.contagem_por_status(empresa_id)
        severidades = DashboardRepository.contagem_por_severidade(empresa_id)
        counts = dict(total=len(devices), online=status.get('ONLINE', 0), instaveis=status.get('INSTAVEL', 0),
                      offline=status.get('OFFLINE', 0), sem_coleta=status.get('SEM_COLETA', 0),
                      falhas_abertas=sum(severidades.values()),
                      desatualizados=sum(Serializador.dispositivo(d)['desatualizado'] for d in devices))
        recent = FalhaRepository.recentes_da_empresa(empresa_id, limite=8)
        device_id = v.query_int(dispositivo_id, 'dispositivo_id')
        if device_id:
            ObterDispositivoService().buscar(empresa_id, device_id)
        elif devices:
            device_id = devices[0].id
        start, end = v.period(inicio, fim, 1)
        series, sample_total = [], 0
        if device_id:
            sample_total, rows = MetricaRepository.serie_do_dispositivo(device_id, start, end, limite=500)
            series = [Serializador.metrica(m) for m in reversed(rows)]
        collectors = [dict(id=c.id, nome=c.nome, estado=EstadoColetor.calcular(c, now), ultimo_contato=iso(c.ultimo_contato),
                           ultimo_erro=c.ultimo_erro) for c in ColetorRepository.ativos_da_empresa(empresa_id)]
        return dict(coletores=collectors, indicadores=counts, severidades=severidades,
                    falhas_recentes=[Serializador.falha(f) for f in recent], serie=series, serie_total=sample_total,
                    dispositivo_id=device_id, dispositivos=[Serializador.dispositivo(d) for d in devices], atualizado_em=iso(now),
                    custos=ResumirPrejuizoService().executar(empresa_id, now),
                    falhas_por_dispositivo=FalhaRepository.ranking_dispositivos(empresa_id, now - timedelta(days=30), None, limite=5))
