# habit-streak

Небольшой трекер привычек в терминале. Отметки за дни пишутся в `habits.json` рядом со скриптом и сохраняются между запусками.

A small command-line habit streak tracker. Check-ins are stored in `habits.json` next to the script and survive restarts.

Нужен только Python 3.9+ из стандартной библиотеки — ставить зависимости не нужно.

Python 3.9+ from the standard library is enough. There is nothing to install.

## Как запустить / How to run

Из папки проекта / from this folder:

```bash
cd habit-streak
python3 habits.py --help
```

Из корня репозитория / from the repo root (файл данных всё равно будет `habit-streak/habits.json`):

```bash
python3 habit-streak/habits.py --help
```

Свой путь к файлу / custom data file:

```bash
python3 habits.py --file ~/my-habits.json list
```

## Примеры / Examples

```bash
python3 habits.py add "Drink water"
python3 habits.py add "Read 10 pages"
python3 habits.py checkin 1
python3 habits.py done 2
python3 habits.py list
python3 habits.py status
python3 habits.py reset 1
python3 habits.py remove 2
```

`add` можно вызывать и без кавычек: слова собираются в одно название.

`add` also accepts separate words and joins them: `python3 habits.py add Drink water`.

`done` — то же, что `checkin`. `status` — то же, что `list`.

`done` is an alias of `checkin`. `status` is an alias of `list`.

Повторный `checkin` за тот же день ничего не меняет и завершается с кодом 0.

Running `checkin` again for the same day leaves the file unchanged and exits 0.

Отметить прошедший день / record a past day:

```bash
python3 habits.py checkin 1 --date 2026-11-06
```

Пример вывода `list` / sample `list` output:

```text
1  Drink water
     streak 3 days (best 5 days)  checked in today
2  Read 10 pages
     streak 2 days (best 4 days)  not checked in today

2 habits, 1 checked in today
```

## Как считается серия / Streak rules

День считается по локальному календарю. Текущая серия — это подряд идущие дни, которые заканчиваются сегодня или вчера. Если последняя отметка старше, чем вчера, текущая серия равна 0, а лучшая серия остаётся в истории. `reset` очищает все отметки привычки, поэтому и текущая, и лучшая серии становятся 0.

Days follow the local calendar. The current streak is the run of consecutive check-ins ending today or yesterday. If the latest check-in is older than yesterday, the current streak is 0 and the best streak stays as history. `reset` deletes that habit's check-ins, so both the current streak and the best streak go back to 0.

## Команды / Commands

| Команда / Command | Что делает / What it does |
| --- | --- |
| `add <название>` | Добавить привычку и напечатать её id |
| `checkin <id>` / `done <id>` | Отметить день. По умолчанию сегодня; `--date YYYY-MM-DD` — другой день |
| `list` / `status` | Показать текущую и лучшую серию каждой привычки |
| `reset <id>` | Очистить отметки привычки |
| `remove <id>` | Удалить привычку |
| `--help` | Справка по команде или подкоманде |

## Коды выхода / Exit codes

| Код | Значение / Meaning |
| --- | --- |
| 0 | Успех / success |
| 1 | Ошибка пользователя: пустое название, неизвестный id или дата в будущем |
| 2 | Неверные аргументы, или файл данных нельзя прочитать или записать |

## Файл данных / Data file

`habits.json` создаётся при первой записи и указан в `.gitignore`. Формат — JSON:

```json
{
  "version": 1,
  "next_id": 2,
  "habits": [
    {
      "id": 1,
      "name": "Drink water",
      "created_at": "2026-11-07T06:00:00+00:00",
      "checkins": ["2026-11-05", "2026-11-06", "2026-11-07"]
    }
  ]
}
```

`checkins` — список календарных дней `YYYY-MM-DD`. Серии каждый раз считаются из этого списка.
