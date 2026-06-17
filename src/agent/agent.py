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

AGENT_DIR   = Path(__file__).parent
KNOWLEDGE   = AGENT_DIR / "knowledge"
MEMORY_DIR  = AGENT_DIR / "memory"
SOLUTIONS   = AGENT_DIR / "solutions"

MODEL = "claude-sonnet-4-6"

class EOSAgent:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self._manual     = self._load_file(KNOWLEDGE / "eos_manual.md")
        self._rules      = self._load_file(KNOWLEDGE / "agent_rules.md")
        self._solutions  = self._load_solutions()
        self._session_log = []

    # ─── Загрузка знаний ──────────────────────────────────────────────────────

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

    def _build_system_prompt(self, eos_state: dict) -> str:
        """Собрать системный промпт с актуальным контекстом."""
        state_str = json.dumps(eos_state, ensure_ascii=False, indent=2)
        solutions_block = f"\n## Записанные решения\n{self._solutions}" if self._solutions else ""

        return f"""Ты — умный ассистент светового пульта ETC EOS.

## Текущее состояние пульта
```json
{state_str}
```

## Мануал EOS (твоя база знаний)
{self._manual}

## Правила работы
{self._rules}
{solutions_block}

## Твоя задача
1. Анализируй запрос пользователя в контексте текущего состояния пульта
2. Если запрос неоднозначен — уточни (не выполняй вслепую)
3. Если знаешь решение — выполни и объясни кратко
4. Если встретил новую проблему и нашёл решение — попроси меня записать его
5. Отвечай на русском, кратко и по делу

## Формат команды для выполнения
Если нужно выполнить команду на пульте — верни JSON в теге <cmd>:
<cmd>{{"cmd": "GO TO CUE 5"}}</cmd>

Можно несколько команд:
<cmd>{{"cmd": "GO TO CUE OUT"}}</cmd>
<cmd>{{"cmd": "BLIND"}}</cmd>

Если команда опасная (DELETE, массовые изменения) — сначала спроси подтверждение,
не вкладывай <cmd> до получения "да".
"""

    # ─── Основной цикл ────────────────────────────────────────────────────────

    def chat(self, user_message: str, eos_state: dict, history: list) -> dict:
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
        system = self._build_system_prompt(eos_state)

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

        # Убираем теги cmd из текста
        clean_text = re.sub(r'<cmd>.*?</cmd>', '', text, flags=re.DOTALL).strip()

        # Проверяем хочет ли агент сохранить решение
        save_solution = None
        if "[SAVE_SOLUTION:" in text:
            m = re.search(r'\[SAVE_SOLUTION:(.*?)\]', text)
            if m:
                save_solution = m.group(1).strip()
                clean_text = clean_text.replace(m.group(0), "").strip()

        # Логируем
        self._log(user_message, clean_text, commands)

        return {
            "text": clean_text,
            "commands": commands,
            "needs_confirm": False,
            "save_solution": save_solution,
        }

    # ─── Память и обучение ────────────────────────────────────────────────────

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
