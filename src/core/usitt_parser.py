# -*- coding: utf-8 -*-
"""
Парсер USITT ASCII файлов из ETC EOS.
Формат EOS:
  Cue 1.5 1             <- номер кью + номер листа
     Text LABEL          <- название
     Chan 211@Hff ...    <- каналы: hex уровень (Hff=100%, H78=47%)
     $$ChanMove ...      <- перемещённые каналы
     $$Param ch p@v ...  <- параметры: channel, param_id@value (1=Intensity)
     $$Block             <- кью заблокирован (все значения зафиксированы)
"""

import re

# Intensity param IDs (cat=1). Cat 1 = Intensity (param_id 1, 281-284 = Intens_5..8)
INTENSITY_PARAM_IDS = {1, 281, 282, 283, 284}

# Категории параметров из $ParamType (cat: 1=Intensity, 2=Focus, 3=Color, 4=Image, 5=Form, 6=Shutter, 7=Control)
PARAM_CATEGORIES = {}  # заполняется при разборе файла


def _hex_to_pct(hval):
    try:
        v = int(hval, 16)
        maxv = 65535 if v > 255 else 255
        return round(v / maxv * 100, 1)
    except (ValueError, TypeError):
        return None


def _parse_chan_tokens(tokens, channels):
    for tok in tokens:
        m = re.match(r'^(\d+)@H([0-9a-fA-F]+)$', tok)
        if m:
            ch = m.group(1)
            pct = _hex_to_pct(m.group(2))
            if pct is not None:
                channels[ch] = pct


def _parse_param_line(rest, param_data):
    """
    Разбирает строку $$Param: "channel_num param_id@value param_id@value ..."
    param_data[ch] = {"intensity": val_or_None, "non_intensity": [param_id, ...]}
    """
    tokens = rest.split()
    if not tokens:
        return
    ch = tokens[0]
    entry = param_data.setdefault(ch, {"intensity": None, "non_intensity": []})
    for tok in tokens[1:]:
        m = re.match(r'^(\d+)@(.+)$', tok)
        if m:
            pid = int(m.group(1))
            val = m.group(2)
            if pid in INTENSITY_PARAM_IDS:
                # значение может быть числом или PRxxx
                try:
                    entry["intensity"] = int(val)
                except ValueError:
                    entry["intensity"] = val
            else:
                if pid not in entry["non_intensity"]:
                    entry["non_intensity"].append(pid)


def parse(text):
    cues = {}
    current_cue = None
    param_categories = {}  # param_id -> category (1=Intensity, 2=Focus, 3=Color...)

    for line in text.splitlines():
        stripped = line.strip()

        # Определение типов параметров: "$ParamType id cat name"
        m = re.match(r'^\$ParamType\s+(\d+)\s+(\d+)\s+', stripped)
        if m:
            param_categories[int(m.group(1))] = int(m.group(2))
            continue

        # Заголовок кью: "Cue 1.5 1"
        m = re.match(r'^Cue\s+([\d.]+)\s+(\d+)', stripped, re.IGNORECASE)
        if m:
            current_cue = m.group(1)
            cue_list = m.group(2)
            if current_cue not in cues:
                cues[current_cue] = {
                    "num": current_cue,
                    "list": cue_list,
                    "label": "",
                    "channels": {},
                    "params": {},   # ch -> {intensity, non_intensity}
                    "is_block": False,
                }
            continue

        if not current_cue:
            continue

        # Название
        m = re.match(r'^(?:\$\$)?Text\s+(.*)', stripped, re.IGNORECASE)
        if m:
            cues[current_cue]["label"] = m.group(1).strip().strip('"')
            continue

        # Block флаг
        if stripped == '$$Block':
            cues[current_cue]["is_block"] = True
            continue

        # Каналы: "Chan 211@Hff 251@Hff ..."
        m = re.match(r'^Chan\s+(.*)', stripped, re.IGNORECASE)
        if m:
            _parse_chan_tokens(m.group(1).split(), cues[current_cue]["channels"])
            continue

        # Перемещённые каналы: "$$ChanMove 5703@H78 ..."
        m = re.match(r'^\$\$ChanMove\s+(.*)', stripped, re.IGNORECASE)
        if m:
            _parse_chan_tokens(m.group(1).split(), cues[current_cue]["channels"])
            continue

        # Параметры: "$$Param channel pid@val pid@val ..."
        m = re.match(r'^\$\$Param\s+(.*)', stripped, re.IGNORECASE)
        if m:
            _parse_param_line(m.group(1), cues[current_cue]["params"])
            continue

    # --- Анализ ---
    all_channels = set()
    for c in cues.values():
        all_channels.update(c["channels"].keys())
        all_channels.update(c["params"].keys())

    # Каналы с intensity=0 но есть non-intensity параметры (фантомные)
    phantom_cues = []
    for num, cue in sorted(cues.items(), key=lambda x: float(x[0])):
        phantom_channels = []
        for ch, pdata in cue["params"].items():
            intensity = pdata["intensity"]
            has_nonint = bool(pdata["non_intensity"])
            # intensity==0 или канал в channels с уровнем 0
            ch_intensity = cue["channels"].get(ch)
            is_dark = (
                intensity == 0 or
                (intensity is None and ch_intensity is not None and ch_intensity == 0.0)
            )
            if is_dark and has_nonint:
                phantom_channels.append({
                    "channel": ch,
                    "param_ids": pdata["non_intensity"]
                })

        if phantom_channels:
            phantom_cues.append({
                "num": num,
                "label": cue["label"],
                "is_block": cue["is_block"],
                "phantom_channels": phantom_channels,
                "phantom_count": len(phantom_channels),
            })

    # Нулевые каналы (intensity=0 в Chan/ChanMove)
    zero_map = {}
    for num, cue in cues.items():
        for ch, pct in cue["channels"].items():
            if pct == 0.0:
                zero_map.setdefault(ch, []).append(num)

    zero_channels = sorted(
        [{"channel": ch, "cues": sorted(lst, key=lambda x: float(x))}
         for ch, lst in zero_map.items()],
        key=lambda x: int(x["channel"])
    )

    empty_cues = sorted(
        [{"num": c["num"], "label": c["label"]}
         for c in cues.values() if not c["channels"] and not c["params"]],
        key=lambda x: float(x["num"])
    )

    chan_usage = {}
    for cue in cues.values():
        for ch, pct in cue["channels"].items():
            if pct > 0:
                chan_usage[ch] = chan_usage.get(ch, 0) + 1

    channel_stats = sorted(
        [{"channel": ch, "cue_count": cnt} for ch, cnt in chan_usage.items()],
        key=lambda x: -x["cue_count"]
    )

    return {
        "cues": {k: {"num": v["num"], "label": v["label"],
                     "channel_count": len(v["channels"]),
                     "is_block": v["is_block"]}
                 for k, v in cues.items()},
        "cue_count": len(cues),
        "channel_count": len(all_channels),
        "zero_channels": zero_channels,
        "phantom_cues": phantom_cues,
        "phantom_cue_count": len(phantom_cues),
        "empty_cues": empty_cues,
        "channel_stats": channel_stats,
    }
