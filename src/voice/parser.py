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
    # Дефис после кью/cue → пробел ("кью-три" → "кью три")
    t = re.sub(r'(кью|cue|kue)[-–]', r'\1 ', t, flags=re.IGNORECASE)
    # Числительные → цифры
    for word, digit in sorted(_WORD_NUMS.items(), key=lambda x: -len(x[0])):
        t = re.sub(r'\b' + word + r'\b', digit, t, flags=re.IGNORECASE)
    # "3 точка 5" или "3 . 5" → "3.5"
    t = re.sub(r'(\d+)\s*(?:точка|\.)\s*(\d+)', r'\1.\2', t)
    return t

# Однозначные команды без параметров — проверяются в первую очередь
SINGLE_PATTERNS = [
    (r"go\s*to\s*(kue|cue|куэ|кью)\s*(out|аут|аута)",  "GO TO CUE OUT"),
    # GO только если НЕТ "to cue N" — иначе перехватит "go to cue 2"
    (r"(\bgo\b|davaj|dal|sled|next|\bго\b|давай|след)(?!\s*to\s*(kue|cue|куэ|кью)\s*\d)", "GO"),
    (r"(stop|stoj|hold|стоп|стой|держи)",                "STOP"),
    (r"(blind|slepoj|слепой|слеп)",                      "BLIND"),
    (r"\b(live|lajv|лайв|лив)\b",                        "LIVE"),
    (r"(obno|update|обнови|обнов)",                      "UPDATE"),
]

# Паттерны с результатом — используются для построения составной команды
PART_PATTERNS = [
    # Подпись CUE: "подпиши/назови CUE 4 как/: МУЗЫКА"
    ("label_cue", r"(podpishi|nazovi|label|подпиши|назови|имя|name)\s*(kue|cue|куэ|кью)?\s*(\d+[.,]?\d*)\s*(kak|как|:)?\s*(.+)",
                  lambda m: "LABEL CUE {} {}".format(m.group(3).replace(",","."), m.group(5).strip())),
    # Перемещение CUE: "перенеси кью 1.4 на 1.41" → CUE 1.4 MOVE TO CUE 1.41
    ("move_cue",  r"(?:перенес[иь]|перемест[иь]|move)\s*(?:kue|cue|куэ|кью)?\s*(\d+[.,]?\d*)\s*(?:на|to|в)\s*(?:kue|cue|куэ|кью)?\s*(\d+[.,]?\d*)",
                  lambda m: "CUE {} MOVE TO CUE {}".format(m.group(1).replace(",","."), m.group(2).replace(",","."))),
    # Установить время кью: "установи/устанавливаю время кью 5 = 3" → CUE 5 TIME 3
    # Охватываем: установи, установить, устанавливаю, установил
    ("set_cue_time", r"(?:установ\w*|устанавл\w*|set|поставь|измен[иь])\s*(?:время|time|врем)\s*(?:на\s*)?(?:kue|cue|куэ|кью)?\s*[-–]?\s*(\d+[.,]?\d*)\s*[-–=]?\s*(\d+[.,]?\d*)",
                  lambda m: "CUE {} TIME {}".format(m.group(1).replace(",","."), m.group(2).replace(",","."))),
    # "кью 1 время 2" / "кью 1 = 2 сек"
    ("set_cue_time2", r"(?:kue|cue|куэ|кью)\s*(\d+[.,]?\d*)\s*[-–=]?\s*(?:время|time|врем)\s*[-–=]?\s*(\d+[.,]?\d*)",
                  lambda m: "CUE {} TIME {}".format(m.group(1).replace(",","."), m.group(2).replace(",","."))),
    # Переход к CUE со временем кью: "перейди на кью 2 со временем кью" → GO TO CUE 2 TIME
    ("goto_cue_time", r"(?:go\s*to\s*(?:kue|cue|куэ|кью)|(?:перейди|перейти|иди|зайди)\s*(?:на\s*)?(?:kue|cue|куэ|кью)?|на\s*кью)\s*(\d+[.,]?\d*)\s*(?:со\s*временем(?:\s*кью)?|with\s*time|с\s*тайм[ао]м?)",
                  lambda m: "GO TO CUE {} TIME".format(m.group(1).replace(",","."))),
    # Переход к CUE с номером (английский, транслит, русский)
    ("goto_cue",  r"(?:go\s*to\s*(?:kue|cue|куэ|кью)|(?:перейди|перейти|иди|зайди|перейд)\s*(?:на\s*)?(?:kue|cue|куэ|кью)?|на\s*кью)\s*(\d+[.,]?\d*)",
                  lambda m: "GO TO CUE {}".format(m.group(1).replace(",","."))),
    # Запись CUE
    ("record_cue",r"(zapis|record|sohrani|запись|запис|сохрани)\s*(kue|cue|куэ|кью)?\s*(\d+[.,]?\d*)",
                  lambda m: "RECORD CUE {}".format(m.group(3).replace(",","."))),
    # CUE по номеру
    ("cue",       r"(kue|cue|kju|куэ|кью|кю)\s*(\d+[.,]?\d*)",
                  lambda m: "CUE {}".format(m.group(2).replace(",","."))),
    # Канал
    ("chan",      r"(kanal|chan|channel|канал)\s*(\d+)",
                  lambda m: "CHAN {}".format(m.group(2))),
    # Субмастер
    ("sub",       r"(sab|sub|саб)\s*(\d+)",
                  lambda m: "SUB {}".format(m.group(2))),
    # Группа
    ("group",     r"(gruppa|group|группа|групп)\s*(\d+)",
                  lambda m: "GROUP {}".format(m.group(2))),
    # Паркинг канала
    ("park",      r"(park|парк)\s*(\d+)",
                  lambda m: "PARK CHAN {}".format(m.group(2))),
    # Макрос
    ("macro",     r"(makro|macro|макро|макрос)\s*(\d+)",
                  lambda m: "MACRO {}".format(m.group(2))),
    # Уровень числом
    ("level",     r"(uroven|level|уровень|уровен)\s*(\d+)\s*(%|proc|проц)?",
                  lambda m: "@ {}".format(m.group(2))),
    # «на 50» / «на 75.5» — только число (не кью-номер после "на")
    ("level_na",  r"\bна\s+([\d]+(?:\.\d+)?)\s*(%|proc|проц)?(?!\s*(?:кью|cue|kue|\d))",
                  lambda m: "@ {}".format(m.group(1))),
    # Полный
    ("full",      r"(polnyj|full|sto\b|полный|полн|сто\b)",  "@ FULL"),
    # Ноль / гасить
    ("zero",      r"(nol|gasi|off|zero|ноль|нол|гаси)",       "@ 0"),
]

def parse(text):
    t  = _normalize_nums(text.lower().strip())
    t0 = text.strip()  # оригинальный регистр (для label)

    # Сначала проверяем однозначные команды (GO, STOP и т.д.)
    for pat, cmd in SINGLE_PATTERNS:
        if re.search(pat, t, re.IGNORECASE):
            return cmd

    # Собираем составную команду из частей
    parts = {}
    for name, pat, action in PART_PATTERNS:
        # для label ищем в оригинале чтобы сохранить регистр
        src = t0 if name == "label_cue" else t
        m = re.search(pat, src, re.IGNORECASE)
        if m:
            parts[name] = action(m) if callable(action) else action

    if not parts:
        return None

    # Приоритет: готовые команды с переходом/записью
    for key in ("label_cue", "move_cue", "set_cue_time", "set_cue_time2", "goto_cue_time", "goto_cue", "record_cue", "macro", "park"):
        if key in parts:
            return parts[key]

    # Субъект (что выбираем) + уровень
    subject = parts.get("chan") or parts.get("sub") or parts.get("group") or parts.get("cue")
    level   = parts.get("level") or parts.get("level_na") or parts.get("full") or parts.get("zero")

    if subject and level:
        return "{} {}".format(subject, level)
    if subject:
        return subject
    if level:
        return level

    return None
