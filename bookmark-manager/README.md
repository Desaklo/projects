# bookmark-manager

Небольшой менеджер закладок в терминале. Ссылки хранятся в `bookmarks.json` рядом со скриптом и сохраняются между запусками.

A small command-line bookmark manager. URLs are stored in `bookmarks.json` next to the script and survive restarts.

Нужен только Python 3.9+ из стандартной библиотеки — ставить зависимости не нужно.

Python 3.9+ from the standard library is enough. There is nothing to install.

## Как запустить / How to run

Из папки проекта / from this folder:

```bash
cd bookmark-manager
python3 bookmarks.py --help
```

Из корня репозитория / from the repo root (файл данных всё равно будет `bookmark-manager/bookmarks.json`):

```bash
python3 bookmark-manager/bookmarks.py --help
```

Свой путь к файлу / custom data file (`--file` можно ставить до или после команды):

```bash
python3 bookmarks.py --file ~/my-bookmarks.json list
python3 bookmarks.py search docs --file ~/my-bookmarks.json
```

## Примеры / Examples

```bash
python3 bookmarks.py add https://docs.python.org/3/ "Python docs"
python3 bookmarks.py add https://developer.mozilla.org/ MDN Web Docs
python3 bookmarks.py add example.com
python3 bookmarks.py list
python3 bookmarks.py search python
python3 bookmarks.py search github.com
python3 bookmarks.py remove 3
```

`add` без заголовка берёт имя из адреса. Слова после адреса складываются в один заголовок, кавычки не обязательны: `python3 bookmarks.py add https://example.com Example site`.

Without a title, `add` takes the name from the URL. Words after the URL are joined into one title, so quotes are optional.

Если схемы нет, подставляется `https://`. Схема и хост записываются строчными буквами, порты 80 и 443 опускаются. Поэтому `Example.COM` и `https://example.com` — одна и та же закладка. Повторный `add` того же адреса завершается с кодом 1 и не меняет файл.

If the scheme is missing, `https://` is added. The scheme and host are stored in lowercase, and ports 80 and 443 are omitted. `Example.COM` and `https://example.com` are the same bookmark, so adding it again exits 1 and leaves the file unchanged.

Подтверждение `add` / what `add` prints:

```text
Added #1  Python docs  https://docs.python.org/3/
```

`search` ищет подстроку в заголовке или в адресе и не учитывает регистр. Несколько слов собираются в одну фразу. Если ничего не найдено, программа печатает `No matches for ...` и всё равно завершается с кодом 0.

`search` looks for a case-insensitive substring in the title or the URL. Separate words are joined into one phrase. When nothing matches, it prints `No matches for ...` and still exits 0.

Пример `list` по файлу-образцу / sample `list` (`python3 bookmarks.py --file bookmarks.sample.json list`):

```text
1  Python docs   https://docs.python.org/3/
2  MDN Web Docs  https://developer.mozilla.org/
3  GitHub        https://github.com/
4  Хабр          https://habr.com/

4 bookmarks
```

Пример `search docs` по тому же файлу / sample `search docs`:

```text
1  Python docs   https://docs.python.org/3/
2  MDN Web Docs  https://developer.mozilla.org/

2 matches
```

Пустой список — не ошибка, код выхода 0.

An empty list is not an error; the exit code is still 0.

## Команды / Commands

| Команда / Command | Что делает / What it does |
| --- | --- |
| `add <адрес> [заголовок...]` | Сохранить закладку и напечатать её id |
| `list` | Показать все закладки, в порядке добавления |
| `search <текст>` | Найти закладки, у которых заголовок или адрес содержит текст |
| `remove <id>` | Удалить закладку по id из `list` или `search` |
| `--file <путь>` | Другой JSON вместо `bookmarks.json` рядом со скриптом |
| `--help` | Справка по программе или подкоманде |

## Файл данных / Data file

`bookmarks.json` создаётся при первой команде `add` и указан в `.gitignore`, чтобы личные ссылки не попали в git. Кодировка — UTF-8. Запись идёт через временный файл: сбой не оставляет обрезанный JSON.

`bookmarks.json` is created on the first `add` and is listed in `.gitignore`, so personal links stay out of git. The encoding is UTF-8. Writes go through a temporary file, so a crash does not leave a half-written JSON file.

```json
{
  "next_id": 2,
  "bookmarks": [
    {
      "id": 1,
      "title": "Python docs",
      "url": "https://docs.python.org/3/",
      "created_at": "2026-11-06T06:00:00+00:00"
    }
  ]
}
```

`bookmarks.sample.json` — короткий пример. Его можно читать и не создавать свой файл:

`bookmarks.sample.json` is a short example. You can read it without creating your own file:

```bash
python3 bookmarks.py --file bookmarks.sample.json list
python3 bookmarks.py --file bookmarks.sample.json search docs
```

Из корня репозитория путь к образцу другой, потому что `--file` считается от текущей папки, а не от скрипта:

From the repo root the sample path is different, because `--file` is relative to the current directory, not to the script:

```bash
python3 bookmark-manager/bookmarks.py --file bookmark-manager/bookmarks.sample.json list
```

Не добавляйте свои закладки в файл-образец: `add --file bookmarks.sample.json` изменит его.

Don't save your own bookmarks into the sample: `add --file bookmarks.sample.json` would change that file.

Если JSON испорчен или в нём другая структура, команда завершится с кодом 2 и не перезапишет файл.

If the JSON is invalid or has a different structure, the command exits 2 and leaves the file unchanged.

## Коды выхода / Exit codes

| Код | Значение / Meaning |
| --- | --- |
| 0 | Успех, в том числе пустой список или поиск без совпадений |
| 1 | Ошибка пользователя: адрес не http(s), такая закладка уже есть, неизвестный id, пустой текст поиска |
| 2 | Неверные аргументы, или файл данных нельзя прочитать или записать |
