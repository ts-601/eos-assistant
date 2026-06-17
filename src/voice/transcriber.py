import os, tempfile
from faster_whisper import WhisperModel
from config import WHISPER_MODEL

_model = None

def _get_model():
    global _model
    if _model is None:
        _model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    return _model

def transcribe_audio(audio_bytes, lang="ru"):
    """Transcribe raw audio bytes (webm/wav/ogg from browser MediaRecorder)."""
    suffix = ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(audio_bytes)
        fname = f.name
    try:
        segs, _ = _get_model().transcribe(fname, language=lang)
        return " ".join(s.text for s in segs).strip()
    finally:
        try: os.unlink(fname)
        except: pass

def record_and_transcribe(seconds=5, lang="ru"):
    import wave, pyaudio
    RATE, CHUNK = 16000, 1024
    p = pyaudio.PyAudio()
    s = p.open(format=pyaudio.paInt16, channels=1, rate=RATE, input=True, frames_per_buffer=CHUNK)
    frames = [s.read(CHUNK) for _ in range(int(RATE/CHUNK*seconds))]
    s.stop_stream(); s.close(); p.terminate()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wf = wave.open(f,"wb"); wf.setnchannels(1); wf.setsampwidth(2)
        wf.setframerate(RATE); wf.writeframes(b"".join(frames)); wf.close()
        fname = f.name
    try:
        segs, _ = _get_model().transcribe(fname, language=lang)
        return " ".join(s.text for s in segs).strip()
    finally:
        try: os.unlink(fname)
        except: pass
