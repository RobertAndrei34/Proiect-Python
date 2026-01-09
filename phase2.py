#!/usr/bin/env python3
import sys
import re
import os


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def usage():
    eprint("Usage:")
    eprint("  python grep.py <regex> <path> [-ignoreCase]")
    eprint("")
    eprint("Where <path> can be a file or a directory.")
    eprint("Examples:")
    eprint('  python grep.py "test" C:\\MyFolder -ignoreCase')
    eprint('  python grep.py "error|fail" logs.txt')


def is_probably_text_file(path: str, sample_size: int = 4096) -> bool:
    # Simple heuristic: if it contains NUL bytes in the first chunk, treat as binary.
    try:
        with open(path, "rb") as f:
            chunk = f.read(sample_size)
        return b"\x00" not in chunk
    except OSError:
        return False


def iter_files(root: str):
    # Yields file paths under root (recursively if root is a directory).
    if os.path.isfile(root):
        yield root
        return

    for dirpath, dirnames, filenames in os.walk(root):
        for name in filenames:
            yield os.path.join(dirpath, name)


def search_in_file(rx: re.Pattern, filepath: str):
    # Prints matches as: filepath:lineno:line
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for lineno, line in enumerate(f, start=1):
                text = line.rstrip("\n")
                if rx.search(text) is not None:
                    print(f"{filepath}:{lineno}:{text}")
    except (OSError, UnicodeError) as ex:
        eprint(f"Cannot read '{filepath}': {ex}")


def main() -> int:
    if len(sys.argv) < 3:
        usage()
        return 2

    pattern = sys.argv[1]
    path = sys.argv[2]
    ignore_case = any(arg.lower() == "-ignorecase" for arg in sys.argv[3:])

    flags = re.IGNORECASE if ignore_case else 0
    try:
        rx = re.compile(pattern, flags)
    except re.error as ex:
        eprint(f"Invalid regex: {ex}")
        return 2

    if not os.path.exists(path):
        eprint(f"Path not found: {path}")
        return 2

    for fp in iter_files(path):
        if not os.path.isfile(fp):
            continue
        if not is_probably_text_file(fp):
            continue
        search_in_file(rx, fp)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
