"""Special SQL queries of the repositories: data built in the test, exact expected results."""
import threading
from datetime import datetime, timedelta
import pytest
from app import db
from models import Coletor, Diagnostico, Dispositivo, Empresa, Falha, Metrica, Usuario
from repositories import (ColetorRepository, DashboardRepository, DiagnosticoRepository, DispositivoRepository,
                          FalhaRepository, MetricaRepository, RankingCustoRepository, RelatorioRepository,
                          UsuarioRepository)

T0 = datetime(2026, 10, 5, 12, 0)


def at(minutes):
    return T0 + timedelta(minutes=minutes)


def empresa(cnpj):
    return Empresa(nome_fantasia='Empresa ' + cnpj, cnpj=cnpj).salvar()


def dispositivo(e, nome, **campos):
    campos.setdefault('ip', '10.0.%d.%d' % (e.id, Dispositivo.query.count() + 1))
    return Dispositivo(empresa_id=e.id, nome=nome, tipo='Switch', localizacao='Sala', **campos).salvar()


def falha(d, inicio, fim=None, tipo='INSTABILIDADE', severidade='BAIXA'):
    return Falha(dispositivo_id=d.id, tipo=tipo, estado='ENCERRADA' if fim is not None else 'ABERTA',
                 inicio=at(inicio), fim=at(fim) if fim is not None else None,
                 ultima_observacao=at(fim if fim is not None else inicio), descricao='teste',
                 severidade=severidade, justificativa={}).salvar()


def metrica(d, minuto):
    return Metrica(dispositivo_id=d.id, coletada_em=at(minuto), respondeu=True, latencia_ms=1.0, pacotes_enviados=4,
                   pacotes_recebidos=4, perda_pacotes_pct=0.0, status='ONLINE').salvar()


def ids(rows):
    return [r.id for r in rows]


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


# --- FalhaRepository.historico ------------------------------------------------------------------------

def test_failure_history_filters_order_and_pagination(ctx):
    a, b = empresa('11222333000181'), empresa('11444777000161')
    d1, d2, outra = dispositivo(a, 'D1'), dispositivo(a, 'D2'), dispositivo(b, 'B1')
    f1 = falha(d1, 0, 10, severidade='BAIXA')
    f2 = falha(d1, 20, 30, severidade='ALTA')
    f3 = falha(d2, 40, severidade='MEDIA')
    f5 = falha(d2, 40, 45, severidade='BAIXA')  # same start as f3: highest id first
    f4 = falha(d1, 60, severidade='CRITICA')
    falha(outra, 50, severidade='ALTA')

    def hist(dispositivo_id=None, severidade=None, estado=None, inicio=None, fim=None, pagina=1, limite=50):
        rows, total = FalhaRepository.historico(a.id, dispositivo_id, severidade, estado, inicio, fim, pagina, limite)
        return ids(rows), total

    assert hist() == ([f4.id, f5.id, f3.id, f2.id, f1.id], 5)
    assert hist(dispositivo_id=d1.id) == ([f4.id, f2.id, f1.id], 3)
    assert hist(estado='ENCERRADA') == ([f5.id, f2.id, f1.id], 3)
    assert hist(estado='ABERTA') == ([f4.id, f3.id], 2)
    assert hist(severidade='ALTA') == ([f2.id], 1)  # the other company's ALTA is not listed
    assert hist(inicio=at(20), fim=at(60)) == ([f5.id, f3.id, f2.id], 3)  # [inicio, fim) on the start
    assert hist(dispositivo_id=d2.id, estado='ENCERRADA') == ([f5.id], 1)
    assert hist(dispositivo_id=outra.id) == ([], 0)
    assert hist(limite=2, pagina=1) == ([f4.id, f5.id], 5)
    assert hist(limite=2, pagina=2) == ([f3.id, f2.id], 5)
    assert hist(limite=2, pagina=3) == ([f1.id], 5)
    assert hist(limite=2, pagina=4) == ([], 5)


def test_metrics_by_period_and_pagination(ctx):
    a, b = empresa('11222333000181'), empresa('11444777000161')
    d1, d2 = dispositivo(a, 'D1'), dispositivo(a, 'D2')
    m = [metrica(d1, 0), metrica(d2, 5), metrica(d1, 10), metrica(d1, 20)]
    metrica(dispositivo(b, 'B1'), 10)
    assert MetricaRepository.por_periodo(a.id, None, at(0), at(20), 1, 50) == ([m[0], m[1], m[2]], 3)
    assert MetricaRepository.por_periodo(a.id, d1.id, None, None, 1, 50) == ([m[0], m[2], m[3]], 3)
    assert MetricaRepository.por_periodo(a.id, None, None, None, 2, 3) == ([m[3]], 4)
    total, newest_first = MetricaRepository.serie_do_dispositivo(d1.id, at(0), None, limite=2)
    assert (total, newest_first) == (3, [m[3], m[2]])
    assert MetricaRepository.recentes_na_janela(d1.id, at(5), at(20)) == [m[3], m[2]]  # both bounds inclusive


# --- Tenant isolation -------------------------------------------------------------------------------------

def test_every_company_scoped_lookup_ignores_other_companies(ctx):
    a, b = empresa('11222333000181'), empresa('11444777000161')
    da, db_ = dispositivo(a, 'A1', ip='10.0.0.1'), dispositivo(b, 'B1', ip='10.0.0.1')  # same IP: other company
    arquivado = dispositivo(a, 'A2', arquivado_em=T0)
    fa, fb = falha(da, 0), falha(db_, 0)
    ma, mb = metrica(da, 0), metrica(db_, 0)
    ca = Coletor(empresa_id=a.id, nome='Ca', token_hash='a' * 64, token_prefixo='ehc_a').salvar()
    cb = Coletor(empresa_id=b.id, nome='Cb', token_hash='b' * 64, token_prefixo='ehc_b').salvar()
    ua = Usuario(empresa_id=a.id, nome='Ua', email='ua@a.example', senha_hash='x').salvar()
    ub = Usuario(empresa_id=b.id, nome='Ub', email='ub@b.example', senha_hash='x').salvar()
    diag = dict(descricao='d', causas=[], evidencias={}, estado='DISPONIVEL')
    ga, gb = Diagnostico(falha_id=fa.id, **diag).salvar(), Diagnostico(falha_id=fb.id, **diag).salvar()

    pairs = [(DispositivoRepository, da, db_), (FalhaRepository, fa, fb), (MetricaRepository, ma, mb),
             (ColetorRepository, ca, cb), (UsuarioRepository, ua, ub), (DiagnosticoRepository, ga, gb)]
    for repository, own, foreign in pairs:
        assert repository.buscar_da_empresa(a.id, own.id) == own, repository.__name__
        assert repository.buscar_da_empresa(a.id, foreign.id) is None, repository.__name__
        assert repository.buscar_da_empresa(b.id, foreign.id) == foreign, repository.__name__
    assert DispositivoRepository.buscar_da_empresa(a.id, arquivado.id) == arquivado
    assert DispositivoRepository.buscar_da_empresa(a.id, arquivado.id, incluir_arquivados=False) is None
    assert DispositivoRepository.listar_da_empresa(a.id, incluir_arquivados=False) == [da]
    assert DispositivoRepository.listar_da_empresa(a.id, incluir_arquivados=True) == [da, arquivado]
    assert DispositivoRepository.listar_ativos_da_empresa(b.id) == [db_]
    assert ColetorRepository.listar_da_empresa(a.id) == [ca] and ColetorRepository.ativos_da_empresa(b.id) == [cb]
    assert UsuarioRepository.listar_da_empresa(a.id) == [ua]
    assert DispositivoRepository.existe_ip_ativo(a.id, '10.0.0.1') and not DispositivoRepository.existe_ip_ativo(a.id, '10.9.9.9')
    assert FalhaRepository.abertas_da_empresa(a.id) == [fa] and FalhaRepository.recentes_da_empresa(b.id) == [fb]
    assert RelatorioRepository.dispositivos(b.id, None, 10) == [db_]


# --- Report: overlapping periods --------------------------------------------------------------------------

def test_report_includes_incidents_overlapping_the_period(ctx):
    a, b = empresa('11222333000181'), empresa('11444777000161')
    d1, d2, d3, d4 = (dispositivo(a, n) for n in ('D1', 'D2', 'D3', 'D4'))
    inicio, fim = at(100), at(200)
    antes = falha(d1, 0, 50)            # ended before the period: out
    toca_inicio = falha(d1, 0, 100)     # ended exactly at the start: in (fim >= inicio)
    dentro = falha(d1, 150, 160)        # inside: in
    aberta_antes = falha(d3, 50)        # open, started before: in
    aberta_dentro = falha(d2, 190)      # open, started inside: in
    no_fim = falha(d1, 200, 210)        # starts exactly at the exclusive end: out
    depois = falha(d4, 300)             # starts after: out
    falha(dispositivo(b, 'B1'), 150)    # other company: out

    rows = RelatorioRepository.falhas_sobrepostas(a.id, None, inicio, fim, 100)
    assert ids(rows) == [toca_inicio.id, aberta_antes.id, dentro.id, aberta_dentro.id]
    assert ids(RelatorioRepository.falhas_sobrepostas(a.id, d1.id, inicio, fim, 100)) == [toca_inicio.id, dentro.id]
    assert ids(RelatorioRepository.falhas_sobrepostas(a.id, None, inicio, fim, 2)) == [toca_inicio.id, aberta_antes.id]
    assert len(RelatorioRepository.falhas_sobrepostas(a.id, None, None, None, 100)) == 7
    assert {antes.id, no_fim.id, depois.id}.isdisjoint(ids(rows))

    m = [metrica(d1, 99), metrica(d1, 100), metrica(d2, 199), metrica(d1, 200)]
    assert RelatorioRepository.metricas(a.id, None, inicio, fim, 100) == [m[1], m[2]]
    assert RelatorioRepository.metricas(a.id, d2.id, inicio, fim, 100) == [m[2]]
    diag = dict(descricao='d', causas=[], evidencias={}, estado='DISPONIVEL')
    g2, g1 = Diagnostico(falha_id=dentro.id, **diag).salvar(), Diagnostico(falha_id=toca_inicio.id, **diag).salvar()
    assert RelatorioRepository.diagnosticos([toca_inicio.id, dentro.id, antes.id], 100) == [g2, g1]


# --- Dashboard aggregations (SQL text) --------------------------------------------------------------------

def test_dashboard_counts_by_status_and_severity(ctx):
    a, b, vazia = empresa('11222333000181'), empresa('11444777000161'), empresa('45723174000110')
    estados = ['ONLINE', 'ONLINE', 'OFFLINE', 'INSTAVEL', None]
    devs = [dispositivo(a, f'D{i}', status=s) for i, s in enumerate(estados)]
    dispositivo(a, 'Arquivado', status='ONLINE', arquivado_em=T0)
    other = dispositivo(b, 'B1', status='ONLINE')
    falha(devs[0], 0, severidade='ALTA')
    falha(devs[1], 0, severidade='ALTA')
    falha(devs[2], 0, severidade='MEDIA')
    falha(devs[3], 0, 5, severidade='CRITICA')  # closed: not counted
    falha(other, 0, severidade='ALTA')
    assert DashboardRepository.contagem_por_status(a.id) == {'ONLINE': 2, 'OFFLINE': 1, 'INSTAVEL': 1, 'SEM_COLETA': 1}
    assert DashboardRepository.contagem_por_severidade(a.id) == {'ALTA': 2, 'MEDIA': 1}
    assert DashboardRepository.contagem_por_status(b.id) == {'ONLINE': 1}
    assert DashboardRepository.contagem_por_status(vazia.id) == {} == DashboardRepository.contagem_por_severidade(vazia.id)


# --- Rankings (SQL text) ----------------------------------------------------------------------------------

def test_cost_ranking_order_limit_and_ties(ctx):
    a = empresa('11222333000181')
    d = [dispositivo(a, f'D{i}') for i in range(7)]
    cents = {d[0].id: 500, d[1].id: 1500, d[2].id: 0, d[3].id: 1500, d[4].id: 100, d[5].id: 200, d[6].id: 300}
    expected = [d[3], d[1], d[0], d[6], d[5]]  # 1500 tie: highest id first; 0 excluded; 6th place cut
    assert RankingCustoRepository.top_dispositivos(cents, limite=5) == [(x.id, x.nome) for x in expected]
    assert RankingCustoRepository.top_dispositivos(cents, limite=2) == [(d[3].id, 'D3'), (d[1].id, 'D1')]
    assert RankingCustoRepository.top_dispositivos({d[2].id: 0}) == []
    assert RankingCustoRepository.top_dispositivos({}) == []


def test_failure_ranking_per_device_in_the_period(ctx):
    a, b = empresa('11222333000181'), empresa('11444777000161')
    d1, d2, d3, d4 = (dispositivo(a, n) for n in ('D1', 'D2', 'D3', 'D4'))
    falha(d2, 100, 110, tipo='INDISPONIBILIDADE')
    falha(d2, 120, 130)
    falha(d2, 150, tipo='INDISPONIBILIDADE')         # open
    falha(d1, 0, 100)                                # overlaps the start
    falha(d1, 140, 150)
    falha(d3, 50)                                     # open since before the period
    falha(d1, 0, 99)                                  # ended before: out
    falha(d4, 200, 210)                               # starts at the exclusive end: out
    falha(dispositivo(b, 'B1'), 120, 130)             # other company: out

    def row(d, falhas, abertas, indisponibilidades):
        return dict(dispositivo_id=d.id, nome=d.nome, falhas=falhas, abertas=abertas, indisponibilidades=indisponibilidades)

    ranking = FalhaRepository.ranking_dispositivos(a.id, at(100), at(200), limite=10)
    assert ranking == [row(d2, 3, 1, 2), row(d1, 2, 0, 0), row(d3, 1, 1, 0)]
    assert FalhaRepository.ranking_dispositivos(a.id, at(100), at(200), limite=2) == [row(d2, 3, 1, 2), row(d1, 2, 0, 0)]
    assert FalhaRepository.ranking_dispositivos(a.id, None, None, limite=10) == [
        row(d1, 3, 0, 0), row(d2, 3, 1, 2), row(d3, 1, 1, 0), row(d4, 1, 0, 0)]  # 3-3 tie: lowest id first
    assert FalhaRepository.ranking_dispositivos(a.id, at(100), at(200), 10, dispositivo_id=d1.id) == [row(d1, 2, 0, 0)]
    assert FalhaRepository.ranking_dispositivos(b.id, at(300), None) == []


# --- Collection scheduling and lease ----------------------------------------------------------------------

def test_devices_due_for_collection(ctx):
    a = empresa('11222333000181')
    c = Coletor(empresa_id=a.id, nome='C', token_hash='c' * 64, token_prefixo='ehc_c').salvar()
    devida = dispositivo(a, 'Devida', proxima_coleta=at(-10))
    mais_antiga = dispositivo(a, 'Mais antiga', proxima_coleta=at(-20))
    no_horario = dispositivo(a, 'No horário', proxima_coleta=at(0))
    dispositivo(a, 'Futura', proxima_coleta=at(10))
    dispositivo(a, 'Arquivada', proxima_coleta=at(-30), arquivado_em=T0)
    dispositivo(a, 'Do coletor', proxima_coleta=at(-30), coletor_id=c.id)
    assert DispositivoRepository.ids_devidos_para_coleta(at(0)) == [mais_antiga.id, devida.id, no_horario.id]
    assert DispositivoRepository.ids_devidos_para_coleta(at(0), limite=1) == [mais_antiga.id]


def test_lease_is_exclusive_and_expires(ctx):
    a, b = empresa('11222333000181'), empresa('11444777000161')
    c = Coletor(empresa_id=a.id, nome='C', token_hash='c' * 64, token_prefixo='ehc_c').salvar()
    local = dispositivo(a, 'Local', proxima_coleta=at(0))
    remoto = dispositivo(a, 'Remoto', proxima_coleta=at(0), coletor_id=c.id)
    reservar = DispositivoRepository.reservar_para_worker

    assert reservar(local.id, 'dono-1', at(2), at(0), devido_ate=at(0)) is True
    assert reservar(local.id, 'dono-2', at(2), at(1), devido_ate=at(1)) is False      # lease still valid
    DispositivoRepository.liberar_reserva(local.id, 'outro-dono', erro_coleta='x')   # not the owner: no effect
    db.session.commit(); db.session.refresh(local)
    assert (local.lease_owner, local.erro_coleta) == ('dono-1', None)
    assert reservar(local.id, 'dono-3', at(5), at(3), devido_ate=at(3)) is True       # expired lease is taken over
    DispositivoRepository.liberar_reserva(local.id, 'dono-3', erro_coleta='falha')
    db.session.commit(); db.session.refresh(local)
    assert (local.lease_owner, local.lease_until, local.erro_coleta) == (None, None, 'falha')
    assert reservar(local.id, 'dono-4', at(5), at(3), devido_ate=at(-1)) is False     # not due yet
    assert reservar(remoto.id, 'dono-5', at(5), at(3), devido_ate=at(3)) is False     # assigned to a collector
    assert DispositivoRepository.reservar_para_coletor(remoto.id, c.id, b.id, 'x', at(5), at(3)) is False
    assert DispositivoRepository.reservar_para_coletor(local.id, c.id, a.id, 'x', at(5), at(3)) is False
    assert DispositivoRepository.reservar_para_coletor(remoto.id, c.id, a.id, 'dono-6', at(5), at(3)) is True
    db.session.commit()


def test_only_one_concurrent_request_takes_the_lease(app):
    with app.app_context():
        device_id = dispositivo(empresa('11222333000181'), 'Disputado', proxima_coleta=at(0)).id
    start, results = threading.Barrier(8), []

    def compete(n):
        with app.app_context():
            start.wait()
            results.append(DispositivoRepository.reservar_para_worker(device_id, f'dono-{n}', at(2), at(0), at(0)))
            db.session.commit()
            db.session.remove()

    threads = [threading.Thread(target=compete, args=(n,)) for n in range(8)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert sorted(results) == [False] * 7 + [True]


# --- Shared outage group ----------------------------------------------------------------------------------

def test_shared_outage_group_inside_the_correlation_window(ctx):
    a, b = empresa('11222333000181'), empresa('11444777000161')
    d = [dispositivo(a, f'D{i}') for i in range(6)]
    janela = timedelta(seconds=300)
    alvo = falha(d[0], 0, 30, tipo='INDISPONIBILIDADE')
    no_limite_antes = falha(d[1], -5, 30, tipo='INDISPONIBILIDADE')   # exactly -300 s: in
    no_limite_depois = falha(d[2], 5, 30, tipo='INDISPONIBILIDADE')   # exactly +300 s: in
    fora = falha(d[3], 6, 30, tipo='INDISPONIBILIDADE')               # +360 s: out
    instabilidade = falha(d[4], 1, 30, tipo='INSTABILIDADE')          # not an outage: out
    falha(dispositivo(b, 'B1'), 0, 30, tipo='INDISPONIBILIDADE')       # other company: out
    db.session.commit()
    grupo = FalhaRepository.grupo_compartilhado(a.id, T0 - janela, T0 + janela)
    assert ids(grupo) == [alvo.id, no_limite_antes.id, no_limite_depois.id]
    assert {fora.id, instabilidade.id}.isdisjoint(ids(grupo))
