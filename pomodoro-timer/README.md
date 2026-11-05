# pomodoro-timer

Классический помодоро на одной странице. Сборка не нужна: откройте `index.html` в браузере.

A classic pomodoro timer on one page. Open `index.html` in a browser. There is nothing to install and no build step.

## Как открыть / How to open

Дважды щёлкните `index.html`, или из этой папки:

Double-click `index.html`, or from this folder:

```bash
cd pomodoro-timer
python3 -m http.server 8765
```

Затем откройте http://127.0.0.1:8765 . Файл можно открыть и напрямую (`file://`): страница не использует сборщик и внешние скрипты.

Then open http://127.0.0.1:8765. Opening the file directly (`file://`) also works. The page does not use a bundler or any external script.

## Как работает таймер / How the timer works

| Сессия / Session | Длительность / Length |
| --- | --- |
| Work | 25 минут / 25 minutes |
| Short break | 5 минут / 5 minutes |
| Long break | 15 минут / 15 minutes, после каждых 4 рабочих сессий / after every 4 work sessions |

Цикл такой: работа → короткий перерыв, и так четыре раза, затем длинный перерыв, потом снова работа. Следующая сессия сама не стартует. Когда время доходит до нуля, звучит короткий сигнал, страница подсвечивает сообщение, и загружается следующая сессия на паузе. **Start** начинает её.

The cycle is work, then a short break, four times, then a long break, then work again. The next session does not start on its own. At zero, a short chime plays, the page highlights a message, and the next session is loaded paused. **Start** begins it.

- **Start** запускает текущую сессию. **Pause** останавливает отсчёт, не сбрасывая его. **Reset** возвращает текущую сессию к полной длине и не обнуляет число законченных рабочих сессий.
- **Start** runs the current session. **Pause** freezes the countdown. **Reset** restores the current session to its full length and does not clear finished work sessions.
- Кнопки Work, Short break и Long break переключают тип сессии и ставят её полную длину на паузу. Рабочая сессия засчитывается в круг, только если дошла до нуля. Незаконченная работа в счёт не идёт.
- Work, Short break, and Long break load that session at full length and pause. A work session counts toward the round only when it reaches zero.
- В заголовке вкладки видно оставшееся время. Отсчёт идёт по часам компьютера: если браузер притормозит фоновую вкладку, время догонит реальное, когда вы вернётесь.
- The tab title shows the time left. The countdown follows the wall clock, so if a background tab is delayed, it catches up when you return.
- Пробел запускает или ставит на паузу, когда фокус не на кнопке. `R` сбрасывает текущую сессию.
- Space starts or pauses when focus is not on a button. `R` resets the current session.
- Звук — короткий сигнал через Web Audio API, без аудиофайла. Браузер может молчать, пока вы один раз не нажмёте Start.
- The cue is a short Web Audio chime, not an audio file. A browser may stay silent until you press Start once.
- Закрытие страницы обнуляет круг. Ничего не записывается на диск.
- Closing the page clears the round. Nothing is stored.

## Короткие интервалы / Preview timings

Откройте `index.html?demo=1`, чтобы увидеть тот же цикл без ожидания: работа 8 секунд, короткий перерыв 4 секунды, длинный перерыв 6 секунд. На странице есть пометка, что это укороченные интервалы.

Open `index.html?demo=1` to watch the same cycle without waiting: 8-second work, 4-second short break, 6-second long break. The page labels these as preview timings.

## Файлы / Files

- `index.html` — страница / the page
- `styles.css` — оформление / layout and theme
- `app.js` — таймер / the timer
