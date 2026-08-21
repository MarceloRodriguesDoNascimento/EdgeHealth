from pathlib import Path


def test_readme_lists_10_functionalities():
    readme = Path(__file__).resolve().parents[1] / "README.md"
    text = readme.read_text(encoding="utf-8")

    assert "Funcionalidades Implementadas" in text
    count = text.count("\n")
    assert count > 0
    assert "1." in text and "10." in text
