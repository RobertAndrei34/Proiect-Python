#!/usr/bin/env python3
import sys
import re


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def usage():
    eprint("Usage: python grep.py <regex> <file | ->")
    eprint('Example: python grep.py "error|fail" logs.txt')
    eprint('Use "-" as file to read from standard input.')


def main() -> int:
    if len(sys.argv) != 3:
        usage()
        return 2

    pattern = sys.argv[1]
    path = sys.argv[2]

    try:
        rx = re.compile(pattern)
    except re.error as ex:
        eprint(f"Invalid regex: {ex}")
        return 2

    # Open file or read from stdin
    if path == "-":
        f = sys.stdin
        close_after = False
    else:
        try:
            f = open(path, "r", encoding="utf-8", errors="replace")
            close_after = True
        except FileNotFoundError:
            eprint(f"File not found: {path}")
            return 2
        except OSError as ex:
            eprint(f"Cannot open file '{path}': {ex}")
            return 2

    try:
        for lineno, line in enumerate(f, start=1):
            line_no_nl = line.rstrip("\n")
            if rx.search(line_no_nl) is not None:
                # Print matching lines with line numbers
                print(f"{lineno}:{line_no_nl}")
    finally:
        if close_after:
            f.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
