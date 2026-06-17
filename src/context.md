# ETC EOS — справочник команд и синтаксис

## Синтаксис командной строки EOS

EOS работает как калькулятор: сначала выбираешь объект, потом действие.
Команды отправляются через OSC: /eos/cmd "КОМАНДА"

### Основные объекты
```
CHAN 5              — выбрать канал 5
CHAN 1 THRU 10      — каналы 1 до 10
CHAN 1 + 3 + 5      — каналы 1, 3, 5
CHAN 1 THRU 10 - 5  — каналы 1-10 кроме 5
GROUP 3             — группа 3
SUB 2               — субмастер 2
CUE 5               — кью 5 (в текущем листе)
CUE 3/1             — кью 1 в листе 3 (формат: лист/кью)
MACRO 10            — макрос 10
PRESET 5            — пресет 5
PALETTE 3           — палитра 3
```

### Уровни интенсивности
```
CHAN 5 @ 50         — канал 5 на 50%
CHAN 5 @ FULL       — канал 5 на 100%
CHAN 5 @ OUT        — канал 5 на 0%
CHAN 5 @ +10        — канал 5 +10% от текущего
CHAN 5 @ -10        — канал 5 -10% от текущего
CHAN 1 THRU 10 @ 75 — каналы 1-10 на 75%
```

### Навигация по кью
```
GO                  — запустить следующее кью
STOP                — стоп / холд фейд
BACK                — вернуться на предыдущее кью
GO TO CUE 5         — перейти на кью 5 в активном листе
GO TO CUE 3/1       — перейти на кью 1 в листе 3 (только если пользователь явно указал лист)
GO TO CUE 5 TIME 0  — перейти на кью 5 немедленно (время 0)
GO TO CUE 5 TIME    — перейти со временем самого кью
GO TO CUE OUT       — погасить всё (кью OUT)
HOME                — перейти на первое кью в листе
```

### Режимы работы
```
BLIND               — Blind режим (редактирование без влияния на сцену)
LIVE                — Live режим (возврат из Blind)
SETUP               — открыть Setup
FLEXI               — Flexi режим
```

### Запись и редактирование
```
RECORD CUE 10           — записать новое кью 10
RECORD CUE 10 TIME 3    — записать кью 10 со временем 3 сек
UPDATE                  — обновить текущее активное кью
UPDATE CUE 10           — обновить кью 10
LABEL CUE 5 НАЗВАНИЕ    — подписать кью 5
CUE 5 MOVE TO CUE 6    — переместить кью 5 → 6
CUE 5 COPY TO CUE 6    — скопировать кью 5 → 6
DELETE CUE 5            — удалить кью 5
```

### Параметры (не-интенсивность)
```
CHAN 5 PAN 50           — Pan канала 5 на 50
CHAN 5 TILT 75          — Tilt канала 5 на 75
CHAN 5 COLOR PALETTE 3  — применить цветовую палитру 3
CHAN 5 FOCUS PALETTE 2  — применить focus палитру 2
CHAN 5 HOME             — сбросить все параметры канала в Home
CHAN 5 ALLNPS @         — очистить все non-intensity параметры (очень важно!)
SELECT_ACTIVE           — выбрать только активные каналы (intensity > 0)
```

### Трекинг и блокировка
```
TRACKING ENABLE         — включить трекинг
TRACKING DISABLE        — выключить трекинг
CUE 5 BLOCK             — заблокировать кью (записать все значения явно)
CUE 5 UNBLOCK           — разблокировать кью
ASSERT                  — assert (утвердить трекинг)
```

### AutoMark
```
AUTOMARK ENABLE         — включить AutoMark (пресет следующего кью)
AUTOMARK DISABLE        — выключить AutoMark
```

### Субмастеры и фейдеры
```
SUB 2 @ 75             — субмастер 2 на 75%
SUB 2 @ FULL           — субмастер 2 на 100%
SUB 2 @ OUT            — субмастер 2 на 0%
SUB 2 GO               — запустить субмастер 2
SUB 2 STOP             — стоп субмастер 2
```

### Макросы
```
MACRO 5                 — запустить макрос 5
MACRO 5 STOP            — остановить макрос 5
```

### Группы
```
GROUP 3 @ 50           — группа 3 на 50%
RECORD GROUP 5         — записать группу 5 из текущего выбора
LABEL GROUP 5 НАЗВАНИЕ — подписать группу
```

### Пресеты и палитры
```
PRESET 10              — применить пресет 10
RECORD PRESET 10       — записать пресет 10
FOCUS PALETTE 3        — применить focus палитру 3
COLOR PALETTE 5        — применить цветовую палитру 5
RECORD COLOR PALETTE 5 — записать
```

### Эффекты
```
EFFECT 3               — применить эффект 3
EFFECT 3 START         — запустить эффект
EFFECT 3 STOP          — остановить эффект
```

## EOS Macro синтаксис

Макросы пишутся как последовательность EOS ключевых слов.
`♦` = [Enter] — подтверждает каждую команду.
`Clear_CmdLine` — обязательно перед следующей командой.

### Ключевые слова макросов
```
Clear_CmdLine               — очистить командную строку
Macro_Loop_Begin ♦          — начало цикла по кью
Macro_Loop_End ♦            — конец цикла
Macro_Wait 0 . 5 ♦         — пауза 0.5 секунды
Blind ♦                     — перейти в Blind
Live ♦                      — перейти в Live
Setup ♦                     — открыть Setup
Home ♦                      — первое кью
Next ♦                      — следующее кью
Select_Active               — выбрать активные каналы
AllNPs                      — все non-intensity параметры
Group Cue                   — все каналы текущего кью
AutoMark Enable/Disable ♦   — вкл/выкл AutoMark
Tracking Enable/Disable ♦   — вкл/выкл трекинг
```

### Шаблон макроса — чистка phantom NP во всём кью-листе
```
Clear_CmdLine Blind Setup ♦
Clear_CmdLine AutoMark Enable ♦
Clear_CmdLine Tracking Disable ♦
Clear_CmdLine Live ♦
Clear_CmdLine Blind Blind Cue ♦
Clear_CmdLine Home ♦
Macro_Loop_Begin ♦
Group Cue – Select_Active AllNPs @ ♦
Macro_Wait 0 . 2 Clear_CmdLine ♦
Clear_CmdLine Next ♦
Macro_Loop_End ♦
Clear_CmdLine Blind Setup ♦
Clear_CmdLine Tracking Enable ♦
Clear_CmdLine Live ♦
```
Смысл: для каждого кью — берём все каналы минус активные (intensity>0) → очищаем их NP параметры.

## Концепции EOS

**Трекинг** — значения тянутся вперёд по кью-листу пока не встретят новое значение или Block.
**Block** — кью с явно зафиксированными значениями, трекинг сквозь него не проходит.
**Phantom parameters** — канал с intensity=0, но с записанными Pan/Tilt/Color → движется в темноте.
**AutoMark** — EOS автоматически пресетит приборы в параметры следующего кью пока они в темноте.
**Assert** — принудительно применить значения трекинга (если прибор управлялся вручную).
**AllNPs** — все параметры кроме интенсивности (Non-Priority parameters).
**Select_Active** — каналы с intensity > 0 в текущем кью.
**User ID** — идентификатор пользователя, у нас ID 777.

## OSC адреса EOS

```
/eos/cmd "КОМАНДА"          — выполнить CLI команду
/eos/key/go                 — кнопка GO
/eos/key/stop_back          — STOP/BACK
/eos/key/live               — кнопка LIVE
/eos/key/blind              — кнопка BLIND
/eos/subscribe 1            — подписаться на события
/eos/ping                   — проверка связи
/eos/fader/1/1/fire         — запустить фейдер банк 1, слот 1
/eos/cue/1/5/fire           — запустить кью 5 в листе 1
/eos/out/active/cue/text    — текст активного кью (от EOS)
/eos/out/pending/cue/text   — текст следующего кью (от EOS)
```
