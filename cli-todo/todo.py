#!/usr/bin/env python3
"""A small command-line todo list. Tasks persist in a local JSON file."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_FILE = Path(__file__).resolve().parent / "todos.json"

EXIT_OK = 0
EXIT_USER = 1
EXIT_ERROR = 2


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def fail(message: str, code: int) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def load_store(path: Path) -> dict:
    if not path.exists():
        return {"next_id": 1, "todos": []}
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        fail(f"cannot read {path}: {exc}", EXIT_ERROR)
    if not raw.strip():
        return {"next_id": 1, "todos": []}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        fail(f"{path} is not valid JSON ({exc})", EXIT_ERROR)
    if not isinstance(data, dict) or not isinstance(data.get("todos"), list):
        fail(f"{path} has an unexpected format", EXIT_ERROR)

    ids: list[int] = []
    for item in data["todos"]:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("id"), int)
            or isinstance(item.get("id"), bool)
            or not isinstance(item.get("text"), str)
        ):
            fail(f"{path} has an unexpected format", EXIT_ERROR)
        item["done"] = bool(item.get("done", False))
        ids.append(item["id"])

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
            prefix=".todos-",
            suffix=".tmp",
            delete=False,
        ) as tmp:
            tmp.write(payload)
            tmp_path = Path(tmp.name)
        tmp_path.replace(path)
    except OSError as exc:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
        fail(f"cannot write {path}: {exc}", EXIT_ERROR)


def cmd_add(store: dict, words: list[str]) -> int:
    text = " ".join(words).strip()
    if not text:
        print("error: todo text is empty", file=sys.stderr)
        return EXIT_USER
    item = {
        "id": store["next_id"],
        "text": text,
        "done": False,
        "created_at": utc_now(),
    }
    store["next_id"] += 1
    store["todos"].append(item)
    print(f"Added #{item['id']}: {item['text']}")
    return EXIT_OK


def cmd_list(store: dict) -> int:
    todos = store["todos"]
    if not todos:
        print('No todos yet. Add one with: todo.py add "your task"')
        return EXIT_OK

    width = max(len(str(item["id"])) for item in todos)
    open_count = 0
    done_count = 0
    for item in todos:
        if item["done"]:
            done_count += 1
            mark = "x"
        else:
            open_count += 1
            mark = " "
        ident = str(item["id"]).rjust(width)
        print(f"{ident}  [{mark}]  {item['text']}")
    print(f"\n{open_count} open, {done_count} done")
    return EXIT_OK


def cmd_done(store: dict, todo_id: int) -> tuple[int, bool]:
    for item in store["todos"]:
        if item["id"] == todo_id:
            if item["done"]:
                print(f"Already done: #{todo_id} {item['text']}")
                return EXIT_OK, False
            item["done"] = True
            item["done_at"] = utc_now()
            print(f"Done: #{todo_id} {item['text']}")
            return EXIT_OK, True
    print(f"error: no todo with id {todo_id}", file=sys.stderr)
    return EXIT_USER, False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="todo.py",
        description="A small command-line todo list. Tasks are stored in a local JSON file.",
        epilog=(
            "examples:\n"
            '  todo.py add "Buy milk"\n'
            "  todo.py list\n"
            "  todo.py done 1\n"
            "\n"
            "exit codes:\n"
            "  0  success\n"
            "  1  user error (empty text, unknown id)\n"
            "  2  bad usage, or the data file cannot be read or written"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_FILE,
        help=f"path to the todos file (default: {DEFAULT_FILE.name} next to this script)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="add a new todo")
    add.add_argument("text", nargs="+", help="todo text")

    sub.add_parser("list", help="list all todos")

    done = sub.add_parser("done", help="mark a todo as done")
    done.add_argument("id", type=int, help="id of the todo to complete")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = args.file.expanduser()
    store = load_store(path)

    if args.command == "add":
        code = cmd_add(store, args.text)
        if code == EXIT_OK:
            save_store(path, store)
        return code
    if args.command == "list":
        return cmd_list(store)
    if args.command == "done":
        code, changed = cmd_done(store, args.id)
        if changed:
            save_store(path, store)
        return code
    fail(f"unknown command: {args.command}", EXIT_ERROR)
    return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
