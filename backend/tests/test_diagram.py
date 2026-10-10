"""The class diagram (docs/diagrama-classes.md) must match the real Models."""
import inspect
import re
import sys
from pathlib import Path
import models
from models.base import BaseModel

DOCS = Path(__file__).resolve().parents[2] / 'docs'


def mermaid():
    text = (DOCS / 'diagrama-classes.md').read_text(encoding='utf-8')
    return re.search(r'```mermaid\n(.*?)```', text, re.S).group(1)


def diagram_classes():
    """{class: {attribute names}} read from the class blocks."""
    found = {}
    for name, body in re.findall(r'^\s*class (\w+) \{\n(.*?)^\s*\}', mermaid(), re.M | re.S):
        found[name] = {m.group(1) for m in re.finditer(r'^\s*\+\w+ (\w+)(?: PK)?(?: FK)?\s*$', body, re.M)}
    return found


def diagram_relations():
    return {frozenset(pair) for pair in re.findall(r'^\s*(\w+) "[^"]+" (?:\*--|o--|-->) "[^"]+" (\w+) :', mermaid(), re.M)}


def entities():
    return [c for c in (getattr(models, n) for n in models.__all__)
            if inspect.isclass(c) and issubclass(c, BaseModel) and c is not BaseModel]


def test_every_entity_and_column_is_in_the_diagram_and_nothing_else():
    classes = diagram_classes()
    expected = {c.__name__: {col.name for col in c.__table__.columns} for c in entities()}
    assert set(classes) - {'BaseModel'} == set(expected), 'classes do diagrama diferentes dos models'
    for name, columns in expected.items():
        assert classes[name] == columns, f'{name}: faltando {columns - classes[name]}, sobrando {classes[name] - columns}'


def test_base_model_crud_and_inheritance():
    text = mermaid()
    for operation in ('salvar', 'atualizar', 'deletar', 'listar_todos', 'buscar_por_id'):
        assert re.search(rf'class BaseModel \{{[^}}]*\+{operation}\(', text), operation
    for c in entities():
        assert f'BaseModel <|-- {c.__name__}' in text, c.__name__


def test_every_foreign_key_has_a_relationship():
    by_table = {c.__tablename__: c.__name__ for c in entities()}
    relations = diagram_relations()
    for c in entities():
        for column in c.__table__.columns:
            for fk in column.foreign_keys:
                pair = frozenset((c.__name__, by_table[fk.column.table.name]))
                assert pair in relations, f'{c.__name__}.{column.name} sem relacionamento no diagrama'
    assert len(relations) == len({frozenset(p) for p in relations})


def test_committed_diagram_is_the_generated_one():
    sys.path.insert(0, str(DOCS))
    try:
        import gerar_diagrama_classes as gerador
    finally:
        sys.path.remove(str(DOCS))
    assert (DOCS / 'diagrama-classes.md').read_text(encoding='utf-8') == gerador.documento(), \
        'rode docs/gerar_diagrama_classes.py para atualizar o diagrama'
