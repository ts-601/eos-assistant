# EOS Manual — база знаний агента

## Синтаксис команд EOS CLI

### Кью
```
GO                          — нажать GO
STOP                        — стоп/бэк
GO TO CUE 5                 — перейти на кью 5 в активном листе
GO TO CUE 3/1               — кью 1 в листе 3 (только если явно указан лист)
GO TO CUE OUT               — погасить всё (Cue Out)
GO TO CUE 0                 — начало листа
GO TO CUE 5 TIME 3          — перейти с временем 3 сек
RECORD CUE 10               — записать кью 10
DELETE CUE 5                — удалить кью 5
CUE 5 LABEL Сцена 1         — переименовать кью 5
UPDATE CUE 5                — обновить кью 5
CUE 5 MOVE TO CUE 10       — переместить кью 5 → 10
CUE 5 COPY TO CUE 10       — скопировать кью 5 → 10
```

### Каналы и группы
```
CHAN 1 @ FULL               — канал 1 на 100%
CHAN 1 @ 50                 — канал 1 на 50%
CHAN 1 THRU 10 @ 75         — каналы 1-10 на 75%
GROUP 3 @ FULL              — группа 3 на 100%
SUB 2 @ 50                  — субмастер 2 на 50%
```

### Макросы и управление
```
MACRO 42                    — запустить макрос 42
BLIND                       — режим blind
LIVE                        — вернуться в live
UPDATE                      — обновить текущий кью
UNDO                        — отменить действие
```

## OSC протокол EOS

### Подключение
- Протокол: **TCP OSC** на порту **3032**
- Framing: **Packet Length v1.0** (4-байт big-endian length prefix)
- Subscribe: `/eos/subscribe 1` → EOS начинает слать state updates
- НЕ использовать UDP subscribe — EOS не отвечает без настройки TX IP

### Ключевые OSC пути (входящие от EOS)
```
/eos/out/active/cue/text    — активный кью (строка "1/5 LABEL 3.0 100%")
/eos/out/pending/cue/text   — следующий кью
/eos/out/show/name          — название шоу
/eos/out/user/777/cmd       — командная строка пульта
/eos/out/cue/1/5/label      — метка кью 5 в листе 1
```

### Ключевые OSC пути (команды → EOS)
```
/eos/user/777/cmd           — командная строка (строка + "#" = Enter)
/eos/user/777/key/go_0      — кнопка GO
/eos/user/777/key/stop      — кнопка STOP
/eos/user/777/key/escape    — Escape
/eos/user/777/key/update    — Update
/eos/user/777/key/blind     — Blind
/eos/user/777/key/live      — Live
/eos/get/cue/1/5/label      — запросить метку кью 5 листа 1
/eos/subscribe              — подписаться на updates (value=1)
/eos/reset                  — сброс/переподключение
```

## Форматы данных

### Строка активного кью
Формат: `ЛИСТ/НОМЕРкью НАЗВАНИЕ ВРЕМЯ ПРОГРЕСС`
Пример: `1/5.1 Выход артистов 3.0 100%`
- ЛИСТ = номер кью-листа
- НОМЕРкью = номер (может быть дробным: 5.1)
- НАЗВАНИЕ = текстовый лейбл
- ВРЕМЯ = время перехода в секундах
- ПРОГРЕСС = % выполнения

### Нумерация кью
- Целые: 1, 2, 3 ... 999
- Дробные: 1.1, 5.5, 10.99
- Листы: кью 1 в листе 3 → "3/1"
- **Формат: ЛИСТ/КЬЮ** (не кью/лист!)

## USITT ASCII формат EOS

```
Cue 1.5 1           ← кью 1.5, лист 1
   Text LABEL       ← название
   Chan 211@Hff     ← интенсивность hex (Hff=100%, H00=0%)
   $$Param 211 1@65535 2@PR1001
                    ← param_id: 1=Intensity, 2=Pan, 3=Tilt
   $$Block          ← кью заблокирован
```
