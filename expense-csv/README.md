# expense-csv

Небольшой учёт личных расходов в терминале. Каждая запись — дата, сумма, категория и необязательная заметка. Данные лежат в CSV рядом со скриптом.

A small command-line expense tracker. Each row is a date, an amount, a category, and an optional note. The data lives in a CSV file next to the script.

Нужен только Python 3.9+ из стандартной библиотеки — ставить зависимости не нужно.

Python 3.9+ from the standard library is enough. There is nothing to install.

## Как запустить / How to run

Из папки проекта / from this folder:

```bash
cd expense-csv
python3 expenses.py --help
```

Из корня репозитория / from the repo root (файл данных всё равно будет `expense-csv/expenses.csv`):

```bash
python3 expense-csv/expenses.py --help
```

Свой файл / custom CSV (`--file` можно ставить до или после команды):

```bash
python3 expenses.py --file ~/my-expenses.csv list
python3 expenses.py summary --month 2026-11 --file ~/my-expenses.csv
```

## Примеры / Examples

```bash
python3 expenses.py add 12.50 food обед
python3 expenses.py add --date 2026-11-01 40 transport --note метро
python3 expenses.py add 89,00 transport метро
python3 expenses.py list
python3 expenses.py list --limit 5
python3 expenses.py list --all
python3 expenses.py summary
python3 expenses.py summary --month 2026-11
python3 expenses.py summary --from 2026-11-01 --to 2026-11-30
```

`add` без `--date` берёт сегодняшний день по местному времени. Слова после категории складываются в одну заметку. Тот же текст можно передать флагом `--note`.

Without `--date`, `add` uses today's local date. Words after the category are joined into one note. `--note` accepts that text as a single argument instead.

Подтверждение `add` / what `add` prints:

```text
Added 2026-11-01  40.00  transport  метро
```

Сумма — число больше нуля, максимум два знака после запятой, без валюты и без разделителя тысяч. Десятичный знак — точка или запятая: `12.50` и `12,50` — одно и то же.

An amount is a number greater than zero, with at most two decimal places, no currency symbol, and no thousands separator. A dot or a comma is the decimal mark: `12.50` and `12,50` are the same amount.

Категория записывается так, как вы её ввели: `food` и `Food` — разные категории.

A category is stored as you typed it: `food` and `Food` are different categories.

`list` по умолчанию показывает 10 последних записей, самые новые сверху. `--all` печатает все, `--limit N` — только N последних. Если часть строк скрыта, внизу написано, сколько их всего.

`list` shows the 10 newest rows, newest first. `--all` prints every row, and `--limit N` prints N of them. When some rows are hidden, the footer says how many exist.

Пустой список и пустая сводка — это не ошибка, код выхода 0.

An empty list or an empty summary is not an error; the exit code is still 0.

Пример `list` по файлу-образцу / sample `list` (`python3 expenses.py --file expenses.sample.csv list`):

```text
2026-11-04   60.00  transport  такси
2026-11-02  320.00  groceries  овощи и хлеб
2026-10-28   15.50  food       кофе, круассан
2026-10-12   89.00  transport  метро
2026-10-03  450.00  groceries  продукты на неделю

5 expenses, 934.50 total
```

Пример сводки / sample summary (`python3 expenses.py --file expenses.sample.csv summary`):

```text
all expenses

groceries  770.00
transport  149.00
food        15.50

total      934.50
5 expenses
```

Тот же файл за ноябрь / the same file for November (`summary --month 2026-11`):

```text
month 2026-11

groceries  320.00
transport   60.00

total      380.00
2 expenses
```

## Команды / Commands

| Команда / Command | Что делает / What it does |
| --- | --- |
| `add <сумма> <категория> [заметка...]` | Добавить расход. Дата — сегодня, если нет `--date` |
| `list` | Показать 10 последних расходов |
| `list --all` | Показать все расходы |
| `list --limit N` | Показать N последних |
| `summary` | Суммы по категориям и общий итог |
| `summary --month YYYY-MM` | Сводка за один календарный месяц |
| `summary --from YYYY-MM-DD` | Расходы в эту дату и позже |
| `summary --to YYYY-MM-DD` | Расходы в эту дату и раньше |
| `--file <путь>` | Другой CSV вместо `expenses.csv` рядом со скриптом |
| `--help` | Справка по программе или подкоманде |

`--from` и `--to` можно указать вместе: обе границы входят в диапазон. `--month` с ними сочетать нельзя.

`--from` and `--to` can be used together. Both ends are inclusive. `--month` cannot be combined with them.

## Файл данных / Data file

`expenses.csv` создаётся при первой команде `add` и указан в `.gitignore`, чтобы личные суммы не попали в git. Кодировка — UTF-8. Заголовок фиксированный:

`expenses.csv` is created on the first `add` and is listed in `.gitignore`, so personal amounts stay out of git. The encoding is UTF-8. The header is fixed:

```text
date,amount,category,note
```

`expenses.sample.csv` — короткий пример за октябрь и ноябрь 2026. Его можно читать и не создавать свой файл:

`expenses.sample.csv` is a short example covering October and November 2026. You can read it without creating your own file:

```bash
python3 expenses.py --file expenses.sample.csv list
python3 expenses.py --file expenses.sample.csv summary --month 2026-10
```

Из корня репозитория путь к образцу другой, потому что `--file` считается от текущей папки, а не от скрипта:

From the repo root the sample path is different, because `--file` is relative to the current directory, not to the script:

```bash
python3 expense-csv/expenses.py --file expense-csv/expenses.sample.csv summary
```

Не записывайте свои расходы в файл-образец: `add --file expenses.sample.csv` изменит его.

Don't record your own expenses into the sample: `add --file expenses.sample.csv` would change that file.

Если в CSV другая шапка или испорченная строка, команда завершится с кодом 2 и не перезапишет файл.

If the CSV header is different or a row is invalid, the command exits 2 and leaves the file unchanged.

## Коды выхода / Exit codes

| Код | Значение / Meaning |
| --- | --- |
| 0 | Успех, в том числе пустой список или сводка без строк |
| 1 | Ошибка пользователя: сумма не число или не больше нуля, больше двух знаков, пустая категория, дата или месяц не в формате, `--from` позже `--to`, `--limit` меньше 1 |
| 2 | Неверные аргументы (например, `--month` вместе с диапазоном или заметка сразу и словами, и через `--note`), или CSV нельзя прочитать или записать |
