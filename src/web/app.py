import sys, os, json, queue, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from flask import Flask, Response, request, jsonify, render_template
from core.osc_bridge import go, stop, run_eos_cmd, get_state, on_event, on_osc_log, get_osc_log, get_cue_list, request_cue_list, on_cue_list, get_cmd_history, on_cmd_history, get_fader_state, on_fader_state, fader_set, fader_bump, fader_stop, fader_page, get_fader_page, get_active_cue_list_num, reconnect
from voice.parser import parse
from config import WEB_PORT, ANTHROPIC_API_KEY
from agent.agent import EOSAgent

app = Flask(__name__)
_sse_queues = []
_osc_monitor_queues = []
_history = []

_agent = EOSAgent(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

def claude_ask(text):
    if not _agent:
        return {"reply": "API ключ не задан в config.py", "cmds": []}
    result = _agent.chat(text, get_state(), _history)
    return {"reply": result["text"], "cmds": result["commands"]}

def _run_cmd(cmd):
    from agent import sandbox
    if sandbox.is_enabled():
        result = sandbox.execute(cmd)
        return True  # в песочнице всегда "успех"
    return run_eos_cmd(cmd)

def _push(data):
    for q in list(_sse_queues):
        try: q.put_nowait(data)
        except: pass

on_event(lambda s: _push({"type": "state", **s}))
on_cue_list(lambda cues: _push({"type": "cues", "cues": cues}))
on_cmd_history(lambda e: _push({"type": "cmd_history", "entry": e}))
on_fader_state(lambda f: _push({"type": "faders", "faders": f, "page": get_fader_page()}))

def _push_osc(entry):
    for q in list(_osc_monitor_queues):
        try: q.put_nowait(entry)
        except: pass

on_osc_log(_push_osc)

@app.route("/api/events")
def events():
    q = queue.Queue(maxsize=20)
    _sse_queues.append(q)
    def gen():
        pass  # TCP mode: state comes via persistent connection
        yield "data: " + json.dumps({"type": "state", **get_state()}) + "\n\n"
        yield "data: " + json.dumps({"type": "cues", "cues": get_cue_list()}) + "\n\n"
        yield "data: " + json.dumps({"type": "cmd_history_init", "entries": get_cmd_history()}) + "\n\n"
        yield "data: " + json.dumps({"type": "faders", "faders": get_fader_state(), "page": get_fader_page()}) + "\n\n"
        while True:
            try: yield "data: " + json.dumps(q.get(timeout=25)) + "\n\n"
            except: yield ": ping\n\n"
    return Response(gen(), mimetype="text/event-stream",
                    headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

@app.route("/api/chat", methods=["POST"])
def api_chat():
    body = request.json or {}
    text = body.get("text","").strip()
    dry_run = body.get("dry_run", False)  # разобрать но не выполнять
    if not text: return jsonify({"error":"empty"})
    quick = parse(text)
    if quick and len(text.split()) <= 5:
        if not dry_run:
            ok = _run_cmd(quick)
            reply = ("Выполнено: " if ok else "EOS недоступен, не отправлено: ") + quick
        else:
            reply = quick
        _history.extend([{"role":"user","content":text},{"role":"assistant","content":reply}])
        return jsonify({"reply":reply,"cmds":[quick]})
    result = claude_ask(text)
    reply = result.get("reply","")
    cmds  = result.get("cmds",[])
    if not dry_run:
        failed = [cmd for cmd in cmds if not _run_cmd(cmd)]
        if failed:
            reply += " (EOS недоступен: " + ", ".join(failed) + ")"
    _history.extend([{"role":"user","content":text},{"role":"assistant","content":reply}])
    return jsonify({"reply":reply,"cmds":cmds})

@app.route("/api/transcribe", methods=["POST"])
def api_transcribe():
    """Push-to-talk: принимает audio blob из браузера, транскрибирует, выполняет."""
    try:
        from voice.transcriber import transcribe_audio
        audio_bytes = request.data
        if not audio_bytes:
            return jsonify({"error": "Нет аудио"})
        text = transcribe_audio(audio_bytes)
        if not text:
            return jsonify({"error": "Не распознано", "transcribed": ""})
        quick = parse(text)
        if quick and len(text.split()) <= 7:
            ok = _run_cmd(quick)
            reply = ("Выполнено: " if ok else "EOS недоступен: ") + quick
            _history.extend([{"role":"user","content":text},{"role":"assistant","content":reply}])
            return jsonify({"transcribed": text, "reply": reply, "cmds": [quick]})
        result = claude_ask(text)
        reply = result.get("reply","")
        cmds  = result.get("cmds",[])
        for cmd in cmds: _run_cmd(cmd)
        _history.extend([{"role":"user","content":text},{"role":"assistant","content":reply}])
        return jsonify({"transcribed": text, "reply": reply, "cmds": cmds})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/voice", methods=["POST"])
def api_voice():
    try:
        from voice.transcriber import record_and_transcribe
        text = record_and_transcribe()
        if not text: return jsonify({"error":"Не распознано"})
        quick = parse(text)
        if quick and len(text.split()) <= 5:
            ok = _run_cmd(quick)
            reply = ("Выполнено: " if ok else "EOS недоступен, не отправлено: ") + quick
            _history.extend([{"role":"user","content":text},{"role":"assistant","content":reply}])
            d = {"reply": reply, "cmds": [quick]}
        else:
            result = claude_ask(text)
            reply = result.get("reply","")
            cmds  = result.get("cmds",[])
            failed = [cmd for cmd in cmds if not _run_cmd(cmd)]
            if failed:
                reply += " (EOS недоступен: " + ", ".join(failed) + ")"
            _history.extend([{"role":"user","content":text},{"role":"assistant","content":reply}])
            d = {"reply": reply, "cmds": cmds}
        d["transcribed"] = text
        return jsonify(d)
    except Exception as e: return jsonify({"error":str(e)})

@app.route("/api/get_ip")
def api_get_ip():
    import config
    return jsonify({"ip": config.EOS_IP, "port": config.EOS_OSC_PORT, "rx_port": config.EOS_RX_PORT})

@app.route("/api/set_ip", methods=["POST"])
def api_set_ip():
    import config
    import core.osc_bridge as bridge
    data = request.json or {}
    ip = data.get("ip","").strip()
    if not ip: return jsonify({"error":"empty"})
    config.EOS_IP = ip
    cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.py")
    lines = open(cfg_path).readlines()
    with open(cfg_path,"w") as f:
        for line in lines:
            if line.startswith("EOS_IP"):
                f.write('EOS_IP        = "' + ip + '"\n')
            else:
                f.write(line)
    bridge.reconnect()  # reconnect TCP to new IP
    return jsonify({"ok": True, "ip": ip})

@app.route("/api/set_port", methods=["POST"])
def api_set_port():
    import config
    import core.osc_bridge as bridge
    data = request.json or {}
    raw = str(data.get("port","")).strip()
    if not raw: return jsonify({"error":"empty"})
    try:
        port = int(raw)
    except ValueError:
        return jsonify({"error":"invalid"})
    if not (1 <= port <= 65535):
        return jsonify({"error":"out of range"})
    config.EOS_OSC_PORT = port
    cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.py")
    lines = open(cfg_path).readlines()
    with open(cfg_path,"w") as f:
        for line in lines:
            if line.startswith("EOS_OSC_PORT"):
                f.write("EOS_OSC_PORT  = " + str(port) + "\n")
            else:
                f.write(line)
    bridge.reconnect()
    return jsonify({"ok": True, "port": port})

@app.route("/api/cue_list_num")
def api_cue_list_num():
    return jsonify({"list_num": get_active_cue_list_num()})

@app.route("/api/set_cue_list", methods=["POST"])
def api_set_cue_list():
    data = request.json or {}
    try:
        ln = int(data.get("list_num", 1))
    except (ValueError, TypeError):
        return jsonify({"error": "invalid"})
    request_cue_list(ln)
    return jsonify({"ok": True, "list_num": ln})

@app.route("/api/set_rx_port", methods=["POST"])
def api_set_rx_port():
    import config
    import core.osc_bridge as bridge
    data = request.json or {}
    raw = str(data.get("port","")).strip()
    if not raw: return jsonify({"error":"empty"})
    try:
        port = int(raw)
    except ValueError:
        return jsonify({"error":"invalid"})
    if not (1 <= port <= 65535):
        return jsonify({"error":"out of range"})
    config.EOS_RX_PORT = port
    cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.py")
    lines = open(cfg_path).readlines()
    with open(cfg_path,"w") as f:
        for line in lines:
            if line.startswith("EOS_RX_PORT"):
                f.write("EOS_RX_PORT   = " + str(port) + "\n")
            else:
                f.write(line)
    # bridge.restart_receiver(port)  # no-op in TCP mode
    return jsonify({"ok": True, "rx_port": port})

@app.route("/api/fader/set", methods=["POST"])
def api_fader_set():
    d = request.json or {}
    fader_set(int(d["n"]), float(d["level"]))
    return jsonify({"ok": True})

@app.route("/api/fader/bump", methods=["POST"])
def api_fader_bump():
    d = request.json or {}
    fader_bump(int(d["n"]), bool(d.get("on", True)))
    return jsonify({"ok": True})

@app.route("/api/fader/stop", methods=["POST"])
def api_fader_stop():
    d = request.json or {}
    fader_stop(int(d["n"]))
    return jsonify({"ok": True})

@app.route("/api/fader/page", methods=["POST"])
def api_fader_page():
    d = request.json or {}
    page = fader_page(int(d.get("delta", 1)))
    return jsonify({"ok": True, "page": page})

@app.route("/api/analyze/usitt", methods=["POST"])
def api_analyze_usitt():
    """Принять USITT ASCII файл и вернуть анализ шоу."""
    from core.usitt_parser import parse as parse_usitt
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "Файл не получен"})
    try:
        text = f.read().decode("utf-8", errors="replace")
        result = parse_usitt(text)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/analyze/usitt_latest", methods=["GET"])
def api_analyze_usitt_latest():
    """Загрузить последний USITT файл из папки exports."""
    from core.usitt_parser import parse as parse_usitt
    export_dir = "/Users/ts/eos-assistant/exports"
    files = sorted(
        [f for f in os.listdir(export_dir) if f.endswith((".txt", ".asc", ".usitt"))],
        key=lambda f: os.path.getmtime(os.path.join(export_dir, f)),
        reverse=True
    ) if os.path.isdir(export_dir) else []
    if not files:
        return jsonify({"error": "Нет файлов в папке exports", "path": export_dir})
    path = os.path.join(export_dir, files[0])
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
        result = parse_usitt(text)
        result["filename"] = files[0]
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/analyze/probe", methods=["POST"])
def api_analyze_probe():
    """Отладка: смотрим что EOS шлёт в ответ на GET-запросы для кью."""
    from core.eos_analyzer import probe_osc_response
    cue_num = (request.json or {}).get("cue", "1")
    results = probe_osc_response(str(cue_num))
    return jsonify({"cue": cue_num, "packets": results, "count": len(results)})

@app.route("/api/analyze/cue_channels", methods=["POST"])
def api_analyze_cue_channels():
    """Запросить каналы в конкретном кью."""
    from core.eos_analyzer import get_cue_channel_data
    cue_num = (request.json or {}).get("cue", "1")
    chans = get_cue_channel_data(str(cue_num))
    return jsonify({"cue": cue_num, "channels": chans})

@app.route("/api/cues")
def api_cues():
    return jsonify(get_cue_list())

@app.route("/api/cues/refresh", methods=["POST"])
def api_cues_refresh():
    request_cue_list()
    return jsonify({"ok": True})

@app.route("/api/go",   methods=["POST"])
def api_go():   go();   return jsonify({"ok":True})
@app.route("/api/stop", methods=["POST"])
def api_stop(): stop(); return jsonify({"ok":True})
@app.route("/api/state")
def api_state(): return jsonify(get_state())

@app.route("/api/agent/sandbox", methods=["GET", "POST"])
def api_sandbox():
    """Включить/выключить режим песочницы."""
    from agent import sandbox
    if request.method == "POST":
        enabled = (request.json or {}).get("enabled", False)
        if _agent:
            _agent.set_sandbox(enabled)
        return jsonify({"ok": True, "sandbox": sandbox.is_enabled()})
    return jsonify({"sandbox": sandbox.is_enabled()})

@app.route("/api/agent/sandbox/log")
def api_sandbox_log():
    from agent import sandbox
    return jsonify({"log": sandbox.get_log(50)})

@app.route("/api/agent/save_solution", methods=["POST"])
def api_save_solution():
    """Сохранить решение в базу знаний агента."""
    if not _agent:
        return jsonify({"error": "agent not initialized"})
    d = request.json or {}
    title    = d.get("title", "").strip()
    problem  = d.get("problem", "").strip()
    solution = d.get("solution", "").strip()
    if not title or not solution:
        return jsonify({"error": "title and solution required"})
    _agent.save_solution(title, problem, solution)
    return jsonify({"ok": True})

@app.route("/api/agent/reload", methods=["POST"])
def api_agent_reload():
    """Перечитать мануал и записанные решения."""
    if _agent:
        _agent.reload_knowledge()
    return jsonify({"ok": True})

@app.route("/api/cmd", methods=["POST"])
def api_cmd():
    cmd = (request.json or {}).get("cmd", "").strip()
    if not cmd: return jsonify({"error": "empty"})
    ok = run_eos_cmd(cmd)
    return jsonify({"ok": ok, "cmd": cmd})
@app.route("/monitor/events")
def monitor_events():
    q = queue.Queue(maxsize=200)
    _osc_monitor_queues.append(q)
    def gen():
        for entry in get_osc_log():
            yield "data: " + json.dumps(entry) + "\n\n"
        while True:
            try: yield "data: " + json.dumps(q.get(timeout=25)) + "\n\n"
            except: yield ": ping\n\n"
    return Response(gen(), mimetype="text/event-stream",
                    headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

@app.route("/monitor")
def monitor():
    return """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>OSC Monitor</title>
<style>
  body{background:#0d0d0f;color:#d8dce8;font-family:'SF Mono',monospace;font-size:13px;margin:0;padding:12px;}
  h2{color:#4f8ef7;margin:0 0 10px;}
  #log{max-height:calc(100vh - 80px);overflow-y:auto;}
  .row{padding:3px 0;border-bottom:1px solid #1e2128;display:flex;gap:12px;}
  .time{color:#7a7f8e;flex-shrink:0;}
  .addr{color:#4f8ef7;flex-shrink:0;min-width:320px;}
  .args{color:#3dba6e;}
  #count{color:#7a7f8e;font-size:11px;}
  label{color:#7a7f8e;font-size:12px;margin-left:16px;}
</style></head>
<body>
<h2>OSC Monitor — порт 9000 <span id="count"></span>
  <label><input type="checkbox" id="pause"> Пауза</label>
  <button onclick="document.getElementById('log').innerHTML='';n=0;" style="margin-left:12px;background:#1e2128;color:#d8dce8;border:1px solid #2a2d35;border-radius:5px;padding:3px 10px;cursor:pointer;">Очистить</button>
</h2>
<div id="log"></div>
<script>
  let n = 0;
  const log = document.getElementById('log');
  const es = new EventSource('/monitor/events');
  es.onmessage = e => {
    if (document.getElementById('pause').checked) return;
    const d = JSON.parse(e.data);
    n++;
    document.getElementById('count').textContent = '(' + n + ' пакетов)';
    const row = document.createElement('div');
    row.className = 'row';
    const now = new Date().toTimeString().slice(0,8);
    row.innerHTML = '<span class="time">'+now+'</span><span class="addr">'+d.addr+'</span><span class="args">'+JSON.stringify(d.args)+'</span>';
    log.appendChild(row);
    log.scrollTop = log.scrollHeight;
  };
</script></body></html>"""

@app.route("/")
def index(): return render_template("index.html")

if __name__ == "__main__":
    print("\nEOS Assistant — http://localhost:" + str(WEB_PORT) + "\n")
    app.run(host="0.0.0.0", port=WEB_PORT, debug=False)
