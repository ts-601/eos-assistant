# EOS Assistant

AI-ассистент для светового пульта **ETC EOS** / **EOS Nomad** (на Mac).  
Веб-интерфейс + голосовое управление + чат с Claude AI + live-мониторинг состояния пульта.

---

## Возможности

- **Чат с AI** — описываешь на русском что нужно сделать, Claude переводит в команды EOS
- **CUE List** — отображение и навигация по списку кью в реальном времени
- **Голосовое управление** — транскрипция через Whisper, команды голосом
- **Live-статус** — активное/следующее кью, название шоу, командная строка пульта
- **TCP OSC** — надёжное соединение через TCP порт 3032 (не UDP)
- **Настройки в UI** — IP пульта меняется без перезапуска

---

## Быстрый старт

```bash
# 1. Клонировать
git clone https://github.com/YOUR_USERNAME/eos-assistant.git
cd eos-assistant

# 2. Установить зависимости
pip3 install -r requirements.txt

# 3. Настроить
cp src/config.example.py src/config.py
# Отредактировать src/config.py — вписать IP пульта и Anthropic API key

# 4. Запустить
./run.sh
# или: cd src && python3 web/app.py

# 5. Открыть
open http://localhost:5002
```

---

## Настройка пульта EOS

В EOS: **Setup → Show Control → OSC**

| Параметр | Значение |
|---|---|
| OSC RX | Enabled |
| OSC TX | Enabled |
| OSC UDP RX Port | 8000 |
| OSC UDP TX Port | 8001 |
| OSC TCP Server Ports | 3032 |
| OSC TCP Mode | Packet Length (v1.0) |

> **Важно:** Наш ассистент подключается по **TCP на порт 3032**.  
> UDP порты нужны только если хочется отправлять команды через UDP (не используется).

Если используется реальный пульт в сети:
- Узнать IP пульта (Setup → About Device)
- Вписать в `src/config.py` в поле `EOS_IP`
- Либо изменить в веб-интерфейсе (вкладка "Настройки")

Для **EOS Nomad на Mac**:
- Найти реальный IP: `ifconfig | grep "inet "` — брать не 127.0.0.1
- Например: `172.20.10.2` (Wi-Fi hotspot) или `2.254.172.x` (ethernet)

---

## Архитектура

```
Browser ←HTTP/SSE→ Flask (5002) ←TCP OSC→ ETC EOS (3032)
                        ↓
                   Claude AI (Anthropic API)
                        ↓
                   Whisper (локально)
```

### Файлы

```
src/
  config.py              # Настройки (не в git — содержит API key)
  config.example.py      # Шаблон настроек
  core/
    osc_bridge.py        # TCP OSC коннектор к EOS (основной модуль)
    eos_analyzer.py      # Анализ шоу-файлов
    usitt_parser.py      # Парсер USITT ASCII
  voice/
    parser.py            # Парсер голосовых команд
    transcriber.py       # Whisper транскрипция
  web/
    app.py               # Flask сервер, API endpoints
    templates/
      index.html         # Весь фронтенд (SPA, без фреймворков)
  context.md             # Инструкции для Claude — синтаксис команд EOS
```

---

## OSC Bridge — как работает

Модуль `src/core/osc_bridge.py` управляет TCP-соединением с EOS:

1. **Подключение** → `connect()` к `EOS_IP:3032`
2. **Подписка** → `/eos/subscribe 1` — EOS начинает слать state updates
3. **Приём** → TCP stream с 4-байтовым length-prefix (Packet Length v1.0)
4. **Отправка** → все команды через тот же TCP сокет
5. **Переподключение** → автоматически каждые 3 сек при разрыве

### Почему TCP, а не UDP?

EOS не отвечает на UDP subscribe если наш IP не прописан в OSC UDP TX IP Address **на пульте**.  
TCP (порт 3032) работает без дополнительных настроек на пульте — достаточно включить TCP server.

---

## API Endpoints

| Метод | URL | Описание |
|---|---|---|
| GET | `/api/state` | Текущее состояние: active_cue, show_name, eos_ok... |
| GET | `/api/events` | SSE stream обновлений |
| POST | `/api/cmd` | Выполнить EOS-команду `{"cmd": "GO"}` |
| POST | `/api/ai` | Запрос к Claude `{"message": "..."}` |
| GET | `/api/cue_list` | Список CUE |
| POST | `/api/set_cue_list` | Переключить лист CUE `{"list_num": 2}` |
| GET | `/api/get_ip` | Текущие настройки подключения |
| POST | `/api/set_ip` | Сменить IP пульта `{"ip": "..."}` |
| POST | `/api/set_port` | Сменить порт `{"port": 8000}` |

---

## Команды EOS (синтаксис)

Подробнее в `src/context.md`. Основные:

```
GO                        — запустить текущий кью
STOP                      — стоп / бэк
GO TO CUE 5               — перейти на кью 5 (в активном листе)
GO TO CUE 3/1             — кью 1 в листе 3 (только если лист указан явно)
GO TO CUE OUT             — погасить всё
GO TO CUE 0               — начало листа
CUE 5 LABEL Сцена 1       — переименовать кью
RECORD CUE 10             — записать кью
DELETE CUE 5              — удалить кью
MACRO 42                  — запустить макрос
CHAN 1 @ FULL             — канал 1 в полный
GROUP 3 @ 50              — группа 3 на 50%
```

---

## Зависимости

- Python 3.10+
- `flask` — веб-сервер
- `python-osc` — OSC библиотека (используется только для сборки OSC-пакетов)
- `anthropic` — Claude AI API
- `faster-whisper` — локальная транскрипция голоса
- `pyaudio` — захват аудио с микрофона

---

## Переменные окружения (альтернатива config.py)

Можно не хранить ключ в файле, а задать через env:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
cd src && python3 web/app.py
```

*(требует небольшой правки config.py для чтения os.environ)*
