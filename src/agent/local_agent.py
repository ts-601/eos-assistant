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

AGENT_DIR   = Path(__file__).parent
MEMORY_DIR  = AGENT_DIR / "memory"
FIXTURES_DIR = AGENT_DIR.parent.parent / "fixtures"

# ─── Фразы подтверждения ──────────────────────────────────────────────────────
_CONFIRM_YES = re.compile(r'\b(да|yes|подтвер|ок|ok|точно|давай|конечно|yep|угу)\b', re.I)
_CONFIRM_NO  = re.compile(r'\b(нет|no|отмен|стоп|не надо|cancel|назад)\b', re.I)

# ─── Паттерны запросов шаблонов/профилей ─────────────────────────────────────
_Q_FIXTURE = re.compile(
    r'(шаблон|профиль|fixture|gdtf|ma2|найди|есть ли|поищи|profile|library|библиотек)',
    re.I
)

# ─── Паттерны вопросов о состоянии пульта ────────────────────────────────────
_Q_CURRENT_CUE = re.compile(r'(какое|текущее|сейчас|активн).{0,20}(кью|cue|куэ)', re.I)
_Q_NEXT_CUE    = re.compile(r'(следующее|next|след).{0,20}(кью|cue|куэ)', re.I)
_Q_CUE_NAME    = re.compile(r'(как\s+называет|что\s+за\s+кью|имя\s+кью|название|name\s+of|label).{0,15}(\d+[\.,]?\d*)', re.I)
_Q_STATUS      = re.compile(r'(состояние|статус|status|подключ|connect|пульт)', re.I)
_Q_MANUAL_CHAN = re.compile(r'(мануальн|manual).{0,15}(канал|chan)', re.I)

# ─── Паттерны опасных команд (требуют подтверждения) ─────────────────────────
_DANGEROUS = re.compile(r'\b(удал[иь]|delete|стер[иь]|убер[иь]|убра[тьи])\b', re.I)
_DELETE_CUE = re.compile(r'(?:удал[иь]|delete)\s*(?:кью|cue|куэ|kue)?\s*(\d+[\.,]?\d*)', re.I)


def _file_matches(filename: str, keywords: list) -> bool:
    # Нормализуем: убираем разделители, сравниваем и слитно и раздельно
    name  = filename.lower().replace('_', ' ').replace('@', ' ').replace('-', ' ').replace('%40', ' ')
    name2 = re.sub(r'\s+', '', name)  # слитно: "light sky" → "lightsky"
    for k in keywords:
        k = k.lower()
        k2 = re.sub(r'\s+', '', k)
        if k in name or k2 in name2 or k in name2:
            return True
    return False


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

        # 5. Попробуем найти в библиотеке шаблонов (вдруг написали название прибора)
        fixture_reply = self._search_fixtures(text)
        if fixture_reply and "нет профилей" not in fixture_reply and "не найдена" not in fixture_reply:
            self._log(text, fixture_reply, [])
            return {"text": fixture_reply, "commands": [], "needs_confirm": False}

        # 6. Не понял
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

        # Поиск шаблонов/профилей приборов
        if _Q_FIXTURE.search(text):
            return self._search_fixtures(text)

        return None

    # ─── Поиск шаблонов приборов ──────────────────────────────────────────────

    def _search_fixtures(self, text: str) -> str:
        if not FIXTURES_DIR.exists():
            return "Папка fixtures/ не найдена в проекте."

        # Извлекаем ключевые слова из запроса (убираем служебные слова)
        stop = r'\b(шаблон|профиль|fixture|gdtf|ma2|найди|есть|ли|поищи|profile|для|под|прибор|есть ли|библиотек\w*)\b'
        query = re.sub(stop, '', text, flags=re.I).strip()
        keywords = [w for w in re.split(r'\W+', query) if len(w) > 2]

        # Общий вопрос "что есть / покажи библиотеку"
        if not keywords or re.search(r'\b(что|все|весь|список|покажи|библиотек)\b', text, re.I):
            return self._fixtures_summary()

        # Ищем по всем файлам в fixtures/
        gdtf_matches, ma2_matches = [], []

        for f in FIXTURES_DIR.glob("GDTF/**/*"):
            if f.is_file() and _file_matches(f.name, keywords):
                gdtf_matches.append(f.name)

        for f in FIXTURES_DIR.glob("MA2_Profiles/**/*.xml"):
            if _file_matches(f.name, keywords):
                ma2_matches.append(f.relative_to(FIXTURES_DIR / "MA2_Profiles"))

        if not gdtf_matches and not ma2_matches:
            return (
                f"В библиотеке нет профилей для **{' '.join(keywords)}**.\n\n"
                "Алгоритм поиска:\n"
                "1. EOS: fixture-library-hub.etcconnect.com\n"
                "2. GDTF Share: gdtf-share.com (искать под точным именем производителя)\n"
                "3. Сайт производителя → MA Share\n\n"
                "Скажи мне название прибора — помогу найти или сгенерировать профиль."
            )

        lines = []
        if gdtf_matches:
            lines.append("**GDTF для EOS:**")
            for f in gdtf_matches:
                lines.append(f"  📄 {f}")
        if ma2_matches:
            lines.append("**MA2 XML профили:**")
            for f in ma2_matches:
                lines.append(f"  📄 {f}")

        lines.append(f"\n_Файлы в `fixtures/` в репозитории_")
        return "\n".join(lines)

    def _fixtures_summary(self) -> str:
        gdtf = list(FIXTURES_DIR.glob("GDTF/**/*"))
        gdtf = [f for f in gdtf if f.is_file()]
        ma2  = list(FIXTURES_DIR.glob("MA2_Profiles/**/*.xml"))
        return (
            f"В библиотеке: **{len(gdtf)} GDTF** файлов и **{len(ma2)} MA2** профилей.\n"
            "Напиши название прибора — найду что есть."
        )

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

    def save_solution(self, title: str, problem: str, solution: str):  # noqa
        pass  # заглушка — локальный агент не использует solutions

    def reload_knowledge(self):
        pass  # нет внешних знаний для перезагрузки
