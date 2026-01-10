#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator


# ----------------------------
# Color helpers
# ----------------------------
ANSI_RESET = "\x1b[0m"
ANSI_DIM = "\x1b[2m"
ANSI_RED = "\x1b[31m"
ANSI_YELLOW = "\x1b[33m"
ANSI_CYAN = "\x1b[36m"


def supports_color(stream) -> bool:
    return hasattr(stream, "isatty") and stream.isatty()


def colorize(s: str, color: str, enabled: bool) -> str:
    return f"{color}{s}{ANSI_RESET}" if enabled else s


def highlight_regex_first(line: str, rx: re.Pattern, enabled: bool) -> str:
    if not enabled:
        return line
    m = rx.search(line)
    if not m:
        return line
    a, b = m.span()
    return line[:a] + ANSI_YELLOW + line[a:b] + ANSI_RESET + line[b:]


# ----------------------------
# Stats
# ----------------------------
@dataclass
class Stats:
    files_seen: int = 0
    files_read: int = 0
    files_skipped_binary: int = 0
    lines_seen: int = 0
    lines_reported: int = 0
    elapsed_s: float = 0.0


# ----------------------------
# File iteration + heuristics
# ----------------------------
def is_probably_text_file(path: Path, sample_size: int = 4096) -> bool:
    try:
        with path.open("rb") as f:
            chunk = f.read(sample_size)
        return b"\x00" not in chunk
    except OSError:
        return False


def iter_files(inputs: list[Path], recursive: bool) -> Iterator[Path]:
    for p in inputs:
        if p.is_file():
            yield p
        elif p.is_dir():
            if recursive:
                for fp in p.rglob("*"):
                    if fp.is_file():
                        yield fp
            else:
                for fp in p.glob("*"):
                    if fp.is_file():
                        yield fp


# ----------------------------
# Logging (ALWAYS ON)
# ----------------------------
def make_log_path() -> Path:
    """
    Create logs folder in the current working directory (where you run the script),
    and return a unique timestamp-based log filename.
    """
    logs_dir = Path.cwd() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return logs_dir / f"log_{ts}.txt"


def setup_logging(debug: bool) -> tuple[logging.Logger, Path]:
    logger = logging.getLogger("grep")
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.handlers.clear()

    log_path = make_log_path()

    fmt = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")

    # File handler ALWAYS enabled (all runs log to file)
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG if debug else logging.INFO)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Console handler for user-facing errors (keep terminal clean)
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.WARNING)  # warnings/errors show in terminal
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    logger.info("Log started: %s", log_path)
    logger.info("CWD: %s", Path.cwd())

    return logger, log_path


# ----------------------------
# Grep core
# ----------------------------
def grep_file(
    filepath: Path,
    rx: re.Pattern,
    invert: bool,
    count_only: bool,
    color_enabled: bool,
    logger: logging.Logger,
    stats: Stats,
) -> None:
    stats.files_seen += 1

    if not is_probably_text_file(filepath):
        stats.files_skipped_binary += 1
        logger.debug("Skipping binary file: %s", filepath)
        return

    try:
        with filepath.open("r", encoding="utf-8", errors="replace") as f:
            stats.files_read += 1
            match_count = 0

            for lineno, raw in enumerate(f, start=1):
                stats.lines_seen += 1
                line = raw.rstrip("\n")

                matched = rx.search(line) is not None
                ok = (not matched) if invert else matched

                if ok:
                    if count_only:
                        match_count += 1
                    else:
                        shown = line
                        # Highlight only in normal (non-invert) mode
                        if color_enabled and not invert:
                            shown = highlight_regex_first(shown, rx, enabled=True)

                        prefix = f"{filepath}:{lineno}:"
                        prefix = colorize(prefix, ANSI_DIM, color_enabled)
                        print(f"{prefix}{shown}")
                        stats.lines_reported += 1

            if count_only:
                prefix = colorize(f"{filepath}:", ANSI_DIM, color_enabled)
                print(f"{prefix}{match_count}")
                stats.lines_reported += 1

    except OSError as ex:
        logger.error("Cannot read '%s': %s", filepath, ex)


# ----------------------------
# CLI
# ----------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="grep.py",
        description="Lightweight grep-like utility (regex search) for files/folders.",
    )
    p.add_argument("regex", help="Regular expression pattern (Python re).")
    p.add_argument("inputs", nargs="+", help="One or more files/folders to search.")

    p.add_argument("-r", "--recursive", action="store_true", help="Recurse into folders.")
    p.add_argument("-i", "--ignore-case", action="store_true", help="Case-insensitive search.")
    p.add_argument("-v", "--not", dest="invert", action="store_true", help="Invert match (show non-matching lines).")
    p.add_argument("-c", "--count", action="store_true", help="Print count per file (one line per file).")

    p.add_argument(
        "--color",
        choices=["auto", "always", "never"],
        default="auto",
        help="Colored output/highlighting (default: auto).",
    )
    p.add_argument("--debug", action="store_true", help="Enable debug logging (more verbose log file).")

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    logger, log_path = setup_logging(args.debug)

    # Decide color mode
    if args.color == "always":
        color_enabled = True
    elif args.color == "never":
        color_enabled = False
    else:
        color_enabled = supports_color(sys.stdout)

    # Log run config
    logger.info("Args: %s", " ".join(sys.argv))
    logger.info("Options: recursive=%s ignore_case=%s invert=%s count=%s color=%s debug=%s",
                args.recursive, args.ignore_case, args.invert, args.count, args.color, args.debug)

    stats = Stats()
    t0 = time.perf_counter()

    try:
        flags = re.IGNORECASE if args.ignore_case else 0
        try:
            rx = re.compile(args.regex, flags)
        except re.error as ex:
            logger.error("Invalid regex: %s", ex)
            print(colorize(f"Invalid regex: {ex}", ANSI_RED, color_enabled), file=sys.stderr)
            return 2

        inputs = [Path(s) for s in args.inputs]
        missing = [p for p in inputs if not p.exists()]
        if missing:
            for m in missing:
                logger.error("Path not found: %s", m)
            print(colorize(f"Error: {len(missing)} input path(s) not found.", ANSI_RED, color_enabled), file=sys.stderr)
            return 2

        for fp in iter_files(inputs, recursive=args.recursive):
            grep_file(
                filepath=fp,
                rx=rx,
                invert=args.invert,
                count_only=args.count,
                color_enabled=color_enabled,
                logger=logger,
                stats=stats,
            )

        return 0

    except KeyboardInterrupt:
        logger.warning("Interrupted by user (Ctrl+C).")
        print(colorize("Interrupted.", ANSI_RED, color_enabled), file=sys.stderr)
        return 130

    finally:
        stats.elapsed_s = time.perf_counter() - t0

        # ALWAYS write performance metrics to the log file
        logger.info(
            "Performance: files_seen=%d files_read=%d skipped_binary=%d lines_seen=%d lines_reported=%d elapsed=%.6fs",
            stats.files_seen,
            stats.files_read,
            stats.files_skipped_binary,
            stats.lines_seen,
            stats.lines_reported,
            stats.elapsed_s,
        )

        # Also tell user where the log is (stderr, so piping output still works)
        msg = f"Log written to: {log_path}"
        print(colorize(msg, ANSI_CYAN, color_enabled), file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
