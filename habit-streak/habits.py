#!/usr/bin/env python3
"""A small command-line habit streak tracker. Check-ins persist in a local JSON file."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

DEFAULT_FILE = Path(__file__).resolve().parent / "habits.json"

EXIT_OK = 0
EXIT_USER = 1
EXIT_ERROR = 2


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def fail(message: str, code: int) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def parse_iso_date(value: str) -> date:
    """Parse a calendar day. Only YYYY-MM-DD is accepted."""
    if len(value) != 10 or value[4] != "-" or value[7] != "-":
        raise ValueError(value)
    try:
        year = int(value[0:4])
        month = int(value[5:7])
        day = int(value[8:10])
        return date(year, month, day)
    except ValueError as exc:
        raise ValueError(value) from exc


def iso_date_arg(value: str) -> date:
    try:
        return parse_iso_date(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"not an ISO date (YYYY-MM-DD): {value}"
        ) from None


def day_phrase(count: int) -> str:
    return "1 day" if count == 1 else f"{count} days"


def checkin_dates(habit: dict) -> list[date]:
    days: list[date] = []
    seen: set[date] = set()
    for raw in habit["checkins"]:
        day = parse_iso_date(raw)
        if day not in seen:
            seen.add(day)
            days.append(day)
    days.sort()
    return days


def current_streak(days: list[date], today: date) -> int:
    """Consecutive days ending today or yesterday. Older chains count as broken."""
    eligible = [day for day in days if day <= today]
    if not eligible:
        return 0
    last = eligible[-1]
    if (today - last).days > 1:
        return 0
    have = set(eligible)
    streak = 1
    cursor = last
    while (cursor - timedelta(days=1)) in have:
        cursor -= timedelta(days=1)
        streak += 1
    return streak


def best_streak(days: list[date]) -> int:
    if not days:
        return 0
    best = 1
    run = 1
    for prev, cur in zip(days, days[1:]):
        gap = (cur - prev).days
        if gap == 1:
            run += 1
            if run > best:
                best = run
        elif gap > 1:
            run = 1
    return best


def load_store(path: Path) -> dict:
    if not path.exists():
        return {"version": 1, "next_id": 1, "habits": []}
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        fail(f"cannot read {path}: {exc}", EXIT_ERROR)
    if not raw.strip():
        return {"version": 1, "next_id": 1, "habits": []}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        fail(f"{path} is not valid JSON ({exc})", EXIT_ERROR)
    if not isinstance(data, dict) or not isinstance(data.get("habits"), list):
        fail(f"{path} has an unexpected format", EXIT_ERROR)

    ids: list[int] = []
    seen_ids: set[int] = set()
    for item in data["habits"]:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("id"), int)
            or isinstance(item.get("id"), bool)
            or not isinstance(item.get("name"), str)
            or not item["name"].strip()
            or not isinstance(item.get("checkins"), list)
        ):
            fail(f"{path} has an unexpected format", EXIT_ERROR)
        if item["id"] in seen_ids:
            fail(f"{path} has an unexpected format", EXIT_ERROR)
        seen_ids.add(item["id"])
        item["name"] = item["name"].strip()
        if not isinstance(item.get("created_at"), str):
            item["created_at"] = ""
        normalized: list[str] = []
        seen_days: set[str] = set()
        for raw_day in item["checkins"]:
            if not isinstance(raw_day, str):
                fail(f"{path} has an unexpected format", EXIT_ERROR)
            try:
                parsed = parse_iso_date(raw_day)
            except ValueError:
                fail(f"{path} has an unexpected format", EXIT_ERROR)
            iso = parsed.isoformat()
            if iso not in seen_days:
                seen_days.add(iso)
                normalized.append(iso)
        normalized.sort()
        item["checkins"] = normalized
        ids.append(item["id"])

    next_id = data.get("next_id", 1)
    if not isinstance(next_id, int) or isinstance(next_id, bool) or next_id < 1:
        next_id = 1
    if ids:
        next_id = max(next_id, max(ids) + 1)
    data["version"] = 1
    data["next_id"] = next_id
    return data


def save_store(path: Path, data: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        fail(f"cannot create {path.parent}: {exc}", EXIT_ERROR)

    payload = {
        "version": 1,
        "next_id": data["next_id"],
        "habits": data["habits"],
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=".habits-",
            suffix=".tmp",
            delete=False,
        ) as tmp:
            tmp.write(text)
            tmp_path = Path(tmp.name)
        tmp_path.replace(path)
    except OSError as exc:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
        fail(f"cannot write {path}: {exc}", EXIT_ERROR)


def find_habit(store: dict, habit_id: int) -> dict | None:
    for habit in store["habits"]:
        if habit["id"] == habit_id:
            return habit
    return None


def streak_summary(habit: dict, today: date) -> tuple[int, int, bool]:
    days = checkin_dates(habit)
    current = current_streak(days, today)
    best = best_streak(days)
    checked_today = today in days
    return current, best, checked_today


def cmd_add(store: dict, words: list[str]) -> int:
    name = " ".join(words).strip()
    if not name:
        print("error: habit name is empty", file=sys.stderr)
        return EXIT_USER
    habit = {
        "id": store["next_id"],
        "name": name,
        "created_at": utc_now(),
        "checkins": [],
    }
    store["next_id"] += 1
    store["habits"].append(habit)
    print(f"Added #{habit['id']}: {habit['name']}")
    return EXIT_OK


def cmd_list(store: dict, today: date) -> int:
    habits = store["habits"]
    if not habits:
        print('No habits yet. Add one with: habits.py add "drink water"')
        return EXIT_OK

    checked_today = 0
    for habit in habits:
        current, best, done_today = streak_summary(habit, today)
        if done_today:
            checked_today += 1
            when = "checked in today"
        elif current > 0:
            when = "not checked in today"
        elif habit["checkins"]:
            when = f"last {habit['checkins'][-1]}"
        else:
            when = "no check-ins yet"
        print(f"{habit['id']}  {habit['name']}")
        print(
            f"     streak {day_phrase(current)} (best {day_phrase(best)})  {when}"
        )

    habit_word = "habit" if len(habits) == 1 else "habits"
    print(f"\n{len(habits)} {habit_word}, {checked_today} checked in today")
    return EXIT_OK


def cmd_checkin(habit: dict, day: date, today: date) -> tuple[int, bool]:
    dates = checkin_dates(habit)
    iso = day.isoformat()
    if day in dates:
        current = current_streak(dates, today)
        best = best_streak(dates)
        print(
            f"Already checked in #{habit['id']} {habit['name']} for {iso}"
            f" — streak {day_phrase(current)}, best {day_phrase(best)}"
        )
        return EXIT_OK, False

    dates.append(day)
    dates.sort()
    habit["checkins"] = [item.isoformat() for item in dates]
    current = current_streak(dates, today)
    best = best_streak(dates)
    print(
        f"Checked in #{habit['id']} {habit['name']} for {iso}"
        f" — streak {day_phrase(current)}, best {day_phrase(best)}"
    )
    return EXIT_OK, True


def cmd_reset(habit: dict) -> tuple[int, bool]:
    if not habit["checkins"]:
        print(f"Already clear: #{habit['id']} {habit['name']}")
        return EXIT_OK, False
    count = len(habit["checkins"])
    habit["checkins"] = []
    print(f"Reset #{habit['id']} {habit['name']} — cleared {count} check-ins")
    return EXIT_OK, True


def cmd_remove(store: dict, habit: dict) -> int:
    store["habits"] = [item for item in store["habits"] if item["id"] != habit["id"]]
    print(f"Removed #{habit['id']}: {habit['name']}")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="habits.py",
        description=(
            "Track habit streaks from the terminal. "
            "Check-ins are stored in a local JSON file."
        ),
        epilog=(
            "examples:\n"
            '  habits.py add "Drink water"\n'
            "  habits.py checkin 1\n"
            "  habits.py list\n"
            "  habits.py reset 1\n"
            "\n"
            "done is an alias of checkin. status is an alias of list.\n"
            "A streak stays alive through today if the last check-in was yesterday.\n"
            "\n"
            "exit codes:\n"
            "  0  success\n"
            "  1  user error (empty name, unknown id, future date)\n"
            "  2  bad usage, or the data file cannot be read or written"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_FILE,
        help=f"path to the habits file (default: {DEFAULT_FILE.name} next to this script)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="add a habit")
    add.add_argument("name", nargs="+", help="habit name")

    checkin = sub.add_parser(
        "checkin",
        aliases=["done"],
        help="record a check-in (alias: done)",
    )
    checkin.add_argument("id", type=int, help="id of the habit")
    checkin.add_argument(
        "--date",
        type=iso_date_arg,
        default=None,
        help="calendar day to record (YYYY-MM-DD). Default: today, local time",
    )

    sub.add_parser(
        "list",
        aliases=["status"],
        help="show each habit's current and best streak (alias: status)",
    )

    reset = sub.add_parser("reset", help="clear one habit's check-ins")
    reset.add_argument("id", type=int, help="id of the habit")

    remove = sub.add_parser("remove", help="delete a habit")
    remove.add_argument("id", type=int, help="id of the habit")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = args.file.expanduser()
    store = load_store(path)
    today = date.today()

    if args.command in ("list", "status"):
        return cmd_list(store, today)

    if args.command == "add":
        code = cmd_add(store, args.name)
        if code == EXIT_OK:
            save_store(path, store)
        return code

    if args.command in ("checkin", "done", "reset", "remove"):
        habit = find_habit(store, args.id)
        if habit is None:
            print(f"error: no habit with id {args.id}", file=sys.stderr)
            return EXIT_USER

        if args.command in ("checkin", "done"):
            day = today if args.date is None else args.date
            if day > today:
                print(
                    f"error: check-in date {day.isoformat()} is in the future",
                    file=sys.stderr,
                )
                return EXIT_USER
            code, changed = cmd_checkin(habit, day, today)
        elif args.command == "reset":
            code, changed = cmd_reset(habit)
        else:
            code = cmd_remove(store, habit)
            changed = code == EXIT_OK

        if changed:
            save_store(path, store)
        return code

    fail(f"unknown command: {args.command}", EXIT_ERROR)
    return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
