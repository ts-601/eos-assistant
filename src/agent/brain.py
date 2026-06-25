# -*- coding: utf-8 -*-
"""
EOS Brain — фоновый демон: мониторинг, тестирование, аналитика.
Запускается в отдельном потоке вместе с Flask-сервером.
Не использует API — работает полностью локально и бесплатно.
"""
import threading
import time
import json
import re
from datetime import datetime, date, timedelta
from pathlib import Path
from collections import Counter, defaultdict

AGENT_DIR  = Path(__file__).parent
MEMORY_DIR = AGENT_DIR / "memory"
REPORTS_DIR = AGENT_DIR / "reports"

_report: dict = {}          # текущий отчёт (читается через API)
_alerts: list = []          # активные предупреждения
_lock = threading.Lock()
_started = False

# ─── Публичный интерфейс ──────────────────────────────────────────────────────

def start(get_state_fn, run_cmd_fn):
    """Запустить демон в фоне. Вызывать один раз при старте сервера."""
    global _started
    if _started:
        return
    _started = True
    t = threading.Thread(target=_loop, args=(get_state_fn, run_cmd_fn), daemon=True)
    t.start()
    print("[Brain] Демон запущен")

def get_report() -> dict:
    with _lock:
        return dict(_report)

def get_alerts() -> list:
    with _lock:
        return list(_alerts)

# ─── Главный цикл ─────────────────────────────────────────────────────────────

def _loop(get_state_fn, run_cmd_fn):
    REPORTS_DIR.mkdir(exist_ok=True)
    MEMORY_DIR.mkdir(exist_ok=True)

    tick = 0
    while True:
        try:
            tick += 1
            state = get_state_fn()

            # Каждую минуту: мониторинг состояния
            _monitor_state(state, tick)

            # Каждые 15 минут: анализ логов
            if tick % 15 == 0:
                _analyze_logs()

            # Каждый час: тест парсера
            if tick % 60 == 0:
                _test_parser()

            # Каждые 6 часов: полный отчёт
            if tick % 360 == 0:
                _build_full_report(state)

            # При первом запуске — сразу сделать отчёт
            if tick == 1:
                _analyze_logs()
                _test_parser()
                _build_full_report(state)

        except Exception as e:
            print(f"[Brain] Ошибка в цикле: {e}")

        time.sleep(60)  # тик раз в минуту

# ─── Мониторинг состояния ─────────────────────────────────────────────────────

_disconnect_count = 0
_last_eos_ok = None

def _monitor_state(state: dict, tick: int):
    global _disconnect_count, _last_eos_ok
    eos_ok = state.get("eos_ok", False)

    if _last_eos_ok is True and not eos_ok:
        _disconnect_count += 1
        _add_alert("warning", f"EOS отключился (всего отключений: {_disconnect_count})")

    if not _last_eos_ok and eos_ok:
        _clear_alert("eos_disconnect")
        _add_alert("info", "EOS подключился ✓", ttl=5)

    _last_eos_ok = eos_ok

    with _lock:
        _report["eos_ok"] = eos_ok
        _report["show_name"] = state.get("show_name", "—")
        _report["active_cue"] = state.get("active_cue", "—")
        _report["disconnect_count"] = _disconnect_count
        _report["last_update"] = datetime.now().strftime("%H:%M:%S")

# ─── Анализ логов сессии ──────────────────────────────────────────────────────

def _analyze_logs():
    today = date.today().strftime("%Y%m%d")
    log_path = MEMORY_DIR / f"session_{today}.jsonl"

    if not log_path.exists():
        # Нет лога сегодня — ищем последний
        logs = sorted(MEMORY_DIR.glob("session_*.jsonl"))
        if not logs:
            return
        log_path = logs[-1]

    entries = []
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except Exception:
                pass

    if not entries:
        return

    # Считаем команды
    all_cmds = []
    for e in entries:
        all_cmds.extend(e.get("commands", []))

    cmd_counter = Counter()
    for cmd in all_cmds:
        # Группируем: "GO TO CUE 5" → "GO TO CUE", "CHAN 3 @ 75" → "CHAN @ level"
        base = _cmd_base(cmd)
        cmd_counter[base] += 1

    # Считаем запросы без команды (не распознанные)
    no_cmd = sum(1 for e in entries if not e.get("commands"))
    total  = len(entries)

    # Активность по часам
    hour_counts = Counter()
    for e in entries:
        try:
            h = datetime.fromisoformat(e["ts"]).hour
            hour_counts[h] += 1
        except Exception:
            pass

    top_cmds = cmd_counter.most_common(10)

    with _lock:
        _report["today_messages"]   = total
        _report["today_commands"]   = len(all_cmds)
        _report["today_no_parse"]   = no_cmd
        _report["top_commands"]     = top_cmds
        _report["hour_activity"]    = dict(sorted(hour_counts.items()))
        _report["log_file"]         = log_path.name
        _report["analyzed_at"]      = datetime.now().strftime("%H:%M:%S")

    _save_report()
    print(f"[Brain] Проанализировано {total} записей из {log_path.name}")

def _cmd_base(cmd: str) -> str:
    """Нормализовать команду для группировки."""
    cmd = cmd.strip()
    if re.match(r"GO TO CUE\s+\S+", cmd):   return "GO TO CUE"
    if re.match(r"CHAN\s+[\d\s]+@\s*FULL", cmd): return "CHAN @ FULL"
    if re.match(r"CHAN\s+[\d\s]+@\s*0",    cmd): return "CHAN @ OUT"
    if re.match(r"CHAN\s+[\d\s]+@",        cmd): return "CHAN @ level"
    if re.match(r"RECORD CUE",             cmd): return "RECORD CUE"
    if re.match(r"DELETE CUE",             cmd): return "DELETE CUE"
    if re.match(r"LABEL CUE",              cmd): return "LABEL CUE"
    return cmd.split()[0] if cmd else "?"

# ─── Тестирование парсера ─────────────────────────────────────────────────────

_PARSER_TESTS = [
    ("перейди на кью 5",              "GO TO CUE 5"),
    ("канал 10 на 75",                "CHAN 10 @ 75"),
    ("go",                            "GO"),
    ("стоп",                          "STOP"),
    ("back",                          "BACK"),
    ("назад",                         "BACK"),
    ("blind",                         "BLIND"),
    ("assert",                        "ASSERT"),
    ("home",                          "HOME"),
    ("select active",                 "SELECT ACTIVE"),
    ("выбери активные",               "SELECT ACTIVE"),
    ("кью 3.1",                       "CUE 3.1"),
    ("запиши кью 10",                 "RECORD CUE 10"),
    ("сник",                          "SNEAK"),
    ("go to cue out",                 "GO TO CUE OUT"),
    ("канал 5 на полный",             "CHAN 5 @ FULL"),
    ("канал 5 плюс 10",               "CHAN 5 @ +10"),
    ("канал 5 минус 5",               "CHAN 5 @ -5"),
    ("канал 1 по 10",                 "CHAN 1 THRU 10"),
    ("канал 1 thru 10 на 50",         "CHAN 1 THRU 10 @ 50"),
    ("паркани канал 5",               "PARK CHAN 5"),
    ("пресет 5",                      "PRESET 5"),
    ("color palette 3",               "COLOR PALETTE 3"),
    ("скопируй кью 5 на 6",           "CUE 5 COPY TO CUE 6"),
    ("какое сейчас активное кью и что следующее?", None),
]

def _test_parser():
    try:
        import sys, os
        sys.path.insert(0, str(AGENT_DIR.parent))
        from voice.parser import parse
    except Exception as e:
        _add_alert("error", f"Парсер не импортируется: {e}")
        return

    passed = 0
    failed = []
    for text, expected in _PARSER_TESTS:
        result = parse(text)
        if result == expected:
            passed += 1
        else:
            failed.append({"input": text, "expected": expected, "got": result})

    total = len(_PARSER_TESTS)
    with _lock:
        _report["parser_tests_total"]  = total
        _report["parser_tests_passed"] = passed
        _report["parser_tests_failed"] = failed
        _report["parser_tested_at"]    = datetime.now().strftime("%H:%M:%S")

    if failed:
        _add_alert("warning", f"Парсер: {len(failed)}/{total} тестов не прошло")
    else:
        print(f"[Brain] Парсер: {passed}/{total} тестов ✓")

# ─── Полный отчёт ─────────────────────────────────────────────────────────────

def _build_full_report(state: dict):
    # Статистика за несколько дней
    logs = sorted(MEMORY_DIR.glob("session_*.jsonl"))[-7:]  # последние 7 дней
    daily = {}
    for log in logs:
        day = log.stem.replace("session_", "")
        entries = _load_log(log)
        cmds = sum(len(e.get("commands", [])) for e in entries)
        daily[day] = {"messages": len(entries), "commands": cmds}

    with _lock:
        _report["daily_stats"]   = daily
        _report["report_built"]  = datetime.now().isoformat()
        _report["uptime_min"]    = _report.get("uptime_min", 0) + 360

    _save_report()
    print("[Brain] Полный отчёт построен")

def _load_log(path: Path) -> list:
    entries = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                try: entries.append(json.loads(line))
                except Exception: pass
    except Exception: pass
    return entries

# ─── Алерты ───────────────────────────────────────────────────────────────────

def _add_alert(level: str, msg: str, ttl: int = None):
    entry = {
        "level": level,
        "msg": msg,
        "ts": datetime.now().strftime("%H:%M"),
        "ttl": ttl,
    }
    with _lock:
        _alerts.append(entry)
        if len(_alerts) > 50:
            _alerts.pop(0)

def _clear_alert(tag: str):
    pass  # упрощённо — алерты не удаляем, просто накапливаем

# ─── Сохранение отчёта на диск ────────────────────────────────────────────────

def _save_report():
    try:
        today = date.today().strftime("%Y%m%d")
        path = REPORTS_DIR / f"report_{today}.json"
        with _lock:
            data = dict(_report)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Brain] Ошибка сохранения отчёта: {e}")
