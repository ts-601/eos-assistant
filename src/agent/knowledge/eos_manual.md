# EOS Manual — база знаний агента

## Синтаксис команд EOS CLI

### Кью — переходы
```
GO                              — нажать GO (следующий кью)
STOP                            — стоп/бэк
GO TO CUE 5                     — перейти на кью 5 в активном листе
GO TO CUE 3/1                   — кью 1 в листе 3 (формат ЛИСТ/КЬЮ!)
GO TO CUE OUT                   — погасить всё
GO TO CUE 0                     — начало листа
GO TO CUE 5 TIME 3              — перейти с временем 3 сек
```

### Кью — параметры
```
CUE 5 LABEL Сцена               — переименовать кью 5  ✓ работает
CUE 5 COPY TO CUE 10            — скопировать          ✓ работает
CUE 5 MOVE TO CUE 10            — переместить          ✓ работает
```

❌ НЕ РАБОТАЕТ через OSC (EOS требует ручного редактирования):
- CUE 5 TIME 3      — изменить время кью (только на пульте вручную)
- CUE 5 UP TIME 2   — время нарастания
- CUE 5 DOWN TIME 4 — время спада
- CUE 5 DELAY 1     — задержка

Если пользователь просит изменить время кью — скажи: «Это можно сделать только вручную на пульте: выбери кью в Blind, нажми Time и введи значение».

### Кью — запись и редактирование
```
RECORD CUE 10                   — записать кью 10
UPDATE CUE 5                    — обновить кью 5
DELETE CUE 5                    — удалить кью 5 (необратимо!)
```

### Каналы и уровни
```
CHAN 1 @ FULL                   — канал 1 на 100%
CHAN 1 @ 50                     — канал 1 на 50%
CHAN 1 @ OUT                    — канал 1 в 0
CHAN 1 THRU 10 @ 75             — каналы 1-10 на 75%
GROUP 3 @ FULL                  — группа 3 на 100%
SUB 2 @ 50                      — субмастер 2 на 50%
```

### Управление и режимы
```
MACRO 42                        — запустить макрос 42
BLIND                           — режим blind
LIVE                            — вернуться в live
UPDATE                          — обновить текущий кью
UNDO                            — отменить действие
```

---

## OSC протокол EOS

### Подключение
- Протокол: **TCP OSC** на порту **3032** (Packet Length v1.0)
- Framing: `[4 байта big-endian uint32: длина][OSC сообщение]`
- Subscribe: `/eos/subscribe 1` → EOS начинает слать state updates
- **НЕ использовать UDP** — не работает без настройки TX IP на пульте
- User ID: **777**

### Команды → EOS
```
/eos/user/777/cmd   "GO TO CUE 5#"  — CLI команда (# = Enter)
/eos/user/777/key/go_0              — кнопка GO
/eos/user/777/key/stop              — кнопка STOP
/eos/user/777/key/blind             — Blind
/eos/user/777/key/live              — Live
/eos/user/777/key/update            — Update
/eos/user/777/key/undo              — Undo
/eos/user/777/key/escape            — Escape / очистить буфер
```

### Прямые OSC пути (надёжнее CLI)
```
/eos/cue/1/5/fire               — fire кью 5 листа 1
/eos/cue/1/0/fire               — GO TO CUE OUT
/eos/chan/1=75                   — канал 1 на 75%
/eos/chan/1/full                 — канал 1 на 100%
/eos/group/3=100                 — группа 3 на 100%
/eos/sub/2=0.5                   — суб 2 на 50% (float 0.0-1.0!)
/eos/macro/42/fire              — запустить макрос 42
/eos/set/cue/1/5/label="Текст" — установить лейбл кью
```

### Запросы данных
```
/eos/get/cue/1/count            → кол-во кью в листе 1
/eos/get/cue/1/5                → данные кью 5
/eos/get/cue/1/index/0          → первый кью (0-based)
```

### EOS → нам
```
/eos/out/active/cue/text        — "1/5 НАЗВАНИЕ 3.0 100%"
/eos/out/pending/cue/text       — следующий кью
/eos/out/show/name              — название шоу
/eos/out/user/777/cmd           — командная строка пульта
/eos/out/event/cue/1/5/fire     — кью 5 запустился
/eos/out/event/state            — 0=Blind, 1=Live
/eos/out/fader/1/1              — уровень фейдера
```

---

## Форматы данных

### Строка активного кью
```
"1/5.1 Выход артистов 3.0 100%"
  └─┬─┘ └──────┬──────┘ └┬┘ └┬┘
    │           │          │   └─ прогресс
    │           │          └───── время (сек)
    │           └──────────────── название
    └─────────────────────────── ЛИСТ/НОМЕР
```

### Нумерация кью
- Целые: 1, 2, 3 ... 999  |  Дробные: 1.1, 5.5, 10.99
- **Формат: ЛИСТ/КЬЮ** — 3/1 = лист 3, кью 1 (не наоборот!)

---

## Макросы EOS

```
♦ = [Enter]           — подтверждение
Clear_CmdLine          — очистить буфер (обязательно перед каждой командой!)
Macro_Loop_Begin/End ♦ — цикл по всем кью
Macro_Wait 0 . 2       — пауза 0.2 сек
Select_Active          — каналы с intensity > 0
AllNPs                 — все non-intensity параметры
Group Cue              — все каналы текущего кью
```

### Макрос 690 — чистка phantom NP
```
Clear_CmdLine Blind Setup ♦
Clear_CmdLine Tracking Disable ♦
Clear_CmdLine Live ♦
Clear_CmdLine Blind Blind Cue ♦
Clear_CmdLine Home ♦
Macro_Loop_Begin ♦
Group Cue – Select_Active AllNPs @ ♦
Macro_Wait 0 . 2 Clear_CmdLine ♦
Clear_CmdLine Next ♦
Macro_Loop_End ♦
Clear_CmdLine Tracking Enable ♦
Clear_CmdLine Live ♦
```
Формула: `(все каналы кью) − (активные) → их NP → @ (очистить)`

---

## USITT ASCII формат

```
Cue 1.5 1           — кью 1.5, лист 1
   Text LABEL        — название
   Chan 211@Hff      — интенсивность hex (Hff=100%, H00=0%)
   $$Param 211 1@65535 2@PR1001
   $$Block           — кью заблокирован
```
param_id: 1=Intensity, 2=Pan, 3=Tilt
