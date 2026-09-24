"""CLAUDE.md §2 as a CI check: every folder has a CONTEXT.md that names each of its files, and the root
CONTEXT.md names every folder. Package markers (`__init__.py`, `py.typed`) are exempt. Exit 1 on any gap."""

import subprocess
import sys
from pathlib import Path, PurePosixPath

EXEMPT = {"CONTEXT.md", "__init__.py", "py.typed"}


def main() -> int:
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], check=True, capture_output=True,
    ).stdout.decode("utf-8")
    files = [PurePosixPath(p) for p in listed.split("\0") if p and Path(p).is_file()]
    folders = sorted({f.parent for f in files})
    root_map = Path("CONTEXT.md").read_text(encoding="utf-8")
    problems = []
    for folder in folders:
        context = folder / "CONTEXT.md"
        if context not in files:
            problems.append(f"{folder}/: no CONTEXT.md")
            continue
        text = Path(context).read_text(encoding="utf-8")
        problems += [f"{context}: does not mention {f.name}"
                     for f in files if f.parent == folder and f.name not in EXEMPT and f.name not in text]
        if folder != PurePosixPath(".") and f"{folder}/" not in root_map:
            problems.append(f"CONTEXT.md: the map does not mention {folder}/")
    print(*problems, sep="\n") if problems else None
    print(f"{len(folders)} folders, {len(files)} files, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
