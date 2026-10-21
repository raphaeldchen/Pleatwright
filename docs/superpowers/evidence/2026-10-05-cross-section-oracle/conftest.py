"""Shared test machinery for the cross-section oracle's unit tests.

Holds ONE copy of the import-allowlist check. Both `lines.py` and `strip.py`
must be free of production code and of `geom` (design spec section 2.3), and
the check for that is identical in structure for each -- so it lives here
rather than being repeated, and it carries a POSITIVE CONTROL proving it can
actually fail. A checker that never fails is the same trap as a gate that
never fires.

This file is test machinery. Neither `lines.py` nor `strip.py` imports it,
and their own allowlists do not list it.
"""
import ast
import os

#: Module names whose mere MENTION in the oracle's source -- docstrings
#: included -- would indicate a production dependency. The constraint is
#: literal, so the scan is too.
PRODUCTION_NAMES = ("layer_order", "layer_certify", "box_pleat", "flat_fold",
                    "build", "mcp_harness")


def imported_modules(src):
    """Every module named by an import statement in `src`.

    Structural, via the AST, rather than by substring: a substring scan would
    match a module name inside a comment and miss `from x import y`.
    """
    out = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            out.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            out.add(node.module)
    return out


def assert_import_allowlist(path, allowed, banned=PRODUCTION_NAMES):
    """The oracle module at `path` imports only `allowed` and names no
    module in `banned`.

    Three checks, all required:
      1. every imported module is in `allowed`;
      2. no dynamic-import escape hatch, which would evade check 1;
      3. no `banned` name anywhere in the RAW source, docstrings included.

    Check 3 is on raw source deliberately. The predecessor slice hit the
    contradiction of a docstring naming a module its own test banned, and
    resolved it the wrong way round once by relaxing the test. The rule is:
    conform the docstring -- cite the file and line instead -- never the test.
    """
    with open(path) as fh:
        src = fh.read()
    name = os.path.basename(path)
    extra = sorted(imported_modules(src) - set(allowed))
    assert not extra, (
        f"{name} imports {extra} beyond the allowlist {sorted(allowed)}")
    for dynamic in ("__import__", "importlib"):
        assert dynamic not in src, (
            f"{name} mentions {dynamic!r}; a dynamic import would evade the "
            f"AST allowlist")
    for bad in banned:
        assert bad not in src, (
            f"{name} mentions {bad!r}; the oracle must not import or name "
            f"production code, or the comparison is circular")
