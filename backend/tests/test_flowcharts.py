"""Every Controller, Service and Repository named in docs/fluxogramas.md exists in the code,
with the cited method: the flowcharts cannot silently fall out of date."""
import ast
import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
FLOWCHARTS = BACKEND.parent / 'docs' / 'fluxogramas.md'
LAYER = re.compile(r'\b([A-Z]\w*(?:Controller|Service|Repository))\b(?:\.(\w+))?')


def code_classes():
    """{class name: {method names}} of every class in the backend layers."""
    found = {}
    for folder in ('controllers', 'services', 'repositories', 'models'):
        for path in (BACKEND / folder).rglob('*.py'):
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                if isinstance(node, ast.ClassDef):
                    found[node.name] = {n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    return found


def flowchart_references():
    text = FLOWCHARTS.read_text(encoding='utf-8')
    blocks = re.findall(r'```mermaid\n(.*?)```', text, re.S)
    return blocks, {(m.group(1), m.group(2)) for block in blocks for m in LAYER.finditer(block)}


def test_six_flowcharts_cover_input_retrieval_and_ai():
    blocks, _ = flowchart_references()
    headings = re.findall(r'^## \d\. (Entrada|Recuperação) de dados', FLOWCHARTS.read_text(encoding='utf-8'), re.M)
    assert len(blocks) == 7  # legend + 6 use cases
    assert 'GeminiService.executar' in blocks[6], 'o caso de uso de IA deve passar pelo GeminiService'
    assert headings.count('Entrada') >= 2 and headings.count('Recuperação') >= 2
    for block in blocks[1:]:
        assert 'Controller.' in block and 'Service' in block and 'Repository.' in block, 'fluxo sem passar por todas as camadas'


def test_every_cited_class_and_method_exists():
    classes = code_classes()
    _, references = flowchart_references()
    assert len({name for name, _ in references}) >= 25
    problems = []
    for name, method in sorted(references, key=lambda r: (r[0], r[1] or '')):
        if name not in classes:
            problems.append(f'classe inexistente: {name}')
        elif method and method not in classes[name]:
            problems.append(f'método inexistente: {name}.{method}')
    assert not problems, problems
