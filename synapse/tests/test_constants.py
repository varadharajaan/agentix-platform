"""Guard: operative literals live only in synapse.constants.

Scans every module under ``src/synapse`` with AST (docstrings excluded) and
fails if a forbidden literal — in-cluster URLs, EverMemOS API paths, CRD
versions, annotations, the placeholder key — appears anywhere but
``constants.py``. Add new literals to ``constants.py`` first, then import.
"""

from __future__ import annotations

import ast
from pathlib import Path

import synapse

SRC = Path(synapse.__file__).parent

FORBIDDEN_OUTSIDE_CONSTANTS = [
    ".svc.cluster.local",  # in-cluster service URLs
    "/api/v1/memories",  # EverMemOS REST paths
    "kagent.dev/",  # CRD api version
    "platform.agentic.io/",  # platform annotations
    "gateway-injected",  # PLACEHOLDER_API_KEY value
]


def _docstring_lines(tree: ast.AST) -> set[int]:
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(
            node, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
        ):
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                lines.add(first.value.lineno)
    return lines


def _operative_strings(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text())
    doc_lines = _docstring_lines(tree)
    return [
        (node.lineno, node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.lineno not in doc_lines
    ]


def test_no_hardcoded_literals_outside_constants():
    offenders: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        if path.name == "constants.py":
            continue
        for lineno, value in _operative_strings(path):
            for literal in FORBIDDEN_OUTSIDE_CONSTANTS:
                if literal in value:
                    offenders.append(f"{path.name}:{lineno}: {value!r} ({literal})")
    assert not offenders, "hardcoded literals belong in constants.py:\n" + "\n".join(
        offenders
    )


def test_constants_are_the_docstring_examples():
    """The well-known direct-mode endpoints exist for docs/examples to reuse."""
    from synapse.constants import OLLAMA_BASE_URL, OPENAI_BASE_URL

    assert OLLAMA_BASE_URL.endswith("11434/v1")
    assert OPENAI_BASE_URL.startswith("https://")
