import threading, time, socket as _socket, struct as _struct
import config as config
from config import EOS_IP, EOS_OSC_PORT, EOS_RX_PORT, EOS_USER_ID

EOS_TCP_PORT = 3032  # EOS TCP OSC server port

_tcp_sock = None
_tcp_lock = threading.Lock()
_cmd_lock = threading.Lock()

_KEY_PATH = "/eos/user/{}/key/".format(EOS_USER_ID)
_CMD_PATH = "/eos/user/{}/cmd".format(EOS_USER_ID)

# Фейдерный банк
FADER_BANK = 1
FADER_COUNT = 10
_fader_page = 1
_fader_state = {i: {"name": "Sub {}".format(i), "level": 0.0} for i in range(1, FADER_COUNT + 1)}
_fader_listeners = []

def get_fader_state():
    return dict(_fader_state)

def on_fader_state(cb):
    _fader_listeners.append(cb)

def _notify_faders():
    for cb in _fader_listeners:
        try: cb(dict(_fader_state))
        except: pass

_state = {"active_cue": "", "pending_cue": "", "show_name": "", "cmd_line": "", "eos_ok": False}
_last_rx = 0.0
_listeners = []
_osc_log = []
_osc_log_listeners = []

_cue_list = {}
_cue_list_listeners = []

_active_cue_list_num = 1

def get_active_cue_list_num():
    return _active_cue_list_num

def get_cue_list():
    return sorted(_cue_list.values(), key=lambda c: float(c.get("num", 0)))

def on_cue_list(cb):
    _cue_list_listeners.append(cb)

def _notify_cues():
    for cb in _cue_list_listeners:
        try: cb(get_cue_list())
        except: pass

def _parse_cue_text(text):
    import re as _re
    m = _re.match(r"(?:\d+/)?([\d.]+)\s*(.*)", text.strip())
    if not m:
        return
    num = m.group(1)
    rest = m.group(2).strip()
    label = _re.sub(r"\s+[\d.]+%?\s*$", "", rest).strip()
    label = _re.sub(r"\s+[\d.]+\s*$", "", label).strip()
    if num and num not in _cue_list:
        _cue_list[num] = {"num": num, "label": label}
        _notify_cues()
    elif num and label and not _cue_list[num].get("label"):
        _cue_list[num]["label"] = label
        _notify_cues()

# ─── TCP OSC transport ────────────────────────────────────────────────────────

def _build_osc(address, args):
    """Build raw OSC message bytes (no length prefix)."""
    addr_b = address.encode() + b'\x00'
    while len(addr_b) % 4:
        addr_b += b'\x00'

    tags = ','
    arg_data = b''
    for a in args:
        if isinstance(a, bool):
            tags += 'T' if a else 'F'
        elif isinstance(a, int):
            tags += 'i'
            arg_data += _struct.pack('>i', a)
        elif isinstance(a, float):
            tags += 'f'
            arg_data += _struct.pack('>f', a)
        elif isinstance(a, str):
            tags += 's'
            sb = a.encode() + b'\x00'
            while len(sb) % 4:
                sb += b'\x00'
            arg_data += sb

    tag_b = tags.encode() + b'\x00'
    while len(tag_b) % 4:
        tag_b += b'\x00'

    return addr_b + tag_b + arg_data

def _send(address, args=None):
    """Send OSC message over TCP (4-byte length prefix framing)."""
    if args is None:
        args = []
    if not isinstance(args, list):
        args = [args]
    global _tcp_sock
    with _tcp_lock:
        sock = _tcp_sock
        if sock is None:
            return False
        try:
            msg = _build_osc(address, args)
            packet = _struct.pack('>I', len(msg)) + msg
            sock.sendall(packet)
            return True
        except Exception as e:
            print(f"[OSC->] send error: {e}")
            _tcp_sock = None
            _state["eos_ok"] = False
            _notify()
            return False

# ─── EOS commands ─────────────────────────────────────────────────────────────

def _key(name):
    _send(_KEY_PATH + name, [1]); time.sleep(0.05)
    _send(_KEY_PATH + name, [0]); time.sleep(0.1)

def _cli(cmd):
    _send(_CMD_PATH, [cmd + "#"])

def _clear_cmd():
    # Shift+Clear — полная очистка буфера и ошибок пользователя
    _send(_KEY_PATH + "shift", [1]); time.sleep(0.05)
    _send(_KEY_PATH + "clr",   [1]); time.sleep(0.05)
    _send(_KEY_PATH + "clr",   [0]); time.sleep(0.05)
    _send(_KEY_PATH + "shift", [0]); time.sleep(0.3)

def go():
    _push_cmd_history("GO")
    _key("go_0")
    return True

def stop():
    _push_cmd_history("STOP")
    _key("stop")
    return True

def go_to_cue(num, cue_time=None):
    if cue_time is not None and cue_time != "":
        _push_cmd_history("GO TO CUE {} TIME {}".format(num, cue_time))
        with _cmd_lock:
            _clear_cmd()
            _cli("Go_To_Cue {} Time {}".format(num, cue_time))
    elif cue_time == "":
        _push_cmd_history("GO TO CUE {} TIME".format(num))
        with _cmd_lock:
            _clear_cmd()
            _cli("Go_To_Cue {} Time".format(num))
    else:
        _push_cmd_history("GO TO CUE {}".format(num))
        with _cmd_lock:
            _clear_cmd()
            _cli("Go_To_Cue {}".format(num))
    return True

def go_to_cue_out():
    _push_cmd_history("GO TO CUE OUT")
    with _cmd_lock:
        _clear_cmd()
        _cli("Go_To_Cue Out Time 0")
    return True

def move_cue(src, dst):
    _push_cmd_history("CUE {} MOVE TO CUE {}".format(src, dst))
    with _cmd_lock:
        _clear_cmd()
        _send(_CMD_PATH, ["Cue {}".format(src)])
        time.sleep(0.3)
        _key("move_to")
        time.sleep(0.2)
        _cli("Cue {}".format(dst))
    return True

def copy_cue(src, dst):
    _push_cmd_history("CUE {} COPY TO CUE {}".format(src, dst))
    with _cmd_lock:
        _clear_cmd()
        _send(_CMD_PATH, ["Cue {}".format(src)])
        time.sleep(0.3)
        _key("copy_to")
        time.sleep(0.2)
        _cli("Cue {}".format(dst))
    return True

def label_cue(num, text):
    _push_cmd_history("CUE {} LABEL {}".format(num, text))
    with _cmd_lock:
        _clear_cmd()
        _cli("Cue {} Label {}".format(num, text))
    return True

def record_cue(num):
    _push_cmd_history("RECORD CUE {}".format(num))
    with _cmd_lock:
        _clear_cmd()
        _cli("Record Cue {}".format(num))
    return True

def update_cue(num=None):
    _push_cmd_history("UPDATE{}".format(" CUE " + str(num) if num else ""))
    with _cmd_lock:
        _clear_cmd()
        if num:
            _cli("Update Cue {}".format(num))
        else:
            _key("update")
    return True

def delete_cue(num):
    _push_cmd_history("DELETE CUE {}".format(num))
    with _cmd_lock:
        _clear_cmd()
        _cli("Delete Cue {}".format(num))
    return True

def fire_macro(num):
    _push_cmd_history("MACRO {}".format(num))
    with _cmd_lock:
        _clear_cmd()
        _cli("Macro {}".format(num))
    return True

def set_chan(chan, level=None):
    if level is not None:
        return send_cmd("Chan {} At {}".format(chan, level))
    return send_cmd("Chan {}".format(chan))

def set_group(num, level=None):
    if level is not None:
        return send_cmd("Group {} At {}".format(num, level))
    return send_cmd("Group {}".format(num))

def set_sub(num, level=None):
    if level is not None:
        return send_cmd("Sub {} At {}".format(num, level))
    return send_cmd("Sub {}".format(num))

def fader_set(fader_num, level_0_1):
    _send("/eos/fader/{}/{}".format(FADER_BANK, fader_num), [float(level_0_1)])
    return True

def fader_bump(fader_num, on):
    _send("/eos/fader/{}/{}/fire".format(FADER_BANK, fader_num), [1.0 if on else 0.0])
    return True

def fader_stop(fader_num):
    _send("/eos/fader/{}/{}/stop".format(FADER_BANK, fader_num), [1.0])
    return True

def fader_page(delta):
    global _fader_page
    _fader_page = max(1, _fader_page + delta)
    _send("/eos/fader/{}/config/{}/{}".format(FADER_BANK, _fader_page, FADER_COUNT), [])
    return _fader_page

def get_fader_page():
    return _fader_page

def blind():
    _push_cmd_history("BLIND")
    with _cmd_lock:
        _clear_cmd()
        _send(_CMD_PATH, ["Blind#"])
    return True

def live():
    _push_cmd_history("LIVE")
    with _cmd_lock:
        _clear_cmd()
        _send(_CMD_PATH, ["Live#"])
    return True

def send_cmd(cmd):
    _push_cmd_history(cmd)
    with _cmd_lock:
        _clear_cmd()
        _send(_CMD_PATH, [cmd + "#"])
    return True

def run_eos_cmd(cmd):
    import re
    c = cmd.strip()

    if c == "GO":            return go()
    if c == "STOP":          return stop()
    if c == "GO TO CUE OUT": return go_to_cue_out()
    if c == "BLIND":         return blind()
    if c == "LIVE":          return live()
    if c == "UPDATE":        return update_cue()
    if c == "UNDO":
        _push_cmd_history("UNDO")
        _key("undo"); return True

    m = re.match(r"GO TO CUE ([\d.]+)\s+TIME\s+([\d.]+)", c)
    if m: return go_to_cue(m.group(1), m.group(2))

    m = re.match(r"GO TO CUE ([\d.]+)\s+TIME$", c)
    if m: return go_to_cue(m.group(1), "")

    m = re.match(r"GO TO CUE ([\d.]+)", c)
    if m: return go_to_cue(m.group(1))

    m = re.match(r"CUE ([\d.]+)\s+TIME\s+([\d.]+)", c)
    if m:
        num, t = m.group(1), m.group(2)
        _push_cmd_history("CUE {} TIME {}".format(num, t))
        with _cmd_lock:
            _clear_cmd()
            _send(_CMD_PATH, ["Blind#"])
            time.sleep(0.5)
            _send(_CMD_PATH, ["Cue {} Time {}#".format(num, t)])
            time.sleep(0.5)
            _send(_CMD_PATH, ["Live#"])
        return True

    m = re.match(r"CUE ([\d.]+) MOVE TO CUE ([\d.]+)", c)
    if m: return move_cue(m.group(1), m.group(2))

    m = re.match(r"CUE ([\d.]+) COPY TO CUE ([\d.]+)", c)
    if m: return copy_cue(m.group(1), m.group(2))

    if c.startswith("LABEL CUE"):
        m2 = re.match(r"LABEL CUE ([\d.]+)\s+(.+)", c)
        if m2: return label_cue(m2.group(1), m2.group(2).strip())

    m = re.match(r"RECORD CUE ([\d.]+)", c)
    if m: return record_cue(m.group(1))

    m = re.match(r"UPDATE CUE ([\d.]+)", c)
    if m: return update_cue(m.group(1))

    m = re.match(r"DELETE CUE ([\d.]+)", c)
    if m: return delete_cue(m.group(1))

    m = re.match(r"MACRO ([\d]+)", c)
    if m: return fire_macro(m.group(1))

    m = re.match(r"CUE ([\d.]+)$", c)
    if m: return go_to_cue(m.group(1))

    m = re.match(r"CHAN ([\d]+)\s+@\s+(FULL|[\d]+)", c)
    if m:
        ch, lvl = m.group(1), m.group(2)
        return set_chan(ch, "Full" if lvl == "FULL" else lvl)

    m = re.match(r"CHAN ([\d]+)$", c)
    if m: return set_chan(m.group(1))

    m = re.match(r"GROUP ([\d]+)\s+@\s+(FULL|[\d]+)", c)
    if m:
        g, lvl = m.group(1), m.group(2)
        return set_group(g, "Full" if lvl == "FULL" else lvl)

    m = re.match(r"SUB ([\d]+)\s+@\s+(FULL|[\d]+)", c)
    if m:
        s, lvl = m.group(1), m.group(2)
        return set_sub(s, "Full" if lvl == "FULL" else lvl)

    return send_cmd(c)

# ─── Command history ──────────────────────────────────────────────────────────

_cmd_history = []
_cmd_history_listeners = []

def get_cmd_history(): return list(_cmd_history)
def on_cmd_history(cb): _cmd_history_listeners.append(cb)

def _push_cmd_history(cmd):
    entry = {"ts": time.strftime("%H:%M:%S"), "cmd": cmd}
    _cmd_history.append(entry)
    if len(_cmd_history) > 50: _cmd_history.pop(0)
    for cb in _cmd_history_listeners:
        try: cb(entry)
        except: pass

# ─── State / SSE ──────────────────────────────────────────────────────────────

def get_state():    return dict(_state)
def on_event(cb):   _listeners.append(cb)
def on_osc_log(cb): _osc_log_listeners.append(cb)
def get_osc_log():  return list(_osc_log)

def _notify():
    for cb in _listeners:
        try: cb(dict(_state))
        except: pass

def _push_log(addr, args):
    global _last_rx
    _last_rx = time.time()
    _state["eos_ok"] = True
    entry = {"addr": addr, "args": [str(a) for a in args]}
    print("[OSC<-]", addr, args)
    _osc_log.append(entry)
    if len(_osc_log) > 200:
        _osc_log.pop(0)
    for cb in list(_osc_log_listeners):
        try: cb(entry)
        except: pass

# ─── OSC parser ───────────────────────────────────────────────────────────────

def _parse_osc_msg(data, offset=0):
    try:
        null = data.index(b'\x00', offset)
        addr = data[offset:null].decode('utf-8', errors='replace')
        pos = offset + (((null - offset) + 4) & ~3)
        if pos >= len(data):
            return addr, []
        null2 = data.index(b'\x00', pos)
        tags = data[pos:null2].decode('ascii', errors='replace')
        pos = offset + (((null2 - offset) + 4) & ~3)
        args = []
        for t in tags:
            if t in (',', ' '): continue
            elif t == 's':
                null3 = data.index(b'\x00', pos)
                args.append(data[pos:null3].decode('utf-8', errors='replace'))
                pos = (null3 + 4) & ~3
            elif t == 'f':
                args.append(_struct.unpack('>f', data[pos:pos+4])[0]); pos += 4
            elif t == 'i':
                args.append(_struct.unpack('>i', data[pos:pos+4])[0]); pos += 4
            elif t in ('T', 'F', 'N', 'I'):
                pass
        return addr, args
    except Exception:
        return None, []

def _unpack_bundle(data):
    messages = []
    if not data.startswith(b'#bundle\x00'):
        addr, args = _parse_osc_msg(data, 0)
        if addr:
            messages.append((addr, args))
        return messages
    pos = 16
    while pos < len(data):
        if pos + 4 > len(data): break
        size = _struct.unpack('>I', data[pos:pos+4])[0]
        pos += 4
        if size <= 0 or pos + size > len(data): break
        chunk = data[pos:pos+size]
        pos += size
        if chunk.startswith(b'#bundle\x00'):
            messages.extend(_unpack_bundle(chunk))
        else:
            addr, args = _parse_osc_msg(chunk, 0)
            if addr:
                messages.append((addr, args))
    return messages

_STATE_MAP = {
    "/eos/out/active/cue/text":  "active_cue",
    "/eos/out/pending/cue/text": "pending_cue",
    "/eos/out/show/name":        "show_name",
}

def _dispatch(addr, args):
    key = _STATE_MAP.get(addr)
    if key:
        val = str(args[0]) if args else ""
        _state[key] = val
        if key in ("active_cue", "pending_cue") and val:
            _parse_cue_text(val)
        _notify()
    elif addr == "/eos/out/user/{}/cmd".format(EOS_USER_ID):
        _state["cmd_line"] = str(args[0]) if args else ""
        _notify()
    else:
        import re as _re
        ln = str(_active_cue_list_num)

        m = _re.match(r"^/eos/out/get/cue/" + ln + r"/([\d.]+)/\d+/list/\d+/\d+$", addr)
        if m and len(args) > 2:
            num = m.group(1)
            label = str(args[2]) if args[2] not in ('', None) else ""
            notes = str(args[24]) if len(args) > 24 and args[24] not in ('', None) else ""
            if not _re.match(r"^\d+(\.\d+)?$", label) and (label or notes):
                changed = False
                if num not in _cue_list:
                    _cue_list[num] = {"num": num, "label": label, "notes": notes}
                    changed = True
                else:
                    entry = _cue_list[num]
                    if entry.get("label") != label:
                        entry["label"] = label; changed = True
                    if entry.get("notes") != notes:
                        entry["notes"] = notes; changed = True
                if changed:
                    _notify_cues()

        m = _re.match(r"^/eos/out/cue/" + ln + r"/([\d.]+)/label$", addr)
        if m and args:
            num = m.group(1)
            label = str(args[0])
            if num not in _cue_list:
                _cue_list[num] = {"num": num, "label": label, "notes": ""}
            else:
                _cue_list[num]["label"] = label
            _notify_cues()

        m = _re.match(r"^/eos/out/cue/" + ln + r"/([\d.]+)/notes$", addr)
        if m and args:
            num = m.group(1)
            if num in _cue_list:
                _cue_list[num]["notes"] = str(args[0])
                _notify_cues()

        m = _re.match(r"^/eos/out/event/cue/(\d+)/([\d.]+)/fire$", addr)
        if m:
            lst, num = m.group(1), m.group(2)
            if lst == str(_active_cue_list_num):
                if num not in _cue_list:
                    _cue_list[num] = {"num": num, "label": ""}
                    _notify_cues()
                label = _cue_list.get(num, {}).get("label", "")
                _state["active_cue"] = f"{lst}/{num} {label}".strip()
                _notify()

        m = _re.match(r"^/eos/out/fader/{}/(\d+)/name$".format(FADER_BANK), addr)
        if m and args:
            n = int(m.group(1))
            if 1 <= n <= FADER_COUNT:
                _fader_state[n]["name"] = str(args[0])
                _notify_faders()

        m = _re.match(r"^/eos/fader/{}/(\d+)$".format(FADER_BANK), addr)
        if m and args:
            n = int(m.group(1))
            if 1 <= n <= FADER_COUNT:
                try:
                    _fader_state[n]["level"] = float(args[0])
                    _notify_faders()
                except (ValueError, TypeError):
                    pass

        m = _re.match(r"^/eos/out/fader/{}$".format(FADER_BANK), addr)
        if m and args:
            _state["fader_page"] = str(args[0])
            _notify()

    _push_log(addr, args)

# ─── TCP receiver / reconnect loop ───────────────────────────────────────────

def _tcp_recv_loop(sock):
    """Read OSC messages from a TCP socket (Packet Length v1.0 framing)."""
    buf = b''
    while True:
        try:
            chunk = sock.recv(4096)
            if not chunk:
                print("[OSC<-] TCP connection closed by EOS")
                break
            buf += chunk
            while len(buf) >= 4:
                length = _struct.unpack('>I', buf[:4])[0]
                if len(buf) < 4 + length:
                    break
                packet = buf[4:4 + length]
                buf = buf[4 + length:]
                messages = _unpack_bundle(packet)
                for addr, args in messages:
                    _dispatch(addr, args)
        except Exception as e:
            print(f"[OSC<-] recv error: {e}")
            break

def _connect_tcp():
    """Try to connect to EOS TCP OSC. Returns socket or None."""
    try:
        sock = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((config.EOS_IP, EOS_TCP_PORT))
        sock.settimeout(None)
        print(f"[OSC] TCP connected to {config.EOS_IP}:{EOS_TCP_PORT}")
        return sock
    except Exception as e:
        print(f"[OSC] TCP connect failed: {e}")
        return None

def _subscribe(sock):
    """Send subscribe and initial state requests over TCP."""
    def s(addr, args=None):
        if args is None: args = []
        msg = _build_osc(addr, args)
        sock.sendall(_struct.pack('>I', len(msg)) + msg)

    s("/eos/subscribe", [1])
    s("/eos/get/show/name")
    s("/eos/get/active/cue/text")
    s("/eos/get/pending/cue/text")
    s("/eos/fader/{}/config/{}/{}".format(FADER_BANK, _fader_page, FADER_COUNT))

def start_tcp_connection():
    """Background thread: connect to EOS, receive, reconnect on drop."""
    global _tcp_sock

    def _loop():
        global _tcp_sock
        while True:
            sock = _connect_tcp()
            if sock is None:
                time.sleep(3)
                continue
            with _tcp_lock:
                _tcp_sock = sock
            try:
                _subscribe(sock)
            except Exception as e:
                print(f"[OSC] subscribe error: {e}")

            # Start cue scan after connect
            threading.Thread(target=request_cue_list, daemon=True).start()

            _tcp_recv_loop(sock)

            # Connection dropped
            with _tcp_lock:
                if _tcp_sock is sock:
                    _tcp_sock = None
            _state["eos_ok"] = False
            _notify()
            print("[OSC] reconnecting in 3s...")
            time.sleep(3)

    threading.Thread(target=_loop, daemon=True, name="osc-tcp").start()
    print("[OSC] TCP connection thread started")

# ─── Cue list scan ───────────────────────────────────────────────────────────

def request_cue_list(list_num=None):
    global _active_cue_list_num, _cue_list
    if list_num is not None:
        _active_cue_list_num = list_num
        _cue_list = {}
    ln = _active_cue_list_num

    def _do():
        candidates = []
        for n in range(1, 21):
            candidates.append(str(n))
        for n in range(1, 16):
            for m in range(1, 10):
                candidates.append(f"{n}.{m}")
        for n in range(1, 11):
            for m in range(11, 100, 10):
                candidates.append(f"{n}.{m}")
            for m in range(1, 10):
                for mm in range(1, 10):
                    candidates.append(f"{n}.{m}{mm}")
        for num in candidates:
            _send("/eos/get/cue/{}/{}/label".format(ln, num), [])
            time.sleep(0.01)
        _notify_cues()

    threading.Thread(target=_do, daemon=True, name="cue-scan").start()

def refresh_cue_labels():
    ln = _active_cue_list_num
    def _do():
        for num in list(_cue_list.keys()):
            _send("/eos/get/cue/{}/{}/label".format(ln, num), [])
            time.sleep(0.01)
    threading.Thread(target=_do, daemon=True, name="cue-refresh").start()

# ─── Compatibility stubs ──────────────────────────────────────────────────────

def restart_receiver(new_port):
    """No-op for TCP mode — RX port is not used."""
    pass

_rx_sock = None  # kept for compatibility with app.py imports

def reconnect():
    """Force reconnect by closing current TCP socket."""
    global _tcp_sock
    with _tcp_lock:
        if _tcp_sock:
            try: _tcp_sock.close()
            except: pass
            _tcp_sock = None

# ─── Init ─────────────────────────────────────────────────────────────────────

start_tcp_connection()
