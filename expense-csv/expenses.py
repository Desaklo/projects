#!/usr/bin/env python3
"""Track personal expenses in a CSV file next to this script."""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import NoReturn

DEFAULT_FILE = Path(__file__).resolve().parent / "expenses.csv"
FIELDS = ("date", "amount", "category", "note")
RECENT_LIMIT = 10
CENTS = Decimal("0.01")

EXIT_OK = 0
EXIT_USER = 1
EXIT_ERROR = 2

_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_ISO_MONTH = re.compile(r"\d{4}-\d{2}")
_AMOUNT = re.compile(r"-?\d+(\.\d+)?")


class InputError(ValueError):
    """A date, amount, or text field the user (or the CSV) supplied is invalid."""


@dataclass(frozen=True)
class Expense:
    when: date
    amount: Decimal
    category: str
    note: str


def fail(message: str, code: int) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def money(amount: Decimal) -> str:
    return f"{amount:.2f}"


def count_label(amount: int, singular: str, plural: str) -> str:
    word = singular if amount == 1 else plural
    return f"{amount} {word}"


def parse_date(raw: str) -> date:
    text = raw.strip()
    if not _ISO_DATE.fullmatch(text):
        raise InputError(f"date must be YYYY-MM-DD, got {raw!r}")
    year, month, day = (int(part) for part in text.split("-"))
    try:
        return date(year, month, day)
    except ValueError:
        raise InputError(f"date must be YYYY-MM-DD, got {raw!r}") from None


def parse_month(raw: str) -> tuple[date, date]:
    text = raw.strip()
    if not _ISO_MONTH.fullmatch(text):
        raise InputError(f"month must be YYYY-MM, got {raw!r}")
    year, month = (int(part) for part in text.split("-"))
    try:
        start = date(year, month, 1)
    except ValueError:
        raise InputError(f"month must be YYYY-MM, got {raw!r}") from None
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return start, next_month - timedelta(days=1)


def parse_amount(raw: str) -> Decimal:
    text = raw.strip().replace("\u00a0", "")
    if not text:
        raise InputError("amount is empty")
    if any(ch.isspace() for ch in text):
        raise InputError(
            f"amount must not contain spaces, got {raw!r} (write 1200.50 or 1200,50)"
        )
    if "," in text and "." in text:
        raise InputError(
            f"use either a dot or a comma as the decimal separator, got {raw!r}"
        )
    normalized = text.replace(",", ".")
    if normalized.startswith("+"):
        normalized = normalized[1:]
    if not _AMOUNT.fullmatch(normalized):
        raise InputError(f"amount must be a number, got {raw!r}")
    value = Decimal(normalized)
    if not value.is_finite():
        raise InputError(f"amount must be a number, got {raw!r}")
    exponent = value.as_tuple().exponent
    if isinstance(exponent, int) and exponent < -2:
        raise InputError(f"amount must have at most 2 decimal places, got {raw!r}")
    if value <= 0:
        raise InputError(f"amount must be greater than zero, got {raw!r}")
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)


def normalize_field(raw: str, label: str, allow_empty: bool) -> str:
    if "\n" in raw or "\r" in raw:
        raise InputError(f"{label} must be a single line")
    text = raw.strip()
    if not text and not allow_empty:
        raise InputError(f"{label} is empty")
    return text


def load_expenses(path: Path) -> list[Expense]:
    if not path.exists():
        return []
    if not path.is_file():
        fail(f"not a file: {path}", EXIT_ERROR)
    try:
        handle = path.open(encoding="utf-8-sig", newline="")
    except OSError as exc:
        fail(f"cannot read {path}: {exc}", EXIT_ERROR)
    with handle:
        try:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames
            parsed: list[Expense] = []
            if fieldnames is None:
                return []
            if any(not isinstance(name, str) for name in fieldnames):
                fail(f"{path} must have header: {','.join(FIELDS)}", EXIT_ERROR)
            header = [name.strip() for name in fieldnames]
            if header != list(FIELDS):
                fail(f"{path} must have header: {','.join(FIELDS)}", EXIT_ERROR)
            # DictReader keeps the raw header text as keys. Replace it so
            # "date, amount, category, note" still maps onto the four fields.
            reader.fieldnames = header
            for row in reader:
                if _blank_row(row):
                    continue
                parsed.append(_parse_row(path, reader.line_num, row))
        except csv.Error as exc:
            fail(f"{path} is not valid CSV ({exc})", EXIT_ERROR)
        except UnicodeDecodeError:
            fail(f"{path} is not valid UTF-8", EXIT_ERROR)
    return parsed


def _has_extra(row: dict) -> bool:
    extra = row.get(None) or []
    return any(item is not None and str(item).strip() != "" for item in extra)


def _blank_row(row: dict) -> bool:
    if _has_extra(row):
        return False
    for name in FIELDS:
        value = row.get(name)
        if value is not None and str(value).strip() != "":
            return False
    return True


def _parse_row(path: Path, line_no: int, row: dict) -> Expense:
    if _has_extra(row):
        fail(f"{path}: line {line_no} has extra columns", EXIT_ERROR)
    try:
        raw_date = row.get("date")
        raw_amount = row.get("amount")
        raw_category = row.get("category")
        if raw_date is None or raw_amount is None or raw_category is None:
            raise InputError("row must include date, amount, and category")
        raw_note = row.get("note")
        if raw_note is None:
            raw_note = ""
        return Expense(
            when=parse_date(raw_date),
            amount=parse_amount(raw_amount),
            category=normalize_field(raw_category, "category", allow_empty=False),
            note=normalize_field(raw_note, "note", allow_empty=True),
        )
    except InputError as exc:
        fail(f"{path}: line {line_no}: {exc}", EXIT_ERROR)


def save_expenses(path: Path, rows: list[Expense]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        fail(f"cannot create {path.parent}: {exc}", EXIT_ERROR)

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            prefix=".expenses-",
            suffix=".tmp",
            delete=False,
        ) as tmp:
            writer = csv.DictWriter(tmp, fieldnames=FIELDS, lineterminator="\n")
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        "date": row.when.isoformat(),
                        "amount": money(row.amount),
                        "category": row.category,
                        "note": row.note,
                    }
                )
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


def newest_first(rows: list[Expense]) -> list[Expense]:
    indexed = sorted(
        enumerate(rows),
        key=lambda pair: (pair[1].when, pair[0]),
        reverse=True,
    )
    return [row for _index, row in indexed]


def format_expense(row: Expense) -> str:
    text = f"{row.when.isoformat()}  {money(row.amount)}  {row.category}"
    if row.note:
        text += f"  {row.note}"
    return text


def print_rows(rows: list[Expense]) -> None:
    amount_width = max(len(money(row.amount)) for row in rows)
    category_width = max(len(row.category) for row in rows)
    for row in rows:
        base = (
            f"{row.when.isoformat()}  "
            f"{money(row.amount).rjust(amount_width)}  "
            f"{row.category.ljust(category_width)}"
        )
        if row.note:
            print(f"{base}  {row.note}")
        else:
            print(base.rstrip())


def within(when: date, start: date | None, end: date | None) -> bool:
    if start is not None and when < start:
        return False
    if end is not None and when > end:
        return False
    return True


def scope_label(start: date | None, end: date | None) -> str:
    if start is not None and end is not None:
        return f"{start.isoformat()} to {end.isoformat()}"
    if start is not None:
        return f"from {start.isoformat()}"
    if end is not None:
        return f"through {end.isoformat()}"
    return "all expenses"


def cmd_add(path: Path, args: argparse.Namespace) -> int:
    note_words = " ".join(args.note_words).strip()
    if note_words and args.note is not None:
        print(
            "error: pass the note as extra words or as --note, not both",
            file=sys.stderr,
        )
        return EXIT_ERROR
    note_raw = args.note if args.note is not None else note_words
    try:
        amount = parse_amount(args.amount)
        category = normalize_field(args.category, "category", allow_empty=False)
        note = normalize_field(note_raw, "note", allow_empty=True)
        when = date.today() if args.date is None else parse_date(args.date)
    except InputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USER

    rows = load_expenses(path)
    rows.append(Expense(when=when, amount=amount, category=category, note=note))
    save_expenses(path, rows)
    print(f"Added {format_expense(rows[-1])}")
    return EXIT_OK


def cmd_list(rows: list[Expense], show_all: bool, limit: int | None) -> int:
    if limit is not None and limit < 1:
        print("error: --limit must be at least 1", file=sys.stderr)
        return EXIT_USER
    if not rows:
        print('No expenses yet. Add one with: expenses.py add 12.50 food')
        return EXIT_OK

    ordered = newest_first(rows)
    shown = ordered if show_all else ordered[: RECENT_LIMIT if limit is None else limit]
    print_rows(shown)
    shown_total = sum((row.amount for row in shown), Decimal("0.00"))
    if len(shown) == len(rows):
        footer = (
            f"{count_label(len(shown), 'expense', 'expenses')}, "
            f"{money(shown_total)} total"
        )
    else:
        footer = (
            f"{len(shown)} of {count_label(len(rows), 'expense', 'expenses')}, "
            f"{money(shown_total)} shown. Use --all to see every row."
        )
    print(f"\n{footer}")
    return EXIT_OK


def cmd_summary(
    rows: list[Expense],
    month: str | None,
    start_raw: str | None,
    end_raw: str | None,
) -> int:
    if month and (start_raw or end_raw):
        print(
            "error: use either --month or --from/--to, not both",
            file=sys.stderr,
        )
        return EXIT_ERROR
    try:
        if month:
            start, end = parse_month(month)
            label = f"month {month.strip()}"
        else:
            start = parse_date(start_raw) if start_raw else None
            end = parse_date(end_raw) if end_raw else None
            if start is not None and end is not None and start > end:
                print(
                    f"error: --from {start.isoformat()} is after --to {end.isoformat()}",
                    file=sys.stderr,
                )
                return EXIT_USER
            label = scope_label(start, end)
    except InputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USER

    selected = [row for row in rows if within(row.when, start, end)]
    print(label)
    if not selected:
        print("\nNo expenses.")
        return EXIT_OK

    totals: dict[str, Decimal] = {}
    for row in selected:
        totals[row.category] = totals.get(row.category, Decimal("0.00")) + row.amount
    ordered = sorted(
        totals.items(),
        key=lambda item: (-item[1], item[0].casefold(), item[0]),
    )
    grand = sum((row.amount for row in selected), Decimal("0.00"))
    labels = [name for name, _total in ordered]
    label_width = max(len("total"), *(len(name) for name in labels))
    amount_text = [money(total) for _name, total in ordered]
    amount_text.append(money(grand))
    amount_width = max(len(item) for item in amount_text)

    print()
    for name, total_text in zip(labels, amount_text):
        print(f"{name.ljust(label_width)}  {total_text.rjust(amount_width)}")
    print()
    print(f"{'total'.ljust(label_width)}  {amount_text[-1].rjust(amount_width)}")
    print(count_label(len(selected), "expense", "expenses"))
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    file_help = "CSV file (default: expenses.csv next to this script)"
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
        prog="expenses.py",
        description="Track personal expenses in a local CSV file.",
        epilog=(
            "examples:\n"
            "  expenses.py add 12.50 food lunch\n"
            "  expenses.py add --date 2026-11-01 40 transport --note metro\n"
            "  expenses.py list\n"
            "  expenses.py list --all\n"
            "  expenses.py summary --month 2026-11\n"
            "  expenses.py summary --from 2026-11-01 --to 2026-11-30\n"
            "\n"
            "amounts use a dot or a comma (12.50 or 12,50) and no currency symbol.\n"
            "dates are YYYY-MM-DD. add uses today's local date when --date is omitted.\n"
            "list shows the 10 newest rows unless you pass --all or --limit.\n"
            "\n"
            "exit codes:\n"
            "  0  success (an empty list or summary is still success)\n"
            "  1  user error (bad amount, empty category, bad date or month)\n"
            "  2  bad usage, or the CSV cannot be read or written"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[common],
    )
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser(
        "add",
        parents=[sub_common],
        help="record one expense",
        description="Append one expense. The date defaults to today.",
    )
    add.add_argument("amount", help="positive number, such as 12.50 or 12,50")
    add.add_argument("category", help="category name, matched exactly")
    add.add_argument(
        "note_words",
        nargs="*",
        metavar="NOTE",
        help="optional note (separate words are joined)",
    )
    add.add_argument("--date", help="YYYY-MM-DD (default: today, local time)")
    add.add_argument("--note", help="optional note, instead of extra words")

    listing = sub.add_parser(
        "list",
        parents=[sub_common],
        help="show recent expenses, or all of them",
        description="Show the newest expenses. The default is 10 rows.",
    )
    window = listing.add_mutually_exclusive_group()
    window.add_argument("--all", action="store_true", help="show every expense")
    window.add_argument(
        "--limit",
        type=int,
        help=f"how many of the newest expenses to show (default: {RECENT_LIMIT})",
    )

    summary = sub.add_parser(
        "summary",
        parents=[sub_common],
        help="total amounts by category",
        description="Print one total per category, then the overall total.",
    )
    summary.add_argument("--month", help="only this calendar month (YYYY-MM)")
    summary.add_argument(
        "--from",
        dest="start",
        help="include expenses on or after this date (YYYY-MM-DD)",
    )
    summary.add_argument(
        "--to",
        dest="end",
        help="include expenses on or before this date (YYYY-MM-DD)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = args.file.expanduser()
    if args.command == "add":
        return cmd_add(path, args)
    rows = load_expenses(path)
    if args.command == "list":
        return cmd_list(rows, args.all, args.limit)
    if args.command == "summary":
        return cmd_summary(rows, args.month, args.start, args.end)
    fail(f"unknown command: {args.command}", EXIT_ERROR)
    return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
