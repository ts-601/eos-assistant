import os, tempfile, struct, wave
from faster_whisper import WhisperModel
from config import WHISPER_MODEL

_model = None

def _get_model():
    global _model
    if _model is None:
        _model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    return _model

def _webm_to_wav(src_path: str, dst_path: str):
    """Convert any browser audio (webm/ogg/mp4) to 16kHz mono wav using PyAV."""
    import av
    with av.open(src_path) as inp:
        audio = inp.streams.audio[0]
        with wave.open(dst_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # int16
            wf.setframerate(16000)
            resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
            for frame in inp.decode(audio):
                for rf in resampler.resample(frame):
                    wf.writeframes(rf.to_ndarray().tobytes())
            # flush resampler
            for rf in resampler.resample(None):
                wf.writeframes(rf.to_ndarray().tobytes())

def transcribe_audio(audio_bytes, lang="ru"):
    """Transcribe raw audio bytes (webm/wav/ogg from browser MediaRecorder)."""
    wav_path = None
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
        f.write(audio_bytes)
        src_path = f.name
    try:
        wav_fd, wav_path = tempfile.mkstemp(suffix=".wav")
        os.close(wav_fd)
        _webm_to_wav(src_path, wav_path)
        segs, _ = _get_model().transcribe(wav_path, language=lang)
        return " ".join(s.text for s in segs).strip()
    finally:
        try: os.unlink(src_path)
        except: pass
        if wav_path:
            try: os.unlink(wav_path)
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
