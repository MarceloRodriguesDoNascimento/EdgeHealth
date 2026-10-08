"""Layered architecture rules: Controller -> Service -> Model/Repository -> database."""
import ast
from pathlib import Path
import models
from models.base import BaseModel

BACKEND = Path(__file__).resolve().parents[1]


def sources(layer):
    files = sorted((BACKEND / layer).rglob('*.py'))
    assert files, f'nenhum arquivo encontrado em {layer}/'
    return [(path.relative_to(BACKEND).as_posix(), ast.parse(path.read_text(encoding='utf-8'))) for path in files]


def imported_names(tree):
    """(module, name) of every import; name is None for `import module`."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, None
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                yield node.module, alias.name


def database_access(path, tree):
    found = []
    for module, name in imported_names(tree):
        if module.split('.')[0] in ('sqlalchemy', 'flask_sqlalchemy'):
            found.append(f'{path}: import de {module}')
        if module == 'app.extensions' or (module == 'app' and name in ('db', 'extensions')):
            found.append(f'{path}: import de db ({module})')
    return found


def test_controllers_do_not_import_sqlalchemy_or_db():
    problems = [p for path, tree in sources('controllers') for p in database_access(path, tree)]
    assert not problems, problems


def test_services_do_not_use_flask_request_or_g():
    problems = []
    for path, tree in sources('services'):
        problems += [f'{path}: from flask import {name}' for module, name in imported_names(tree)
                     if module == 'flask' and name in ('request', 'g')]
        problems += [f'{path}: flask.{node.attr}' for node in ast.walk(tree)
                     if isinstance(node, ast.Attribute) and node.attr in ('request', 'g')
                     and isinstance(node.value, ast.Name) and node.value.id == 'flask']
    assert not problems, problems


def test_services_reach_the_database_only_through_models_and_repositories():
    problems = [p for path, tree in sources('services') for p in database_access(path, tree)]
    assert not problems, problems


def test_base_model_has_the_five_crud_operations():
    missing = [op for op in ('salvar', 'atualizar', 'deletar', 'listar_todos', 'buscar_por_id')
               if not callable(getattr(BaseModel, op, None))]
    assert not missing, f'BaseModel não define: {missing}'
    entities = [getattr(models, name) for name in models.__all__ if hasattr(getattr(models, name), '__tablename__')]
    assert len(entities) == 13 and all(issubclass(entity, BaseModel) for entity in entities)
