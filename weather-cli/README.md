# weather-cli

Текущая погода для города в терминале. Город ищется через Open-Meteo, ключ API не нужен.

Current weather for a city, in the terminal. The city is resolved through Open-Meteo. No API key is required.

Нужен Python 3.9+ из стандартной библиотеки и доступ в сеть. Ставить зависимости не нужно.

Python 3.9+ from the standard library is enough, plus a network connection. There is nothing to install.

## Как запустить / How to run

Из папки проекта / from this folder:

```bash
cd weather-cli
python3 weather.py --help
python3 weather.py London
```

Из корня репозитория / from the repo root:

```bash
python3 weather-cli/weather.py "New York"
```

Несколько слов в названии города можно передавать и без кавычек: они собираются в одну строку.

Separate words are joined into one city name: `python3 weather.py New York`.

## Примеры / Examples

```bash
python3 weather.py Berlin
python3 weather.py --units fahrenheit Tokyo
python3 weather.py --country US Springfield
python3 weather.py --list Springfield
python3 weather.py --pick 2 Springfield
python3 weather.py --json Paris
```

Пример вывода / sample output:

```text
Berlin, State of Berlin, Germany
Light drizzle
Temperature: 2.6 °C (feels like -0.2 °C)
Humidity: 92%
Wind: 6.9 km/h from SE
Precipitation: 0.0 mm
Observed: 2026-11-08 07:00 GMT+1

9 other matches. Run with --list to choose a different place.

Data: Open-Meteo (https://open-meteo.com/)
```

`--units fahrenheit` (или `f`) показывает температуру в °F и ветер в mph. Осадки всегда в миллиметрах. По умолчанию — градусы Цельсия и км/ч.

`--units fahrenheit` (or `f`) reports temperature in °F and wind in mph. Precipitation stays in millimeters. The default is Celsius and km/h.

Если название встречается несколько раз, берётся первый результат поиска, а в конце печатается, сколько ещё совпадений есть. `--list` показывает нумерованный список. `--pick N` выбирает строку из этого списка. `--country US` оставляет только места с этим двухбуквенным кодом страны.

When several places share the name, the first search result is used and the output says how many others matched. `--list` prints the numbered matches. `--pick N` selects one of those rows. `--country US` keeps only places with that two-letter country code.

## API

Используется бесплатный [Open-Meteo](https://open-meteo.com/): геокодер `geocoding-api.open-meteo.com` и текущие условия `api.open-meteo.com`. Регистрация и ключ не нужны. Для некоммерческого использования действует лимит сервиса (до 10 000 запросов в день). Данные распространяются по лицензии [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); программа указывает источник в каждом ответе.

This tool calls the free [Open-Meteo](https://open-meteo.com/) geocoder (`geocoding-api.open-meteo.com`) and forecast API (`api.open-meteo.com`). There is no sign-up and no API key. Non-commercial use is covered by the service limit (up to 10,000 requests per day). Weather data is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); every response names Open-Meteo as the source.

## Команды / Commands

| Флаг / Flag | Что делает / What it does |
| --- | --- |
| `CITY` | Город. Слова после имени программы склеиваются в одно название |
| `--units celsius\|fahrenheit` | Единицы температуры. Короткие формы: `c` и `f` |
| `--country CC` | Ограничить поиск кодом страны, например `DE` |
| `--list` | Показать совпадения и выйти |
| `--pick N` | Взять совпадение номер N из `--list` |
| `--json` | Напечатать погоду как JSON |
| `--help` | Справка |

## Коды выхода / Exit codes

| Код | Значение / Meaning |
| --- | --- |
| 0 | Успех / success |
| 1 | Ошибка пользователя: пустое название, город не найден или неверный `--pick` / `--country` |
| 2 | Неверные аргументы, или сервис погоды недоступен либо вернул ошибку |
