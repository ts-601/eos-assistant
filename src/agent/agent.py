"""
EOS Assistant Agent — умный агент с памятью и самообучением.

Отличие от простого ChatBot:
- Читает мануал и правила при старте
- Запоминает решения проблем в папку solutions/
- Анализирует контекст EOS перед ответом
- Уточняет неоднозначные запросы
- Учится на ошибках
"""

import os
import json
import time
import anthropic
from datetime import datetime
from pathlib import Path
from agent.knowledge.indexer import ManualIndex
import agent.sandbox as sandbox

AGENT_DIR   = Path(__file__).parent
KNOWLEDGE   = AGENT_DIR / "knowledge"
MEMORY_DIR  = AGENT_DIR / "memory"
SOLUTIONS   = AGENT_DIR / "solutions"

MODEL = "claude-sonnet-4-6"

class EOSAgent:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self._index      = ManualIndex()
        self._rules      = self._load_file(KNOWLEDGE / "agent_rules.md")
        self._solutions  = self._load_solutions()
        self._session_log = []
        print(f"[Agent] Индекс мануала: {self._index.stats}")

    # ─── Загрузка знаний ──────────────────────────────────────────────────────

    @property
    def sandbox_enabled(self) -> bool:
        return sandbox.is_enabled()

    def set_sandbox(self, enabled: bool):
        sandbox.enable() if enabled else sandbox.disable()

    def _load_file(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ""

    def _load_solutions(self) -> str:
        """Загрузить все записанные решения."""
        if not SOLUTIONS.exists():
            return ""
        texts = []
        for f in sorted(SOLUTIONS.glob("*.md"))[-10:]:  # последние 10
            texts.append(f"### {f.stem}\n" + f.read_text(encoding="utf-8"))
        return "\n\n".join(texts)

    def _build_system_prompt(self, eos_state: dict, query: str = "", cue_list: dict = None) -> str:
        """Собрать системный промпт с актуальным контекстом."""
        state_str = json.dumps(eos_state, ensure_ascii=False, indent=2)
        solutions_block = f"\n## Записанные решения\n{self._solutions}" if self._solutions else ""
        sandbox_block = "\n⚠ РЕЖИМ ПЕСОЧНИЦЫ АКТИВЕН — команды не отправляются на реальный пульт." if sandbox.is_enabled() else ""

        # Индексный поиск: только релевантные секции мануала
        manual_context = self._index.get_context(query, max_chars=2500) if query else self._index.get_context("cue go chan", max_chars=1500)

        # Кью-лист для ответов на вопросы о названиях кью
        cue_block = ""
        if cue_list:
            items = cue_list if isinstance(cue_list, list) else sorted(cue_list.values(), key=lambda x: float(x['num']))
            lines = [f"  {v['num']}: {v.get('label','—')} {('/ '+v['notes']) if v.get('notes') else ''}" for v in items]
            cue_block = "\n## Кью-лист (названия и заметки)\n" + "\n".join(lines[:40])

        return f"""Ты — EOS Agent, оператор светового пульта ETC EOS.
{sandbox_block}

## Текущее состояние пульта
```json
{state_str}
```
{cue_block}

## Релевантные разделы мануала EOS
{manual_context}

## Правила работы
{self._rules}
{solutions_block}

## Твоя задача
1. Анализируй запрос в контексте состояния пульта и кью-листа
2. Если спрашивают НАЗВАНИЕ/ОПИСАНИЕ кью — отвечай текстом из кью-листа выше, НЕ отправляй команду CUE
3. Если запрос неоднозначен — уточни, не выполняй вслепую
4. Отвечай на русском, кратко

## ⚠ ОБЯЗАТЕЛЬНО: опасные команды
DELETE CUE, RECORD (перезапись), массовые изменения — ТОЛЬКО после явного "да" от пользователя.
Не вкладывай <cmd> с DELETE до подтверждения. Сначала спроси: "Удалить кью X? (да/нет)"

## Формат команды
<cmd>{{"cmd": "GO TO CUE 5"}}</cmd>
"""

    # ─── Основной цикл ────────────────────────────────────────────────────────

    def chat(self, user_message: str, eos_state: dict, history: list, cue_list: dict = None) -> dict:
        """
        Обработать сообщение пользователя.

        Returns:
            {
                "text": str,           — текст ответа
                "commands": [str],     — команды для выполнения на EOS
                "needs_confirm": bool, — нужно ли подтверждение
                "save_solution": str,  — если агент хочет сохранить решение
            }
        """
        system = self._build_system_prompt(eos_state, query=user_message, cue_list=cue_list)

        # Строим историю для API
        messages = []
        for entry in history[-10:]:  # последние 10 сообщений
            messages.append({"role": entry["role"], "content": entry["content"]})
        messages.append({"role": "user", "content": user_message})

        try:
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=system,
                messages=messages,
            )
            text = response.content[0].text
        except Exception as e:
            return {"text": f"⚠ Ошибка API: {e}", "commands": [], "needs_confirm": False}

        # Парсим команды из ответа
        import re
        cmd_matches = re.findall(r'<cmd>(.*?)</cmd>', text, re.DOTALL)
        commands = []
        for m in cmd_matches:
            try:
                obj = json.loads(m.strip())
                if "cmd" in obj:
                    commands.append(obj["cmd"])
            except Exception:
                pass

        # Убираем теги из текста
        clean_text = re.sub(r'<cmd>.*?</cmd>', '', text, flags=re.DOTALL)
        clean_text = re.sub(r'<learn>.*?</learn>', '', clean_text, flags=re.DOTALL).strip()

        # Автосохранение решения из тега <learn>
        learn_match = re.search(r'<learn>(.*?)</learn>', text, re.DOTALL)
        if learn_match:
            self._auto_learn(user_message, learn_match.group(1).strip())

        # Логируем
        self._log(user_message, clean_text, commands)

        return {
            "text": clean_text,
            "commands": commands,
            "needs_confirm": False,
        }

    # ─── Память и обучение ────────────────────────────────────────────────────

    def _auto_learn(self, user_message: str, learn_block: str):
        """Автоматически сохранить решение из тега <learn>."""
        lines = {l.split(':', 1)[0].strip(): l.split(':', 1)[1].strip()
                 for l in learn_block.splitlines() if ':' in l}
        title    = lines.get('title', user_message[:40])
        problem  = lines.get('problem', user_message)
        solution = lines.get('solution', learn_block)
        self.save_solution(title, problem, solution)

    def save_solution(self, title: str, problem: str, solution: str):
        """Записать найденное решение в базу знаний."""
        SOLUTIONS.mkdir(exist_ok=True)
        date = datetime.now().strftime("%Y-%m-%d")
        slug = title.lower().replace(" ", "_")[:40]
        path = SOLUTIONS / f"{date}_{slug}.md"
        content = f"# {title}\n\n**Проблема:** {problem}\n\n**Решение:** {solution}\n\n*Записано: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n"
        path.write_text(content, encoding="utf-8")
        self._solutions = self._load_solutions()  # обновить кэш
        print(f"[Agent] Решение записано: {path.name}")

    def _log(self, user_msg: str, reply: str, commands: list):
        entry = {
            "ts": datetime.now().isoformat(),
            "user": user_msg,
            "reply": reply[:200],
            "commands": commands,
        }
        self._session_log.append(entry)
        # Записываем лог сессии
        MEMORY_DIR.mkdir(exist_ok=True)
        log_path = MEMORY_DIR / f"session_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def reload_knowledge(self):
        """Перечитать мануал и решения (если файлы изменились)."""
        self._manual    = self._load_file(KNOWLEDGE / "eos_manual.md")
        self._rules     = self._load_file(KNOWLEDGE / "agent_rules.md")
        self._solutions = self._load_solutions()
        print("[Agent] Знания перезагружены")
