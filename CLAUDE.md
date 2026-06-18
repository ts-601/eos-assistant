# EOS Assistant — CLAUDE.md

Проект: веб-интерфейс + ИИ-агент для светового пульта **ETC EOS** (шоу "Великий Гэтсби").

---

## Быстрый старт

```bash
cd /Users/ts/eos-assistant/src && python3 web/app.py
# → http://localhost:5002
```

После запуска проверить подключение:
```bash
curl -s http://localhost:5002/api/state | python3 -m json.tool
# eos_ok: true — пульт подключён
```

Перезапустить сервер:
```bash
pkill -f "app.py"; sleep 1; cd /Users/ts/eos-assistant/src && python3 web/app.py &>/tmp/eos-app.log &
```

---

## Архитектура

```
src/
├── web/
│   ├── app.py              — Flask сервер (порт 5002)
│   └── templates/index.html — весь UI (одна страница, 6 вкладок)
├── core/
│   ├── osc_bridge.py       — TCP OSC соединение с EOS (порт 3032)
│   └── usitt_parser.py     — парсер USITT ASCII экспорта
├── agent/
│   ├── agent.py            — EOSAgent (Claude API + индекс мануала + память)
│   ├── sandbox.py          — режим песочницы (команды не идут на пульт)
│   ├── knowledge/
│   │   ├── eos_manual.md   — база знаний: синтаксис EOS, OSC пути
│   │   ├── agent_rules.md  — правила: когда уточнять, что опасно
│   │   └── indexer.py      — поиск по секциям мануала
│   ├── memory/             — логи сессий (JSONL)
│   └── solutions/          — записанные решения проблем (MD)
├── voice/
│   ├── parser.py           — быстрый парсер голосовых команд
│   └── transcriber.py      — Faster-Whisper STT
└── config.py               — IP пульта, API ключи (НЕ в git)
```

---

## Ключевые факты

### EOS подключение
- **Протокол:** TCP OSC на порту **3032** (Packet Length v1.0 framing)
- **Пульт IP:** `2.254.172.153` (реальный пульт в сети)
- **Nomad IP:** `172.20.10.2` (локальная разработка)
- **Framing:** `[4 байта big-endian uint32: длина][OSC сообщение]`
- UDP subscribe **не работает** без настройки TX IP на пульте — только TCP
- `/eos/subscribe 1` → EOS начинает слать state updates

### OSC пути (самые важные)
```
→ EOS:  /eos/user/777/cmd  "GO TO CUE 5#"   — команда (# = Enter)
← EOS:  /eos/out/active/cue/text             — активное кью
← EOS:  /eos/out/show/name                   — название шоу
```

### Формат кью EOS
- `GO TO CUE 5` — кью 5 в активном листе (без номера листа если не указан явно)
- `GO TO CUE 3/1` — кью 1 в листе 3 (ЛИСТ/КЬЮ — не наоборот!)
- `GO TO CUE OUT` — погасить всё
- Дробные кью: `5.1`, `10.99`

---

## config.py (не в git, создать из config.example.py)

```python
EOS_IP        = "2.254.172.153"   # реальный пульт
EOS_OSC_PORT  = 3032
EOS_RX_PORT   = 8000
WEB_PORT      = 5002
ANTHROPIC_API_KEY = "sk-ant-..."
```

---

## Git / GitHub

Репозиторий: `ts-601/eos-assistant`

```bash
# Push — credentials сохранены в ~/.git-credentials, просто:
git push
```

`src/config.py` исключён из git через `.gitignore` — содержит реальный API ключ и IP пульта.

---

## Агент (EOSAgent)

- Использует `claude-sonnet-4-6`
- При каждом запросе ищет релевантные секции мануала через `ManualIndex` (не грузит весь мануал)
- Команды возвращает в тегах `<cmd>{"cmd": "GO TO CUE 5"}</cmd>`
- Логирует сессии в `agent/memory/session_YYYYMMDD.jsonl`
- Sandbox режим: `POST /api/agent/sandbox {"enabled": true}` — команды не идут на пульт

---

## UI (index.html)

6 вкладок: **Live** · Каналы · CUE List · Фейдеры · Шоу · Настройки

Важные кнопки Live:
- 🎙 — push-to-talk (долгое нажатие → выбор микрофона)
- 🔊 — TTS ответов агента (долгое нажатие → выбор голоса)

SSE поток: `GET /api/events` — реалтайм обновления состояния пульта.

---

## Частые задачи

**Проверить OSC трафик:**
```
http://localhost:5002/monitor
```

**Сменить IP пульта без перезапуска:**
```bash
curl -s -X POST http://localhost:5002/api/set_ip -H "Content-Type: application/json" -d '{"ip":"2.254.172.153"}'
```

**Анализ USITT файла:**
```
http://localhost:5002 → вкладка Шоу → загрузить .asc файл
```

**Включить песочницу агента:**
```bash
curl -s -X POST http://localhost:5002/api/agent/sandbox -H "Content-Type: application/json" -d '{"enabled":true}'
```

---

## Что НЕ делать

- Не трогать TX Port/IP в настройках EOS на реальном пульте — продакшен
- Не коммитить `src/config.py` — там реальный API ключ
- Не использовать UDP для OSC — не работает без настройки на пульте
- `GO TO CUE` — без номера листа если пользователь не указал явно
