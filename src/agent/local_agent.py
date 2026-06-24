# -*- coding: utf-8 -*-
"""
LocalAgent — бесплатная замена EOSAgent без API.
Использует voice/parser.py для парсинга команд + прямые ответы по контексту.
"""
import re
import json
from datetime import datetime
from pathlib import Path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from voice.parser import parse as _parse_cmd
import agent.sandbox as sandbox

AGENT_DIR = Path(__file__).parent
MEMORY_DIR = AGENT_DIR / "memory"

# ─── Фразы подтверждения ──────────────────────────────────────────────────────
_CONFIRM_YES = re.compile(r'\b(да|yes|подтвер|ок|ok|точно|давай|конечно|yep|угу)\b', re.I)
_CONFIRM_NO  = re.compile(r'\b(нет|no|отмен|стоп|не надо|cancel|назад)\b', re.I)

# ─── Паттерны вопросов о состоянии пульта ────────────────────────────────────
_Q_CURRENT_CUE = re.compile(r'(какое|текущее|сейчас|активн).{0,20}(кью|cue|куэ)', re.I)
_Q_NEXT_CUE    = re.compile(r'(следующее|next|след).{0,20}(кью|cue|куэ)', re.I)
_Q_CUE_NAME    = re.compile(r'(как\s+называет|что\s+за\s+кью|имя\s+кью|название|name\s+of|label).{0,15}(\d+[\.,]?\d*)', re.I)
_Q_STATUS      = re.compile(r'(состояние|статус|status|подключ|connect|пульт)', re.I)
_Q_MANUAL_CHAN = re.compile(r'(мануальн|manual).{0,15}(канал|chan)', re.I)

# ─── Паттерны опасных команд (требуют подтверждения) ─────────────────────────
_DANGEROUS = re.compile(r'\b(удал[иь]|delete|стер[иь]|убер[иь]|убра[тьи])\b', re.I)
_DELETE_CUE = re.compile(r'(?:удал[иь]|delete)\s*(?:кью|cue|куэ|kue)?\s*(\d+[\.,]?\d*)', re.I)


class LocalAgent:
    """Агент без API — парсит команды локально, отвечает по контексту."""

    def __init__(self):
        self._pending_confirm = None  # команда ожидающая подтверждения
        self._session_log = []

    @property
    def sandbox_enabled(self) -> bool:
        return sandbox.is_enabled()

    def set_sandbox(self, enabled: bool):
        sandbox.enable() if enabled else sandbox.disable()

    # ─── Главный метод ────────────────────────────────────────────────────────

    def chat(self, user_message: str, eos_state: dict, history: list, cue_list: dict = None) -> dict:
        text = user_message.strip()

        # 1. Ждём подтверждения опасной команды?
        if self._pending_confirm:
            return self._handle_confirm(text)

        # 2. Вопросы о состоянии пульта (отвечаем текстом, без команды)
        answer = self._try_answer_question(text, eos_state, cue_list)
        if answer:
            self._log(text, answer, [])
            return {"text": answer, "commands": [], "needs_confirm": False}

        # 3. Опасные команды — попросить подтверждение
        if _DANGEROUS.search(text):
            return self._handle_dangerous(text)

        # 4. Парсим команду
        cmd = _parse_cmd(text)
        if cmd:
            sandbox_note = " *(режим песочницы — пульт не изменится)*" if sandbox.is_enabled() else ""
            reply = f"Отправляю: `{cmd}`{sandbox_note}"
            self._log(text, reply, [cmd])
            return {"text": reply, "commands": [cmd], "needs_confirm": False}

        # 5. Не понял
        reply = self._not_understood(text)
        self._log(text, reply, [])
        return {"text": reply, "commands": [], "needs_confirm": False}

    # ─── Ответы на вопросы ────────────────────────────────────────────────────

    def _try_answer_question(self, text: str, eos_state: dict, cue_list: dict) -> str | None:
        # Статус подключения
        if _Q_STATUS.search(text):
            ok = eos_state.get("eos_ok", False)
            show = eos_state.get("show_name", "—")
            cue  = eos_state.get("active_cue", "—")
            status = "подключён ✓" if ok else "нет связи ✗"
            return f"Пульт: {status}\nШоу: {show}\nАктивное кью: {cue}"

        # Текущее кью
        if _Q_CURRENT_CUE.search(text):
            cue  = eos_state.get("active_cue", "—")
            label = eos_state.get("active_cue_text", "")
            return f"Активное кью: **{cue}**" + (f" — {label}" if label else "")

        # Следующее кью
        if _Q_NEXT_CUE.search(text):
            cue = eos_state.get("pending_cue", "—")
            label = eos_state.get("pending_cue_text", "")
            return f"Следующее кью: **{cue}**" + (f" — {label}" if label else "")

        # Название конкретного кью из списка
        m = _Q_CUE_NAME.search(text)
        if m and cue_list:
            num = m.group(2).replace(",", ".")
            entry = cue_list.get(num) or cue_list.get(num.lstrip("0"))
            if entry:
                label = entry.get("label", "—")
                notes = entry.get("notes", "")
                return f"Кью {num}: **{label}**" + (f"\n{notes}" if notes else "")
            return f"Кью {num} не найдено в списке."

        # Мануальные каналы
        if _Q_MANUAL_CHAN.search(text):
            chans = eos_state.get("manual_channels", {})
            if not chans:
                return "Мануальных каналов нет."
            lines = [f"Канал {ch}: {v}%" for ch, v in sorted(chans.items(), key=lambda x: int(x[0]))]
            return "Мануальные каналы:\n" + "\n".join(lines)

        return None

    # ─── Опасные команды ──────────────────────────────────────────────────────

    def _handle_dangerous(self, text: str) -> dict:
        m = _DELETE_CUE.search(text)
        if m:
            num = m.group(1).replace(",", ".")
            cmd = f"DELETE CUE {num}"
            self._pending_confirm = cmd
            reply = f"⚠ Удалить кью {num}? Это нельзя отменить.\nОтветь **да** для подтверждения или **нет** для отмены."
            return {"text": reply, "commands": [], "needs_confirm": True}

        self._pending_confirm = None
        return {"text": "Эта команда требует уточнения. Напиши точнее что удалить.", "commands": [], "needs_confirm": False}

    def _handle_confirm(self, text: str) -> dict:
        cmd = self._pending_confirm
        self._pending_confirm = None

        if _CONFIRM_YES.search(text):
            reply = f"Отправляю: `{cmd}`"
            self._log(text, reply, [cmd])
            return {"text": reply, "commands": [cmd], "needs_confirm": False}

        if _CONFIRM_NO.search(text):
            return {"text": "Отменено.", "commands": [], "needs_confirm": False}

        # Непонятный ответ — снова спросить
        self._pending_confirm = cmd
        return {"text": f"Не понял. Подтвердить `{cmd}`? Ответь **да** или **нет**.", "commands": [], "needs_confirm": True}

    # ─── Подсказка при непонимании ────────────────────────────────────────────

    def _not_understood(self, text: str) -> str:
        return (
            "Не понял команду. Примеры:\n"
            "• `кью 5` — выбрать кью 5\n"
            "• `перейди на кью 3` — GO TO CUE 3\n"
            "• `канал 10 на 75` — CHAN 10 @ 75\n"
            "• `go` / `стоп` / `blind`\n"
            "• `как называется кью 3?`\n"
            "• `статус пульта`"
        )

    # ─── Логирование ──────────────────────────────────────────────────────────

    def _log(self, user_msg: str, reply: str, commands: list):
        entry = {
            "ts": datetime.now().isoformat(),
            "user": user_msg,
            "reply": reply[:200],
            "commands": commands,
        }
        self._session_log.append(entry)
        MEMORY_DIR.mkdir(exist_ok=True)
        log_path = MEMORY_DIR / f"session_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def save_solution(self, title: str, problem: str, solution: str):
        pass  # заглушка — локальный агент не использует solutions

    def reload_knowledge(self):
        pass  # нет внешних знаний для перезагрузки
