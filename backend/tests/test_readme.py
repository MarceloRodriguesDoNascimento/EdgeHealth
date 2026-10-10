"""The README's "Funcionalidades Implementadas" table and routes table match the code:
every route, Service, Model/Repository and screen cited exists, so the README cannot fall out of date."""
import re
from pathlib import Path
import pytest
from controllers import rotas
from test_flowcharts import code_classes

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
README = ROOT / 'README.md'
CODE = re.compile(r'`([^`]+)`')


def section(title):
    text = README.read_text(encoding='utf-8')
    match = re.search(rf'^## {re.escape(title)}\n(.*?)(?=^## )', text, re.S | re.M)
    assert match, f'seção "{title}" ausente no README'
    return match.group(1)


def rows(title):
    """Body rows of the table in the section, as lists of cells."""
    return [[c.strip() for c in line.strip().strip('|').split('|')]
            for line in section(title).splitlines()
            if line.startswith('|') and not re.match(r'^\|\s*(-|Nº|Controller)', line)]


def normalize(rule):
    return re.sub(r'<[^>]*>', '<id>', rule)


def code_routes():
    acesso = {rotas.publica: 'público', rotas.sessao: 'técnico', rotas.sessao_sem_termos: 'técnico', rotas.admin: 'admin'}
    return {(metodo, '/api' + normalize(regra)): (acesso.get(nivel, 'coletor'), acao.__self__.__class__.__name__)
            for regra, metodo, _, nivel, acao in rotas.ROTAS}


FEATURES = rows('Funcionalidades Implementadas')


def test_at_least_20_numbered_features_and_4_main_ones():
    assert len(FEATURES) >= 20
    assert [int(r[0]) for r in FEATURES] == list(range(1, len(FEATURES) + 1)), 'numeração fora de ordem'
    assert sum('★' in r[1] for r in FEATURES) >= 4


@pytest.mark.parametrize('row', FEATURES, ids=lambda r: r[0])
def test_feature_route_service_layer_and_screen_exist(row):
    _, _, screen, route, services, layer = row
    routes, classes = code_routes(), code_classes()
    metodo, url = CODE.search(route).group(1).split(' ', 1)
    assert (metodo, url) in routes, f'rota inexistente: {metodo} {url}'
    assert (ROOT / CODE.search(screen).group(1)).is_file(), f'tela inexistente: {screen}'
    names = CODE.findall(services)
    assert names and all(n.endswith('Service') or n.startswith('Calculadora') for n in names)
    for ref in names + CODE.findall(layer):
        name, _, method = ref.partition('.')
        assert name in classes, f'classe inexistente: {name}'
        assert not method or method in classes[name], f'método inexistente: {ref}'


def test_routes_table_lists_every_route_with_controller_and_access():
    table = {(m, CODE.search(u).group(1)): (a, CODE.search(c).group(1)) for c, m, u, a in rows('Rotas da API')}
    assert table == code_routes()


def test_every_relative_link_points_to_an_existing_file():
    links = re.findall(r'\]\(([^)#\s]+)(?:#[^)]*)?\)', README.read_text(encoding='utf-8'))
    local = [link for link in links if not re.match(r'[a-z]+:', link)]
    assert len(local) >= 20
    assert not [link for link in local if not (ROOT / link).exists()]
