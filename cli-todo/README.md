# cli-todo

Небольшой список дел в терминале. Задачи пишутся в `todos.json` рядом со скриптом и сохраняются между запусками.

A small command-line todo list. Tasks are stored in `todos.json` next to the script and survive restarts.

Нужен только Python 3.9+ из стандартной библиотеки — ставить зависимости не нужно.

Python 3.9+ from the standard library is enough. There is nothing to install.

## Как запустить / How to run

Из папки проекта / from this folder:

```bash
cd cli-todo
python3 todo.py --help
```

Из корня репозитория / from the repo root (файл данных всё равно будет `cli-todo/todos.json`):

```bash
python3 cli-todo/todo.py --help
```

Свой путь к файлу / custom data file:

```bash
python3 todo.py --file ~/my-todos.json list
```

## Примеры / Examples

```bash
python3 todo.py add "Купить молоко"
python3 todo.py add "Написать отчёт"
python3 todo.py list
python3 todo.py done 1
python3 todo.py list
```

`add` можно вызывать и без кавычек: слова собираются в один текст.

`add` also accepts separate words and joins them: `python3 todo.py add Buy milk`.

Пример вывода `list` / sample `list` output:

```text
1  [x]  Купить молоко
2  [ ]  Написать отчёт

1 open, 1 done
```

Повторный `done` для уже выполненной задачи ничего не меняет и завершается с кодом 0.

Running `done` again on a finished task leaves the file unchanged and exits 0.

## Команды / Commands

| Команда / Command | Что делает / What it does |
| --- | --- |
| `add <текст>` | Добавить задачу и напечатать её id |
| `list` | Показать все задачи: `[ ]` открыта, `[x]` выполнена |
| `done <id>` | Отметить задачу выполненной |
| `--help` | Справка по команде или подкоманде |

## Коды выхода / Exit codes

| Код | Значение / Meaning |
| --- | --- |
| 0 | Успех / success |
| 1 | Ошибка пользователя: пустой текст или неизвестный id |
| 2 | Неверные аргументы, или файл данных нельзя прочитать или записать |

`todos.json` создаётся при первой записи и указан в `.gitignore`.
