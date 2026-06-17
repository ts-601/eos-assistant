"""
Песочница агента — режим где команды не идут на реальный пульт.

Использование:
  sandbox = Sandbox()
  sandbox.enable()   # включить
  sandbox.disable()  # выключить
  sandbox.execute("GO TO CUE 5")  # вернёт симулированный ответ
"""

import json
from datetime import datetime
from pathlib import Path

SANDBOX_LOG = Path(__file__).parent / "memory" / "sandbox_log.jsonl"

# Команды которые безопасно симулировать
_SAFE_RESPONSES = {
    "GO":          "✓ [SANDBOX] GO — переход на следующий кью",
    "STOP":        "✓ [SANDBOX] STOP — стоп",
    "BLIND":       "✓ [SANDBOX] Режим BLIND включён",
    "LIVE":        "✓ [SANDBOX] Режим LIVE включён",
    "UPDATE":      "✓ [SANDBOX] Кью обновлён",
    "UNDO":        "✓ [SANDBOX] Отмена действия",
}

_enabled = False


def is_enabled() -> bool:
    return _enabled


def enable():
    global _enabled
    _enabled = True
    print("[Sandbox] ВКЛЮЧЕНА — команды не отправляются на пульт")


def disable():
    global _enabled
    _enabled = False
    print("[Sandbox] Выключена — команды идут на реальный пульт")


def execute(cmd: str) -> dict:
    """
    Симулировать выполнение команды в песочнице.
    Возвращает {ok, result, cmd, sandbox: True}
    """
    cmd = cmd.strip().upper()
    # Найти подходящий шаблон ответа
    result = None
    for key, resp in _SAFE_RESPONSES.items():
        if cmd.startswith(key):
            result = resp
            break

    if result is None:
        result = f"✓ [SANDBOX] Команда принята: {cmd} (не выполнена на пульте)"

    # Специальные случаи
    if cmd.startswith("GO TO CUE"):
        parts = cmd.split()
        cue = parts[-1] if len(parts) > 3 else "?"
        result = f"✓ [SANDBOX] GO TO CUE {cue} — переход на кью (симуляция)"
    elif cmd.startswith("CHAN") and "@" in cmd:
        result = f"✓ [SANDBOX] {cmd} — уровень канала установлен (симуляция)"
    elif cmd.startswith("RECORD CUE"):
        result = f"⚠ [SANDBOX] RECORD CUE — запись заблокирована в режиме песочницы"
    elif cmd.startswith("DELETE"):
        result = f"⚠ [SANDBOX] DELETE заблокирован в режиме песочницы"

    # Логируем
    _log(cmd, result)
    return {"ok": True, "sandbox": True, "cmd": cmd, "result": result}


def _log(cmd: str, result: str):
    SANDBOX_LOG.parent.mkdir(exist_ok=True)
    entry = {"ts": datetime.now().isoformat(), "cmd": cmd, "result": result}
    with open(SANDBOX_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def get_log(n: int = 20) -> list:
    """Получить последние n записей из лога песочницы."""
    if not SANDBOX_LOG.exists():
        return []
    lines = SANDBOX_LOG.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(l) for l in lines[-n:]]
