# -*- coding: utf-8 -*-
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

_WORD_NUMS = {
    "ноль":"0","нуль":"0","один":"1","одна":"1","два":"2","две":"2","три":"3",
    "четыре":"4","пять":"5","шесть":"6","семь":"7","восемь":"8","девять":"9",
    "десять":"10","одиннадцать":"11","двенадцать":"12","тринадцать":"13",
    "четырнадцать":"14","пятнадцать":"15","шестнадцать":"16","семнадцать":"17",
    "восемнадцать":"18","девятнадцать":"19","двадцать":"20",
    "zero":"0","one":"1","two":"2","three":"3","four":"4","five":"5",
    "six":"6","seven":"7","eight":"8","nine":"9","ten":"10",
}

def _normalize_nums(t):
    """Заменить числительные на цифры (поддержка 'три точка пять' → '3.5')."""
    t = re.sub(r'(кью|cue|kue)[-–]', r'\1 ', t, flags=re.IGNORECASE)
    # Убираем слово "номер" перед числом: "канал номер 3" → "канал 3"
    t = re.sub(r'\b(номер|number|№)\s*', '', t, flags=re.IGNORECASE)
    for word, digit in sorted(_WORD_NUMS.items(), key=lambda x: -len(x[0])):
        t = re.sub(r'\b' + word + r'\b', digit, t, flags=re.IGNORECASE)
    t = re.sub(r'(\d+)\s*(?:точка|\.)\s*(\d+)', r'\1.\2', t)
    return t

# ── Однозначные команды ───────────────────────────────────────────────────────
SINGLE_PATTERNS = [
    (r"\b(sneak|сник|sneik)\b",                             "SNEAK"),
    (r"go\s*to\s*(kue|cue|куэ|кью)\s*(out|аут|аута)",      "GO TO CUE OUT"),
    (r"(?:перейди|иди|на)\s*(?:кью|cue|kue)?\s*(out|аут|аута|ноль|нуль|нул)", "GO TO CUE OUT"),
    # GO — только отдельное слово, не часть вопроса
    (r"(\bgo\b|davaj|dal|\bsled\b|\bnext\b|\bго\b|давай|\bслед\b)(?!\s*to\s*(kue|cue|куэ|кью)\s*\d)(?!\w)", "GO"),
    # BACK — вернуться на предыдущее кью
    (r"\b(back|назад|вернись|вернуться)\b",                 "BACK"),
    (r"(stop|stoj|hold|стоп|стой|держи)",                   "STOP"),
    (r"(blind|slepoj|слепой|слеп)",                         "BLIND"),
    (r"\b(live|lajv|лайв|лив)\b",                           "LIVE"),
    (r"(obno|update|обнови|обнов)",                         "UPDATE"),
    # ASSERT — утвердить трекинг
    (r"\b(assert|ассерт|утверди|подтверди трекинг)\b",      "ASSERT"),
    # HOME — на начало кью-листа
    (r"\b(home|хоум|начало списка)\b",                      "HOME"),
    # SELECT ACTIVE
    (r"(select\s*active|выбери\s*активн|выбрать\s*активн)", "SELECT ACTIVE"),
]

# ── Паттерны с параметрами ────────────────────────────────────────────────────
PART_PATTERNS = [
    # Подпись CUE
    ("label_cue",
     r"(podpishi|nazovi|label|подпиши|назови|имя|name)\s*(kue|cue|куэ|кью)?\s*(\d+[.,]?\d*)\s*(kak|как|:)?\s*(.+)",
     lambda m: "LABEL CUE {} {}".format(m.group(3).replace(",","."), m.group(5).strip())),

    # Перемещение CUE
    ("move_cue",
     r"(?:перенес[иь]|перемест[иь]|move)\s*(?:kue|cue|куэ|кью)?\s*(\d+[.,]?\d*)\s*(?:на|to|в)\s*(?:kue|cue|куэ|кью)?\s*(\d+[.,]?\d*)",
     lambda m: "CUE {} MOVE TO CUE {}".format(m.group(1).replace(",","."), m.group(2).replace(",","."))),

    # Копирование CUE
    ("copy_cue",
     r"(?:скопи\w+|copy)\s*(?:kue|cue|куэ|кью)?\s*(\d+[.,]?\d*)\s*(?:на|to|в)\s*(?:kue|cue|куэ|кью)?\s*(\d+[.,]?\d*)",
     lambda m: "CUE {} COPY TO CUE {}".format(m.group(1).replace(",","."), m.group(2).replace(",","."))),

    # Время кью: "установи время кью 5 = 3"
    ("set_cue_time",
     r"(?:установ\w*|устанавл\w*|set|поставь|измен[иь])\s*(?:время|time|врем)\s*(?:на\s*)?(?:kue|cue|куэ|кью)?\s*[-–]?\s*(\d+[.,]?\d*)\s*[-–=]?\s*(\d+[.,]?\d*)",
     lambda m: "CUE {} TIME {}".format(m.group(1).replace(",","."), m.group(2).replace(",","."))),

    # Время кью: "кью 5 время 3"
    ("set_cue_time2",
     r"(?:kue|cue|куэ|кью)\s*(\d+[.,]?\d*)\s*[-–=]?\s*(?:время|time|врем)\s*[-–=]?\s*(\d+[.,]?\d*)",
     lambda m: "CUE {} TIME {}".format(m.group(1).replace(",","."), m.group(2).replace(",","."))),

    # GO TO CUE со временем
    ("goto_cue_time",
     r"(?:go\s*to\s*(?:kue|cue|куэ|кью)|(?:перейди|перейти|иди|зайди)\s*(?:на\s*)?(?:kue|cue|куэ|кью)?|на\s*кью)\s*(\d+[.,]?\d*)\s*(?:со\s*временем(?:\s*кью)?|with\s*time|с\s*тайм[ао]м?)",
     lambda m: "GO TO CUE {} TIME".format(m.group(1).replace(",","."))),

    # GO TO CUE
    ("goto_cue",
     r"(?:go\s*to\s*(?:kue|cue|куэ|кью)|(?:перейди|перейти|иди|зайди|перейд)\s*(?:на\s*)?(?:kue|cue|куэ|кью)?|на\s*кью)\s*(\d+[.,]?\d*)",
     lambda m: "GO TO CUE {}".format(m.group(1).replace(",","."))),

    # RECORD CUE
    ("record_cue",
     r"(zapis|record|sohrani|запиши|запись|запис|сохрани)\s*(kue|cue|куэ|кью)?\s*(\d+[.,]?\d*)",
     lambda m: "RECORD CUE {}".format(m.group(3).replace(",","."))),

    # PRESET
    ("preset",
     r"(preset|пресет|пресет)\s*(\d+)",
     lambda m: "PRESET {}".format(m.group(2))),

    # COLOR PALETTE
    ("color_palette",
     r"(?:цвет\w*\s*палитр\w*|color\s*palette)\s*(\d+)",
     lambda m: "COLOR PALETTE {}".format(m.group(1))),

    # FOCUS PALETTE
    ("focus_palette",
     r"(?:фокус\w*\s*палитр\w*|focus\s*palette)\s*(\d+)",
     lambda m: "FOCUS PALETTE {}".format(m.group(1))),

    # PARK CHAN — паркинг, обязательно до "chan" чтобы не урезать
    ("park",
     r"(park|запорку\w*|парку\w+|паркан\w+|парк[ауни]*)\s*(?:канал|chan|channel)?\s*(\d+)",
     lambda m: "PARK CHAN {}".format(m.group(2))),

    # CHAN THRU: "канал 1 по 10" / "канал 1 thru 10"
    ("chan_thru",
     r"(?:kanal|chan|channel|канал)\s*(\d+)\s*(?:по|thru|до|through|-)\s*(\d+)",
     lambda m: "CHAN {} THRU {}".format(m.group(1), m.group(2))),

    # CUE по номеру
    ("cue",
     r"(kue|cue|kju|куэ|кью|кю)\s*(\d+[.,]?\d*)",
     lambda m: "CUE {}".format(m.group(2).replace(",","."))),

    # Канал (одиночный)
    ("chan",
     r"(kanal|chan|channel|канал)\s*(\d+)",
     lambda m: "CHAN {}".format(m.group(2))),

    # Субмастер
    ("sub",
     r"(sab|sub|саб|фейдер|fader)\s*(\d+)",
     lambda m: "SUB {}".format(m.group(2))),

    # Группа
    ("group",
     r"(gruppa|group|группа|групп)\s*(\d+)",
     lambda m: "GROUP {}".format(m.group(2))),

    # Макрос
    ("macro",
     r"(makro|macro|макро|макрос)\s*(\d+)",
     lambda m: "MACRO {}".format(m.group(2))),

    # Относительный уровень: "+10" / "плюс 10" / "минус 5"
    ("level_rel",
     r"(?:\+|(плюс|plus))\s*(\d+)|(-|(минус|minus))\s*(\d+)",
     lambda m: "@ +{}".format(m.group(2)) if (m.group(1) or m.group(0).startswith('+')) else "@ -{}".format(m.group(5) or m.group(2))),

    # Уровень словом
    ("level",
     r"(uroven|level|уровень|уровен)\s*(\d+)\s*(%|proc|проц)?",
     lambda m: "@ {}".format(m.group(2))),

    # «на 50» — только число
    ("level_na",
     r"\bна\s+([\d]+(?:\.\d+)?)\s*(%|proc|проц)?(?!\s*(?:кью|cue|kue|\d))",
     lambda m: "@ {}".format(m.group(1))),

    # FULL / OUT
    ("full", r"(polnyj|full|sto\b|полный|полн|сто\b)",  "@ FULL"),
    ("zero", r"(nol|gasi|off|zero|ноль|нол|гаси)",       "@ 0"),
]

def parse(text):
    t  = _normalize_nums(text.lower().strip())
    t0 = text.strip()

    # Вопросы → LocalAgent отвечает текстом
    if re.search(r'\b(как\s+называет|что\s+за\s+кью|имя\s+кью|название\s+кью|name\s+of\s+cue|label\s+of\s+cue|расскаж|опиши\s+кью|что\s+такое\s+кью)', t):
        return None

    # Удаление → LocalAgent просит подтверждение
    if re.search(r'\b(удал[иь]|delete|стер[иь]|убер[иь]|убра[тьи])\b', t):
        return None

    # Однозначные команды
    for pat, cmd in SINGLE_PATTERNS:
        if re.search(pat, t, re.IGNORECASE):
            return cmd

    # Составная команда из частей
    parts = {}
    for name, pat, action in PART_PATTERNS:
        src = t0 if name == "label_cue" else t
        m = re.search(pat, src, re.IGNORECASE)
        if m:
            parts[name] = action(m) if callable(action) else action

    if not parts:
        return None

    # Приоритет готовых команд
    for key in ("label_cue", "move_cue", "copy_cue", "set_cue_time", "set_cue_time2",
                "goto_cue_time", "goto_cue", "record_cue", "preset",
                "color_palette", "focus_palette", "macro", "park"):
        if key in parts:
            return parts[key]

    # CHAN THRU + уровень: "канал 1 по 10 на 50" → "CHAN 1 THRU 10 @ 50"
    if "chan_thru" in parts:
        level = parts.get("level") or parts.get("level_na") or parts.get("full") or parts.get("zero")
        return "{} {}".format(parts["chan_thru"], level) if level else parts["chan_thru"]

    # Субъект + уровень
    subject = parts.get("chan") or parts.get("sub") or parts.get("group") or parts.get("cue")
    level   = (parts.get("level_rel") or parts.get("level") or
               parts.get("level_na") or parts.get("full") or parts.get("zero"))

    if subject and level:
        return "{} {}".format(subject, level)
    if subject:
        return subject
    if level:
        return level

    return None
