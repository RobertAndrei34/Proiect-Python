#!/usr/bin/env python3
import sys
import re
import os


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def usage():
    eprint("Usage:")
    eprint("  python grep.py <regex> <path> [-ignoreCase] [-not] [-count]")
    eprint("")
    eprint("Options:")
    eprint("  -ignoreCase   Case-insensitive regex")
    eprint("  -not          Invert match (show non-matching lines / count them)")
    eprint("  -count        Print count per file (one line per file)")
    eprint("")
    eprint("Examples:")
    eprint('  python grep.py "test" C:\\MyFolder -ignoreCase')
    eprint('  python grep.py "pattern" folder -ignoreCase -count')
    eprint('  python grep.py "pattern" folder -ignoreCase -count -not')


def is_probably_text_file(path: str, sample_size: int = 4096) -> bool:
    try:
        with open(path, "rb") as f:
            chunk = f.read(sample_size)
        return b"\x00" not in chunk
    except OSError:
        return False


def iter_files(root: str):
    if os.path.isfile(root):
        yield root
        return
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            yield os.path.join(dirpath, name)


def process_file(rx: re.Pattern, filepath: str, invert: bool, do_count: bool):
    count = 0
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for lineno, line in enumerate(f, start=1):
                text = line.rstrip("\n")
                matched = rx.search(text) is not None
                ok = (not matched) if invert else matched

                if ok:
                    if do_count:
                        count += 1
                    else:
                        print(f"{filepath}:{lineno}:{text}")
    except (OSError, UnicodeError) as ex:
        eprint(f"Cannot read '{filepath}': {ex}")
        return

    if do_count:
        print(f"{filepath}:{count}")


def main() -> int:
    if len(sys.argv) < 3:
        usage()
        return 2

    pattern = sys.argv[1]
    path = sys.argv[2]
    opts = [a.lower() for a in sys.argv[3:]]

    ignore_case = "-ignorecase" in opts
    invert = "-not" in opts
    do_count = "-count" in opts

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
        process_file(rx, fp, invert=invert, do_count=do_count)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
