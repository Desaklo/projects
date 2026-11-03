#!/usr/bin/env python3
"""List, show, and search local markdown notes."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DEFAULT_DIR = Path(__file__).resolve().parent / "notes"

EXIT_OK = 0
EXIT_USER = 1
EXIT_ERROR = 2

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_CLOSING_HASHES = re.compile(r"\s+#+\s*$")


def fail(message: str, code: int) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def read_note(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        fail(f"{path.name} is not valid UTF-8", EXIT_ERROR)
    except OSError as exc:
        fail(f"cannot read {path.name}: {exc}", EXIT_ERROR)
    return ""


def discover_notes(directory: Path) -> list[Path]:
    if not directory.exists():
        fail(f"notes directory does not exist: {directory}", EXIT_ERROR)
    if not directory.is_dir():
        fail(f"not a directory: {directory}", EXIT_ERROR)
    try:
        entries = list(directory.iterdir())
    except OSError as exc:
        fail(f"cannot read {directory}: {exc}", EXIT_ERROR)

    notes = [
        entry
        for entry in entries
        if entry.is_file()
        and not entry.name.startswith(".")
        and entry.suffix.lower() == ".md"
    ]
    notes.sort(key=lambda entry: (entry.name.casefold(), entry.name))
    return notes


def extract_title(text: str, fallback: str) -> str:
    for raw in text.splitlines():
        match = _HEADING.match(raw.strip())
        if not match:
            continue
        title = _CLOSING_HASHES.sub("", match.group(2)).strip()
        if title:
            return title
    for raw in text.splitlines():
        line = raw.strip()
        if line:
            return line
    return fallback


def count_label(amount: int, singular: str, plural: str) -> str:
    word = singular if amount == 1 else plural
    return f"{amount} {word}"


def cmd_list(notes: list[Path]) -> int:
    if not notes:
        print("No notes yet. Add a .md file to the notes directory.")
        return EXIT_OK

    titled = [(path, extract_title(read_note(path), path.stem)) for path in notes]
    width = max(len(path.name) for path, _title in titled)
    for path, title in titled:
        print(f"{path.name.ljust(width)}  {title}")
    print(f"\n{count_label(len(notes), 'note', 'notes')}")
    return EXIT_OK


def _one_match(query: str, matches: list[Path]) -> Path | None:
    if not matches:
        return None
    if len(matches) > 1:
        found = ", ".join(item.name for item in matches)
        fail(f"{query!r} matches more than one note: {found}", EXIT_USER)
    return matches[0]


def resolve_note(notes: list[Path], name: str) -> Path:
    query = name.strip()
    if (
        not query
        or query in {".", ".."}
        or "/" in query
        or "\\" in query
        or "\0" in query
    ):
        fail(f"note name must be a file name, not a path: {query!r}", EXIT_USER)

    folded = query.casefold()
    if folded.endswith(".md"):
        stem = query[:-3].strip()
    else:
        stem = query
    if not stem:
        fail(f"no note named {query!r}", EXIT_USER)
    stem_folded = stem.casefold()

    chosen = _one_match(query, [item for item in notes if item.name == query])
    if chosen is not None:
        return chosen

    chosen = _one_match(query, [item for item in notes if item.stem == stem])
    if chosen is not None:
        return chosen

    chosen = _one_match(
        query, [item for item in notes if item.name.casefold() == folded]
    )
    if chosen is not None:
        return chosen

    chosen = _one_match(
        query, [item for item in notes if item.stem.casefold() == stem_folded]
    )
    if chosen is not None:
        return chosen

    chosen = _one_match(
        query,
        [item for item in notes if item.stem.casefold().startswith(stem_folded)],
    )
    if chosen is not None:
        return chosen

    fail(f"no note named {query!r}", EXIT_USER)
    return notes[0]


def cmd_show(notes: list[Path], name: str) -> int:
    path = resolve_note(notes, name)
    text = read_note(path)
    sys.stdout.write(text)
    if text and not text.endswith("\n"):
        sys.stdout.write("\n")
    return EXIT_OK


def cmd_search(notes: list[Path], query: str, case_sensitive: bool) -> int:
    needle = query if case_sensitive else query.casefold()
    matches: list[tuple[str, int, str]] = []
    for path in notes:
        for lineno, line in enumerate(read_note(path).splitlines(), start=1):
            haystack = line if case_sensitive else line.casefold()
            if needle in haystack:
                matches.append((path.name, lineno, line.strip()))

    if not matches:
        print(f"No matches for {query!r}.")
        return EXIT_OK

    for name, lineno, line in matches:
        print(f"{name}:{lineno}: {line}")
    files = len({name for name, _lineno, _line in matches})
    print(
        f"\n{count_label(len(matches), 'match', 'matches')} "
        f"in {count_label(files, 'note', 'notes')}"
    )
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--dir",
        type=Path,
        default=DEFAULT_DIR,
        help="notes directory (default: notes next to this script)",
    )
    # Repeated on each subcommand so `--dir` works before or after the command.
    # SUPPRESS keeps an omitted flag from overwriting a value set on the parent.
    sub_common = argparse.ArgumentParser(add_help=False)
    sub_common.add_argument(
        "--dir",
        type=Path,
        default=argparse.SUPPRESS,
        help="notes directory (default: notes next to this script)",
    )

    parser = argparse.ArgumentParser(
        prog="notes.py",
        description="List, show, and search local markdown notes.",
        epilog=(
            "examples:\n"
            "  notes.py list\n"
            "  notes.py show welcome\n"
            "  notes.py search pathlib\n"
            "  notes.py --dir ~/notes search meeting\n"
            "\n"
            "show accepts a file name with or without .md. A unique prefix works.\n"
            "search looks for a literal substring and ignores case unless\n"
            "--case-sensitive is set. Only .md files in the top level of the\n"
            "notes directory are read.\n"
            "\n"
            "exit codes:\n"
            "  0  success (a search with no matches is still success)\n"
            "  1  user error (unknown or ambiguous note, empty search text)\n"
            "  2  bad usage, or the notes directory cannot be read"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[common],
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser(
        "list",
        parents=[sub_common],
        help="list notes and their titles",
        description="List markdown notes and the title of each one.",
    )

    show = sub.add_parser(
        "show",
        parents=[sub_common],
        help="print one note",
        description="Print one note. The .md suffix is optional.",
    )
    show.add_argument("name", nargs="+", help="file name, with or without .md")

    search = sub.add_parser(
        "search",
        parents=[sub_common],
        help="search note text",
        description="Search note text for a literal substring.",
    )
    search.add_argument("keyword", nargs="+", help="text to find")
    search.add_argument(
        "--case-sensitive",
        action="store_true",
        help="match letter case exactly",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    notes = discover_notes(args.dir.expanduser())

    if args.command == "list":
        return cmd_list(notes)
    if args.command == "show":
        name = " ".join(args.name).strip()
        if not name:
            print("error: note name is empty", file=sys.stderr)
            return EXIT_USER
        return cmd_show(notes, name)
    if args.command == "search":
        query = " ".join(args.keyword).strip()
        if not query:
            print("error: search text is empty", file=sys.stderr)
            return EXIT_USER
        return cmd_search(notes, query, args.case_sensitive)

    fail(f"unknown command: {args.command}", EXIT_ERROR)
    return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
