"""Create task-owned private directories without changing existing ancestors."""

from __future__ import annotations

import os
from pathlib import Path


def ensure_private_dir(path: Path, *, tighten_existing_leaf: bool = True) -> Path:
    path = Path(path)
    missing: list[Path] = []
    cursor = path
    while not cursor.exists():
        missing.append(cursor)
        parent = cursor.parent
        if parent == cursor:
            break
        cursor = parent

    for component in reversed(missing):
        component.mkdir(mode=0o700)
        if os.name == "posix":
            component.chmod(0o700)

    if tighten_existing_leaf and os.name == "posix" and path.exists():
        path.chmod(0o700)
    return path
