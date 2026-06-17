# -*- coding: utf-8 -*-
"""
EOS Show Analyzer — запрашивает данные по OSC GET и анализирует шоу.

Основные задачи:
  1. Найти каналы в кью-листе с уровнем 0 (лишние записи)
  2. Найти каналы в пресетах, которые не используются в кью-листе
"""

import threading, time, re
from core import osc_bridge as _bridge

# Хранилище результатов запросов: path -> (args, event)
_pending = {}
_pending_lock = threading.Lock()
_dispatch_hooks = []  # [(pattern_re, callback)]
_hooks_lock = threading.Lock()

def _register_hook(pattern, cb):
    compiled = re.compile(pattern)
    with _hooks_lock:
        _dispatch_hooks.append((compiled, cb))
    return compiled

def _remove_hook(compiled):
    with _hooks_lock:
        _dispatch_hooks[:] = [(p, c) for p, c in _dispatch_hooks if p is not compiled]


def _install_dispatch_hook():
    """Патчим _dispatch в osc_bridge чтобы перехватывать GET-ответы."""
    orig = _bridge._dispatch

    def patched(addr, args):
        orig(addr, args)
        with _hooks_lock:
            hooks = list(_dispatch_hooks)
        for pattern, cb in hooks:
            if pattern.match(addr):
                try:
                    cb(addr, args)
                except Exception as e:
                    print("[Analyzer] hook error:", e)

    _bridge._dispatch = patched

_install_dispatch_hook()


def _osc_get(path, timeout=2.0):
    """Отправить GET-запрос и ждать одного ответа. Возвращает args или None."""
    event = threading.Event()
    result = [None]
    resp_path = path.replace("/eos/get/", "/eos/out/get/")

    def cb(addr, args):
        result[0] = args
        event.set()

    hook = _register_hook("^" + re.escape(resp_path), cb)
    try:
        _bridge._client.send_message(path, [])
        event.wait(timeout)
    finally:
        _remove_hook(hook)
    return result[0]


def _osc_get_multi(path, timeout=3.0):
    """Отправить GET-запрос и собрать ВСЕ ответы по базовому пути в течение timeout."""
    resp_base = path.replace("/eos/get/", "/eos/out/get/")
    results = []
    lock = threading.Lock()

    def cb(addr, args):
        with lock:
            results.append((addr, args))

    hook = _register_hook("^" + re.escape(resp_base), cb)
    try:
        _bridge._client.send_message(path, [])
        time.sleep(timeout)
    finally:
        _remove_hook(hook)
    return results


# ─────────────────────────────────────────────────────────────────────
#  Разбор аргументов кью
# ─────────────────────────────────────────────────────────────────────

def _parse_cue_args(args):
    """
    EOS /eos/out/get/cue/1/<num>/0/list/0/N
    args структура (индексы из документации EOS v3.2.x):
      [0]  = index внутри списка
      [1]  = cue number (float)
      [2]  = label
      [3]  = up time
      [4]  = down time
      [5]  = wait time
      [6]  = follow/hang time
      [7]  = 0/1 = follow/hang flag
      [8]  = flags
      [9]  = scene label
      ...
    Для нас сейчас нужны только label (args[2]) и базовая структура.
    Детальные данные каналов — в sub-запросах ниже.
    """
    if not args or len(args) < 3:
        return {}
    return {
        "num":   str(args[1]) if args[1] is not None else "",
        "label": str(args[2]) if args[2] is not None else "",
    }


def _parse_chan_list_args(args):
    """
    Ответ на /eos/get/cue/1/<num>/0/chan/list/0/N
    Возвращает список (chan_num, level_pct) для каналов в кью.
    Реальный формат EOS: каждый канал — это пара [channel, level].
    EOS может слать несколько сообщений пачками — собираем всё.
    """
    # args может содержать чередующиеся channel/level
    # формат: [count, ch1, lvl1, ch2, lvl2, ...]
    channels = []
    if not args or len(args) < 3:
        return channels
    # первый arg — count или index
    i = 1
    while i + 1 < len(args):
        ch = args[i]
        lvl = args[i + 1]
        i += 2
        try:
            channels.append((int(ch), float(lvl)))
        except (TypeError, ValueError):
            pass
    return channels


# ─────────────────────────────────────────────────────────────────────
#  Публичные функции анализа
# ─────────────────────────────────────────────────────────────────────

def get_cue_channel_data(cue_num, timeout=3.0):
    """
    Запросить список каналов внутри конкретного кью.
    Возвращает список (channel, level_pct) или пустой список.
    """
    path = "/eos/get/cue/1/{}/0/chan/list/0/200".format(cue_num)
    resp_pattern = r"^/eos/out/get/cue/1/{}/0/chan/list/".format(re.escape(str(cue_num)))

    results = []
    lock = threading.Lock()
    done = threading.Event()

    def cb(addr, args):
        chans = _parse_chan_list_args(args)
        with lock:
            results.extend(chans)
        done.set()

    hook = _register_hook(resp_pattern, cb)
    try:
        _bridge._client.send_message(path, [])
        done.wait(timeout)
    finally:
        _remove_hook(hook)
    return results


def get_preset_channel_data(preset_num, timeout=3.0):
    """
    Запросить список каналов в пресете.
    Возвращает список (channel, level_pct).
    """
    path = "/eos/get/preset/{}/0/chan/list/0/200".format(preset_num)
    resp_pattern = r"^/eos/out/get/preset/{}/0/chan/list/".format(re.escape(str(preset_num)))

    results = []
    lock = threading.Lock()
    done = threading.Event()

    def cb(addr, args):
        chans = _parse_chan_list_args(args)
        with lock:
            results.extend(chans)
        done.set()

    hook = _register_hook(resp_pattern, cb)
    try:
        _bridge._client.send_message(path, [])
        done.wait(timeout)
    finally:
        _remove_hook(hook)
    return results


def get_preset_count(timeout=3.0):
    """Вернуть количество пресетов в шоу."""
    args = _osc_get("/eos/get/preset/count", timeout)
    if args and len(args) > 0:
        try:
            return int(args[0])
        except (TypeError, ValueError):
            pass
    return 0


def get_sub_count(timeout=3.0):
    """Вернуть количество субмастеров."""
    args = _osc_get("/eos/get/sub/count", timeout)
    if args and len(args) > 0:
        try:
            return int(args[0])
        except (TypeError, ValueError):
            pass
    return 0


def analyze_cues_zero_channels(progress_cb=None):
    """
    Анализ кью-листа: найти каналы с уровнем 0.
    Возвращает dict: {cue_num: [channel, ...]}
    """
    from core.osc_bridge import get_cue_list
    cues = get_cue_list()
    result = {}

    for i, cue in enumerate(cues):
        num = cue["num"]
        if progress_cb:
            progress_cb(i, len(cues), "Анализирую кью {}".format(num))
        chans = get_cue_channel_data(num, timeout=2.0)
        zero = [ch for ch, lvl in chans if lvl == 0.0]
        if zero:
            result[num] = zero
        time.sleep(0.05)  # не флудить пульт

    return result


def probe_osc_response(cue_num="1"):
    """
    Отладка: посмотреть что именно шлёт EOS на разные GET-запросы для кью.
    Перехватываем всё от EOS за 5 секунд после серии запросов.
    """
    results = []
    lock = threading.Lock()

    def cb(addr, args):
        with lock:
            results.append({"addr": addr, "args": [str(a) for a in args]})

    # Перехватить вообще все пакеты от EOS
    hook = _register_hook(r"^/eos/out/", cb)
    try:
        cn = str(cue_num)
        # Базовый запрос
        _bridge._client.send_message("/eos/get/cue/1/{}".format(cn), [])
        time.sleep(0.2)
        # List с разными индексами
        _bridge._client.send_message("/eos/get/cue/1/{}/0/list/0/50".format(cn), [])
        time.sleep(0.2)
        # Попробуем прямой канал
        for ch in [1, 2, 3]:
            _bridge._client.send_message("/eos/get/cue/1/{}/0/chan/{}".format(cn, ch), [])
        time.sleep(0.2)
        # Список каналов через chan/list
        _bridge._client.send_message("/eos/get/cue/1/{}/0/chan/list/0/100".format(cn), [])
        time.sleep(0.2)
        # Sub-index для каналов (index 1..5)
        for idx in range(1, 6):
            _bridge._client.send_message("/eos/get/cue/1/{}/0/list/{}/1".format(cn, idx), [])
        time.sleep(2.0)
    finally:
        _remove_hook(hook)
    return results
