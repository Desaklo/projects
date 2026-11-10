# markdown-notes

Небольшая программа для локальных заметок в Markdown. Она показывает файлы `.md` в папке, открывает одну заметку по имени и ищет текст.

A small viewer for local Markdown notes. It lists `.md` files in a folder, opens one note by name, and searches the text.

Нужен только Python 3.9+ из стандартной библиотеки — ставить зависимости не нужно.

Python 3.9+ from the standard library is enough. There is nothing to install.

## Как запустить / How to run

Из папки проекта / from this folder:

```bash
cd markdown-notes
python3 notes.py --help
```

Из корня репозитория / from the repo root (заметки всё равно читаются из `markdown-notes/notes`):

```bash
python3 markdown-notes/notes.py list
```

Своя папка с заметками / custom notes directory (`--dir` можно ставить до или после команды):

```bash
python3 notes.py --dir ~/notes list
python3 notes.py search meeting --dir ~/notes
```

## Примеры / Examples

```bash
python3 notes.py list
python3 notes.py show welcome
python3 notes.py show ideas
python3 notes.py search pathlib
python3 notes.py search закваск
python3 notes.py search --case-sensitive Python
```

`show` принимает имя файла с суффиксом `.md` и без него. Хватает уникального начала имени: `show wel` откроет `welcome.md`.

`show` accepts the file name with or without `.md`. A unique prefix works too: `show wel` opens `welcome.md`.

`search` ищет точную подстроку без регулярных выражений и по умолчанию не учитывает регистр. Слова можно писать без кавычек — они собираются в одну фразу: `search кормить через`.

`search` looks for a literal substring, not a regular expression, and ignores case unless you pass `--case-sensitive`. Separate words are joined into one phrase: `python3 notes.py search кормить через`.

Пример вывода `list` / sample `list` output:

```text
ideas.md    Идеи на неделю
welcome.md  Welcome

2 notes
```

Пример вывода `search pathlib` / sample `search pathlib` output:

```text
ideas.md:3: - Дописать конспект по Python: списки, словари и pathlib.

1 match in 1 note
```

Если совпадений нет, программа печатает `No matches for ...` и всё равно завершается с кодом 0.

When nothing matches, the program prints `No matches for ...` and still exits 0.

## Команды / Commands

| Команда / Command | Что делает / What it does |
| --- | --- |
| `list` | Показать все `.md` в папке и заголовок каждой заметки |
| `show <имя>` | Напечатать заметку |
| `search <текст>` | Найти строки, где встречается этот текст |
| `--dir <папка>` | Другая папка вместо `notes` рядом со скриптом |
| `--case-sensitive` | Учитывать регистр в `search` |
| `--help` | Справка по программе или подкоманде |

Заголовок для `list` — первая строка с `#`. Если её нет, берётся первая непустая строка.

The title shown by `list` is the first Markdown heading. If a note has none, the first non-empty line is used.

## Какие файлы видны / Which files are included

Читается только верхний уровень папки: обычные файлы с расширением `.md`. Вложенные папки и скрытые файлы (имя начинается с точки) пропускаются.

Only the top level of the notes directory is read: regular files ending in `.md`. Subfolders and hidden files (names starting with `.`) are skipped.

## Коды выхода / Exit codes

| Код | Значение / Meaning |
| --- | --- |
| 0 | Успех, в том числе поиск без совпадений |
| 1 | Ошибка пользователя: пустой запрос, неизвестное или неоднозначное имя |
| 2 | Неверные аргументы, или папку заметок нельзя прочитать |

В папке `notes/` лежат два примера: `welcome.md` и `ideas.md`. Их можно править или заменить своими файлами.

`notes/` contains two examples, `welcome.md` and `ideas.md`. Edit them or replace them with your own files.
