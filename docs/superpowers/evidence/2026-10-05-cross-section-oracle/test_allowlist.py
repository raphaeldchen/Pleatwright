"""POSITIVE CONTROL for `conftest.assert_import_allowlist`.

A checker that cannot fail is the same trap as a gate that never fires, and
this arc has already shipped one of those -- an `is_convex` that admitted the
clockwise face it existed to reject. So each of the checker's three checks is
exercised here against a purpose-built file, plus a fourth assertion that it
PASSES a clean one, since a checker that always fails is the mirror-image
trap.

ITS OWN FILE, for two reasons learned by running the first draft of it:

  * pointing the control at `conftest.py` does not work. That file contains
    the literal `__import__` inside its own dynamic-import check, so check 2
    fires first and MASKS checks 1 and 3.
  * pytest does not collect test functions out of `conftest.py` unless the
    file is named on the command line, so a control living there would
    silently not run under the ordinary invocation.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import pytest                          # noqa: E402
from conftest import assert_import_allowlist   # noqa: E402


def test_each_check_fires_and_a_clean_file_passes(tmp_path):
    def _f(name, body):
        p = tmp_path / name
        p.write_text(body)
        return str(p)

    # check 1: an import outside the allowlist.
    with pytest.raises(AssertionError, match="beyond the allowlist"):
        assert_import_allowlist(_f("a.py", "import os\n"),
                                allowed=("fractions",))

    # check 2: a dynamic-import escape hatch, which is NOT an import node and
    # so passes check 1 -- which is exactly why check 2 exists.
    with pytest.raises(AssertionError, match="dynamic import"):
        assert_import_allowlist(_f("b.py", "x = __import__('os')\n"),
                                allowed=())

    # check 3: a banned name in a DOCSTRING rather than an import, which is
    # the case the raw-source scan exists for.
    with pytest.raises(AssertionError, match="layer_order"):
        assert_import_allowlist(_f("c.py", '"""cites layer_order."""\n'),
                                allowed=())

    # and it must PASS a clean file.
    assert_import_allowlist(_f("d.py", "from fractions import Fraction\n"),
                            allowed=("fractions",))
