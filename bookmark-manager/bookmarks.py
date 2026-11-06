#!/usr/bin/env python3
"""A small command-line bookmark manager. Bookmarks persist in a local JSON file."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

DEFAULT_FILE = Path(__file__).resolve().parent / "bookmarks.json"

EXIT_OK = 0
EXIT_USER = 1
EXIT_ERROR = 2


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def fail(message: str, code: int) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def normalize_url(raw: str) -> str | None:
    """Return a canonical http(s) URL, or None when `raw` is not one.

    A missing scheme becomes https://. The scheme and host are lowercased,
    and the default ports 80 and 443 are dropped so the same page is not
    stored twice.
    """
    text = raw.strip()
    if not text or any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in text):
        return None
    if "://" not in text:
        text = "https:" + text if text.startswith("//") else "https://" + text
    try:
        parts = urlsplit(text)
        port = parts.port
    except ValueError:
        return None
    scheme = parts.scheme.lower()
    host = parts.hostname
    if scheme not in {"http", "https"} or not host:
        return None
    host = host.lower()
    if ":" in host:
        host = f"[{host}]"
    netloc = host
    if port is not None and not (
        (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    ):
        netloc = f"{host}:{port}"
    if parts.username is not None:
        auth = parts.username
        if parts.password is not None:
            auth = f"{auth}:{parts.password}"
        netloc = f"{auth}@{netloc}"
    return urlunsplit((scheme, netloc, parts.path, parts.query, parts.fragment))


def default_title(url: str) -> str:
    parts = urlsplit(url)
    path = "" if parts.path == "/" else parts.path
    title = parts.netloc + path
    if parts.query:
        title += "?" + parts.query
    if parts.fragment:
        title += "#" + parts.fragment
    return title or url


def clean_title(words: list[str]) -> str:
    return " ".join(" ".join(words).split())


def empty_store() -> dict:
    return {"next_id": 1, "bookmarks": []}


def load_store(path: Path) -> dict:
    if not path.exists():
        return empty_store()
    if not path.is_file():
        fail(f"not a file: {path}", EXIT_ERROR)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        fail(f"cannot read {path}: {exc}", EXIT_ERROR)
    if not raw.strip():
        return empty_store()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        fail(f"{path} is not valid JSON ({exc})", EXIT_ERROR)
    if not isinstance(data, dict) or not isinstance(data.get("bookmarks"), list):
        fail(f"{path} has an unexpected format", EXIT_ERROR)

    ids: list[int] = []
    seen: set[int] = set()
    for item in data["bookmarks"]:
        ident = item.get("id") if isinstance(item, dict) else None
        title = item.get("title") if isinstance(item, dict) else None
        url = item.get("url") if isinstance(item, dict) else None
        created = item.get("created_at") if isinstance(item, dict) else None
        if (
            not isinstance(ident, int)
            or isinstance(ident, bool)
            or ident < 1
            or not isinstance(title, str)
            or not isinstance(url, str)
            or not url.strip()
            or (created is not None and not isinstance(created, str))
            or ident in seen
        ):
            fail(f"{path} has an unexpected format", EXIT_ERROR)
        seen.add(ident)
        ids.append(ident)

    next_id = data.get("next_id", 1)
    if not isinstance(next_id, int) or isinstance(next_id, bool) or next_id < 1:
        next_id = 1
    if ids:
        next_id = max(next_id, max(ids) + 1)
    data["next_id"] = next_id
    return data


def save_store(path: Path, data: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        fail(f"cannot create {path.parent}: {exc}", EXIT_ERROR)

    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=".bookmarks-",
            suffix=".tmp",
            delete=False,
        ) as tmp:
            tmp.write(payload)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = Path(tmp.name)
        os.replace(tmp_path, path)
        tmp_path = None
    except OSError as exc:
        fail(f"cannot write {path}: {exc}", EXIT_ERROR)
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


def same_url(stored: str, normalized: str) -> bool:
    if stored == normalized:
        return True
    return normalize_url(stored) == normalized


def find_url(store: dict, url: str) -> dict | None:
    for item in store["bookmarks"]:
        if same_url(item["url"], url):
            return item
    return None


def find_id(store: dict, bookmark_id: int) -> dict | None:
    for item in store["bookmarks"]:
        if item["id"] == bookmark_id:
            return item
    return None


def count_label(count: int, singular: str, plural: str) -> str:
    noun = singular if count == 1 else plural
    return f"{count} {noun}"


def print_bookmarks(items: list[dict], footer: str) -> None:
    id_width = max(len(str(item["id"])) for item in items)
    title_width = max(len(item["title"]) for item in items)
    for item in items:
        ident = str(item["id"]).rjust(id_width)
        title = item["title"].ljust(title_width)
        print(f"{ident}  {title}  {item['url']}")
    print(f"\n{footer}")


def cmd_add(store: dict, raw_url: str, title_words: list[str]) -> int:
    url = normalize_url(raw_url)
    if url is None:
        print(f"error: not an http(s) URL: {raw_url}", file=sys.stderr)
        return EXIT_USER
    existing = find_url(store, url)
    if existing is not None:
        print(
            f"error: already saved as #{existing['id']}: {existing['title']}",
            file=sys.stderr,
        )
        return EXIT_USER
    title = clean_title(title_words) or default_title(url)
    item = {
        "id": store["next_id"],
        "title": title,
        "url": url,
        "created_at": utc_now(),
    }
    store["next_id"] += 1
    store["bookmarks"].append(item)
    print(f"Added #{item['id']}  {item['title']}  {item['url']}")
    return EXIT_OK


def cmd_list(store: dict) -> int:
    items = store["bookmarks"]
    if not items:
        print('No bookmarks yet. Add one with: bookmarks.py add https://example.com "Example"')
        return EXIT_OK
    print_bookmarks(items, count_label(len(items), "bookmark", "bookmarks"))
    return EXIT_OK


def cmd_search(store: dict, words: list[str]) -> int:
    query = clean_title(words)
    if not query:
        print("error: search text is empty", file=sys.stderr)
        return EXIT_USER
    folded = query.casefold()
    matches = [
        item
        for item in store["bookmarks"]
        if folded in item["title"].casefold() or folded in item["url"].casefold()
    ]
    if not matches:
        print(f"No matches for {query!r}")
        return EXIT_OK
    print_bookmarks(matches, count_label(len(matches), "match", "matches"))
    return EXIT_OK


def cmd_remove(store: dict, bookmark_id: int) -> tuple[int, bool]:
    for index, item in enumerate(store["bookmarks"]):
        if item["id"] == bookmark_id:
            store["bookmarks"].pop(index)
            print(f"Removed #{item['id']}  {item['title']}  {item['url']}")
            return EXIT_OK, True
    print(f"error: no bookmark with id {bookmark_id}", file=sys.stderr)
    return EXIT_USER, False


def build_parser() -> argparse.ArgumentParser:
    file_help = "path to the bookmarks file (default: bookmarks.json next to this script)"
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--file", type=Path, default=DEFAULT_FILE, help=file_help)
    # Repeated on each subcommand so `--file` works before or after the command.
    # SUPPRESS keeps an omitted flag from overwriting a value set on the parent.
    sub_common = argparse.ArgumentParser(add_help=False)
    sub_common.add_argument(
        "--file",
        type=Path,
        default=argparse.SUPPRESS,
        help=file_help,
    )

    parser = argparse.ArgumentParser(
        prog="bookmarks.py",
        description="Save and search bookmarks in a local JSON file.",
        epilog=(
            "examples:\n"
            '  bookmarks.py add https://docs.python.org/3/ "Python docs"\n'
            "  bookmarks.py add example.com\n"
            "  bookmarks.py list\n"
            "  bookmarks.py search python\n"
            "  bookmarks.py remove 1\n"
            "\n"
            "a missing scheme becomes https://. the host is stored in lowercase.\n"
            "search matches a title or a URL and ignores case.\n"
            "\n"
            "exit codes:\n"
            "  0  success (an empty list or no search matches is still success)\n"
            "  1  user error (bad URL, duplicate URL, unknown id, empty search)\n"
            "  2  bad usage, or the data file cannot be read or written"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[common],
    )
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser(
        "add",
        parents=[sub_common],
        help="save a bookmark",
        description="Save a bookmark. Separate title words are joined into one title.",
    )
    add.add_argument("url", help="http(s) URL; https:// is added when the scheme is missing")
    add.add_argument(
        "title",
        nargs="*",
        help="title (optional; the site name is used when omitted)",
    )

    sub.add_parser(
        "list",
        parents=[sub_common],
        help="list every bookmark",
        description="List every bookmark, oldest first.",
    )

    search = sub.add_parser(
        "search",
        parents=[sub_common],
        help="find bookmarks by title or URL",
        description="Find bookmarks whose title or URL contains this text. Case is ignored.",
    )
    search.add_argument("text", nargs="+", help="text to find; separate words are joined")

    remove = sub.add_parser(
        "remove",
        parents=[sub_common],
        help="delete a bookmark by id",
        description="Delete the bookmark with this id. Ids are shown by list and search.",
    )
    remove.add_argument("id", type=int, help="id of the bookmark to delete")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = args.file.expanduser()
    store = load_store(path)

    if args.command == "add":
        code = cmd_add(store, args.url, args.title)
        if code == EXIT_OK:
            save_store(path, store)
        return code
    if args.command == "list":
        return cmd_list(store)
    if args.command == "search":
        return cmd_search(store, args.text)
    if args.command == "remove":
        code, changed = cmd_remove(store, args.id)
        if changed:
            save_store(path, store)
        return code
    fail(f"unknown command: {args.command}", EXIT_ERROR)
    return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
