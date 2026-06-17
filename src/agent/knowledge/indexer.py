"""
Индексатор мануала EOS для быстрого поиска релевантных секций.

Вместо того чтобы грузить весь мануал в промпт (дорого и шумно),
агент ищет только нужные разделы по ключевым словам запроса.

Использование:
    idx = ManualIndex()
    sections = idx.search("как перейти на кью 5")
    # → [{"title": "Кью", "content": "GO TO CUE 5..."}]
"""

import re
from pathlib import Path
from typing import List, Dict

KNOWLEDGE_DIR = Path(__file__).parent


class ManualSection:
    def __init__(self, title: str, content: str, level: int, keywords: list):
        self.title = title
        self.content = content
        self.level = level
        self.keywords = keywords  # слова для поиска

    def score(self, query_words: list) -> int:
        """Релевантность: сколько слов запроса попали в заголовок/контент."""
        text = (self.title + " " + " ".join(self.keywords) + " " + self.content).lower()
        return sum(1 for w in query_words if w in text)

    def __repr__(self):
        return f"<Section '{self.title}' [{len(self.content)}c]>"


class ManualIndex:
    def __init__(self):
        self._sections: List[ManualSection] = []
        self._load()

    def _load(self):
        """Загрузить и распарсить все .md файлы из knowledge/."""
        self._sections = []
        for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
            self._parse_file(path)

    def _parse_file(self, path: Path):
        """Разбить markdown файл на секции по заголовкам ##."""
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()

        current_title = path.stem
        current_level = 1
        current_lines = []

        for line in lines:
            m = re.match(r'^(#{1,4})\s+(.+)', line)
            if m:
                # Сохранить предыдущую секцию
                if current_lines:
                    self._add_section(current_title, current_level, "\n".join(current_lines))
                current_level = len(m.group(1))
                current_title = m.group(2).strip()
                current_lines = []
            else:
                current_lines.append(line)

        # Последняя секция
        if current_lines:
            self._add_section(current_title, current_level, "\n".join(current_lines))

    def _add_section(self, title: str, level: int, content: str):
        content = content.strip()
        if not content:
            return
        # Извлечь ключевые слова из заголовка и кода
        keywords = self._extract_keywords(title + " " + content)
        self._sections.append(ManualSection(title, content, level, keywords))

    def _extract_keywords(self, text: str) -> list:
        """Извлечь значимые слова (EOS команды, OSC пути, термины)."""
        words = re.findall(r'[A-Za-zА-Яа-я0-9_/]+', text.lower())
        # Стоп-слова
        stop = {"the","a","an","is","in","of","to","and","or","for","at","on",
                "это","для","что","как","или","при","на","в","из","с","по"}
        return [w for w in words if len(w) > 2 and w not in stop]

    def search(self, query: str, top_n: int = 3, min_score: int = 1) -> List[Dict]:
        """
        Найти наиболее релевантные секции для запроса.

        Returns:
            List[{"title": str, "content": str, "score": int}]
        """
        query_words = self._extract_keywords(query)
        if not query_words:
            return []

        scored = [(s.score(query_words), s) for s in self._sections]
        scored.sort(key=lambda x: -x[0])

        results = []
        for score, section in scored[:top_n]:
            if score >= min_score:
                results.append({
                    "title": section.title,
                    "content": section.content,
                    "score": score,
                })
        return results

    def get_context(self, query: str, max_chars: int = 2000) -> str:
        """
        Получить релевантный контекст из мануала для запроса.
        Возвращает текст для вставки в системный промпт.
        """
        sections = self.search(query, top_n=4)
        if not sections:
            return ""

        parts = []
        total = 0
        for s in sections:
            block = f"### {s['title']}\n{s['content']}"
            if total + len(block) > max_chars:
                break
            parts.append(block)
            total += len(block)

        return "\n\n".join(parts)

    def reload(self):
        """Перечитать файлы (если мануал обновился)."""
        self._load()

    @property
    def stats(self) -> dict:
        return {
            "sections": len(self._sections),
            "total_chars": sum(len(s.content) for s in self._sections),
        }
