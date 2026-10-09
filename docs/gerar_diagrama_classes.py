"""Generates docs/diagrama-classes.md from the real Models (backend/models).

Classes, attributes, types and domain methods come from the code; only the nature of each
relationship (composition, aggregation or association) is a modelling decision, listed in
RELACOES below. The script refuses to run if a ForeignKey has no decision.

    backend\\.venv\\Scripts\\python.exe docs\\gerar_diagrama_classes.py
(backend/tests/test_diagram.py fails if the committed diagram differs from the Models.)
"""
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

import models  # noqa: E402
from models.base import BaseModel  # noqa: E402

# (table, column) -> (parent class, child class, kind, parent cardinality, child cardinality, label, reason)
# kind: '*--' composition (the child has no life without the parent), 'o--' aggregation (the part
# exists on its own), '-->' association (only a reference).
RELACOES = {
    ('usuarios', 'empresa_id'): ('Empresa', 'Usuario', '*--', '1', '0..*', 'possui',
                                 'conta de usuário só existe dentro de uma empresa'),
    ('auth_sessions', 'usuario_id'): ('Usuario', 'AuthSession', '*--', '1', '0..*', 'abre',
                                      'sessão é apagada junto com o usuário (ON DELETE CASCADE)'),
    ('coletores', 'empresa_id'): ('Empresa', 'Coletor', '*--', '1', '0..*', 'cadastra',
                                  'coletor pertence a uma única empresa'),
    ('dispositivos', 'empresa_id'): ('Empresa', 'Dispositivo', '*--', '1', '0..*', 'monitora',
                                     'inventário de uma única empresa'),
    ('dispositivos', 'coletor_id'): ('Coletor', 'Dispositivo', 'o--', '0..1', '0..*', 'mede',
                                     'o dispositivo existe sem coletor (worker local) e pode trocar de coletor'),
    ('metricas', 'dispositivo_id'): ('Dispositivo', 'Metrica', '*--', '1', '0..*', 'gera',
                                     'amostra só faz sentido para o dispositivo medido'),
    ('metricas', 'coletor_id'): ('Coletor', 'Metrica', '-->', '0..1', '0..*', 'enviou',
                                 'apenas registra a origem da amostra (vazio = worker local)'),
    ('falhas', 'dispositivo_id'): ('Dispositivo', 'Falha', '*--', '1', '0..*', 'apresenta',
                                   'ocorrência é sempre de um dispositivo'),
    ('impactos', 'falha_id'): ('Falha', 'Impacto', '*--', '1', '1', 'tem',
                               'criado junto com a falha (usuários afetados e custos diretos)'),
    ('diagnosticos', 'falha_id'): ('Falha', 'Diagnostico', '*--', '1', '0..1', 'explicada por',
                                   'análise por regras da própria falha'),
    ('diagnostico_recomendacoes', 'diagnostico_id'): ('Diagnostico', 'DiagnosticoRecomendacao', '*--', '1', '0..*', 'indica',
                                                      'vínculo apagado junto com o diagnóstico (CASCADE)'),
    ('diagnostico_recomendacoes', 'recomendacao_id'): ('Recomendacao', 'DiagnosticoRecomendacao', 'o--', '1', '0..*', 'aplicada em',
                                                       'o catálogo de recomendações existe sem diagnósticos'),
    ('registros_legados', 'empresa_id'): ('Empresa', 'RegistroLegado', '-->', '0..1', '0..*', 'origem',
                                          'registro importado do protótipo; a empresa pode não ter sido reconhecida'),
}

TIPOS = {'Integer': 'int', 'String': 'str', 'Text': 'str', 'DateTime': 'datetime', 'Float': 'float',
         'Boolean': 'bool', 'JSON': 'json', 'DecimalText': 'Decimal'}
CRUD = ['salvar(commit) BaseModel', 'atualizar(commit, campos) BaseModel', 'deletar(commit) None',
        'listar_todos()$ list', 'buscar_por_id(id)$ BaseModel', 'buscar_um_por(filtros)$ BaseModel']


def entidades():
    found = [getattr(models, n) for n in models.__all__]
    return [c for c in found if inspect.isclass(c) and issubclass(c, BaseModel) and c is not BaseModel]


def metodos_de_dominio(cls):
    own = [n for n, v in vars(cls).items() if inspect.isfunction(v) and not n.startswith('_')]
    return [f'+{n}({", ".join(p for p in inspect.signature(getattr(cls, n)).parameters if p != "self")})' for n in own]


def gerar():
    classes = entidades()
    por_tabela = {c.__tablename__: c.__name__ for c in classes}
    fks = {(c.__tablename__, col.name) for c in classes for col in c.__table__.columns for _ in col.foreign_keys}
    faltando = sorted(fks - set(RELACOES))
    if faltando:
        raise SystemExit(f'Chave estrangeira sem decisão de relacionamento em RELACOES: {faltando}')
    linhas = ['classDiagram', '    direction TB', '    class BaseModel {', '        <<abstract>>']
    linhas += [f'        +{m}' for m in CRUD] + ['    }']
    for c in classes:
        linhas.append(f'    class {c.__name__} {{')
        for col in c.__table__.columns:
            tipo = TIPOS.get(type(col.type).__name__, type(col.type).__name__)
            chave = (' PK' if col.primary_key else '') + (' FK' if col.foreign_keys else '')
            linhas.append(f'        +{tipo} {col.name}{chave}')
        linhas += [f'        {m}' for m in metodos_de_dominio(c)]
        linhas.append('    }')
    for c in classes:
        linhas.append(f'    BaseModel <|-- {c.__name__}')
    for (tabela, coluna), (pai, filho, tipo, cp, cf, rotulo, _) in sorted(RELACOES.items()):
        assert por_tabela[tabela] == filho, (tabela, filho)
        linhas.append(f'    {pai} "{cp}" {tipo} "{cf}" {filho} : {rotulo}')
    return '\n'.join(linhas), classes


def documento():
    diagrama, classes = gerar()
    legenda = '\n'.join(f'| {pai} → {filho} | `{tabela}.{coluna}` | {"Composição" if tipo == "*--" else "Agregação" if tipo == "o--" else "Associação"} | {cp} : {cf} | {razao} |'
                        for (tabela, coluna), (pai, filho, tipo, cp, cf, _, razao) in sorted(RELACOES.items()))
    return f"""# Diagrama de classes do domínio

Gerado a partir dos Models reais em [`backend/models/`](../backend/models) por
[`docs/gerar_diagrama_classes.py`](gerar_diagrama_classes.py); `backend/tests/test_diagram.py` falha se o
diagrama ficar diferente do código. Imagem para slides: [`docs/img/diagrama-classes.svg`](img/diagrama-classes.svg)
([PNG](img/diagrama-classes.png)).

- **{len(classes)} entidades**, todas herdando de `BaseModel` (`db.Model` do Flask-SQLAlchemy), que concentra o CRUD
  exigido pela disciplina: `salvar()`, `atualizar()`, `deletar()`, `listar_todos()` e `buscar_por_id()`
  (`$` = método de classe). Consultas especiais ficam na camada Repository.
- Atributos com o tipo do código (`Decimal` = valor monetário exato, `json` = coluna JSON). `PK` = chave primária,
  `FK` = chave estrangeira.

```mermaid
{diagrama}
```

## Relacionamentos

Cardinalidade lida das chaves estrangeiras: `1` quando a FK é obrigatória, `0..1` quando aceita vazio, e `1 : 1` quando
a FK é única (`Impacto` e `Diagnostico` de uma `Falha`).

| Relação | Chave estrangeira | Tipo | Cardinalidade | Por quê |
|---|---|---|---|---|
{legenda}

**Legenda:** composição (losango cheio, `*--`) = a parte não existe sem o todo; agregação (losango vazio, `o--`) = a parte
existe sozinha e só é agrupada; associação (`-->`) = apenas uma referência. `Diagnostico` × `Recomendacao` é
muitos-para-muitos por meio da classe associativa `DiagnosticoRecomendacao`. `LoginAttempt` não tem relacionamento:
guarda só o hash de IP + e-mail para limitar tentativas de login.
"""


if __name__ == '__main__':
    destino = ROOT / 'docs' / 'diagrama-classes.md'
    destino.write_text(documento(), encoding='utf-8')
    print(f'Gerado: {destino}')
