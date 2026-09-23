"""
Guard: a fresh clone configured by copying src/config_example.py must support
EVERY config read in the application — no AttributeError lurking behind a
developer's richer local src/config.py.

legal_basis: infrastructure — this masked real breakage once: the Vorabpauschale
code read the since-retired config.BASISZINS_BY_YEAR, every test stayed green
against a local config that still had the table, and only a clean-clone run
would have failed.
"""
import ast
import re
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"


def _names_assigned_in_config_example():
    tree = ast.parse((SRC / "config_example.py").read_text())
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def _aliased_config_reads(text):
    """Attributes read through whatever name a file binds src.config to --
    `import src.config as global_config`, `from src import config as app_config`,
    `import src.config` -- or imported from it directly. The `config.X` pattern
    below misses every alias (`global_config.X` has no word boundary before
    `config`)."""
    tree = ast.parse(text)
    aliases, reads = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == "src.config":
                    aliases.add(a.asname or "src.config")
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            for a in node.names:
                if node.module == "src" and a.name == "config":
                    aliases.add(a.asname or "config")
                elif node.module == "src.config" and a.name.isupper():
                    reads.add(a.name)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr.isupper():
            if ast.unparse(node.value) in aliases:
                reads.add(node.attr)
    return reads


def _config_attributes_read_in_src():
    reads = {}
    pattern = re.compile(r"\bconfig\.([A-Z][A-Z0-9_]*)")
    for py in SRC.rglob("*.py"):
        if py.name in ("config.py", "config_example.py"):
            continue
        text = py.read_text()
        for attr in set(pattern.findall(text)) | _aliased_config_reads(text):
            reads.setdefault(attr, set()).add(str(py.relative_to(SRC)))
    return reads


def test_every_config_read_is_defined_in_config_example():
    defined = _names_assigned_in_config_example()
    missing = {attr: sorted(files)
               for attr, files in _config_attributes_read_in_src().items()
               if attr not in defined}
    assert not missing, (
        "src/ reads config attributes that src/config_example.py does not "
        f"define — a clean clone would crash: {missing}")
