"""Zip the runtime Python (runtime_files.RUNTIME) into py.zip, the bundle the browser unzips into Pyodide.

    python app/browser/bundle_py.py <out_zip>
"""
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from runtime_files import RUNTIME, ROOT  # noqa: E402

_EPOCH = (2020, 1, 1, 0, 0, 0)   # one fixed timestamp, so the same sources always make the same zip


def build(out_zip: str) -> list[str]:
    """Write out_zip holding RUNTIME at its repo-relative paths; return the member names."""
    os.makedirs(os.path.dirname(os.path.abspath(out_zip)), exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in RUNTIME:
            info = zipfile.ZipInfo(rel, _EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with open(os.path.join(ROOT, rel), "rb") as f:
                z.writestr(info, f.read())
    return list(RUNTIME)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: bundle_py.py <out_zip>")
    members = build(sys.argv[1])
    print(f"{sys.argv[1]}: {len(members)} files")
