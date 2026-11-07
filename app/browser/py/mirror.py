"""Which files in a run folder are new or changed, so they can be copied into browser storage.

A snapshot maps each file's path, relative to the root with forward slashes,
to its (mtime_ns, size). changed() reports the paths that are new or whose
signature differs from an earlier snapshot. Deletions are not reported: the
browser side handles them as run deletion.
"""
import os


def snapshot(root):
    """Relative path -> (mtime_ns, size) for every file under root."""
    out = {}
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            full = os.path.join(dirpath, name)
            try:
                st = os.stat(full)
            except FileNotFoundError:  # removed after the walk listed it
                continue
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            out[rel] = (st.st_mtime_ns, st.st_size)
    return out


def changed(root, before):
    """(sorted paths new or changed since `before`, the new snapshot)."""
    after = snapshot(root)
    paths = sorted(p for p, sig in after.items() if before.get(p) != sig)
    return paths, after
