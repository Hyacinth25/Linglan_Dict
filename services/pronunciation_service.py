import ctypes
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import urllib.parse
import urllib.request
import uuid


class PronunciationService:
    def __init__(self, cache_dir, timeout=6):
        self.cache_dir = cache_dir
        self.data_dir = os.path.dirname(os.path.abspath(cache_dir))
        self.timeout = timeout
        self._lock = threading.Lock()
        self._thread = None

    def play_word(self, word, record=None, on_done=None):
        keyword = self._clean_word(word)
        if not keyword:
            self._notify(on_done, False, "no_word")
            return False
        thread = threading.Thread(
            target=self._play_worker,
            args=(keyword, record or {}, on_done),
            daemon=True,
        )
        with self._lock:
            self._thread = thread
        thread.start()
        return True

    def _play_worker(self, word, record, on_done):
        try:
            audio_path = self._resolve_audio_path(word, record)
            if audio_path and self._play_audio_file(audio_path):
                self._notify(on_done, True, "audio")
                return
            if self._speak_with_system_tts(word):
                self._notify(on_done, True, "tts")
                return
            self._notify(on_done, False, "play_failed")
        except Exception as exc:
            self._notify(on_done, False, str(exc) or "play_failed")

    def _resolve_audio_path(self, word, record):
        audio_value = (record or {}).get("audio")
        for candidate in self._iter_audio_candidates(audio_value):
            local_path = self._candidate_to_local_path(candidate, word)
            if local_path:
                return local_path
        for url in self._online_audio_urls(word):
            cached = self._download_to_cache(url, f"online_{word.lower()}.mp3")
            if cached:
                return cached
        return None

    def _iter_audio_candidates(self, audio_value):
        if not audio_value:
            return
        if isinstance(audio_value, (list, tuple)):
            for item in audio_value:
                yield from self._iter_audio_candidates(item)
            return
        if isinstance(audio_value, dict):
            for key in ("us", "uk", "url", "audio", "mp3", "wav"):
                if key in audio_value:
                    yield from self._iter_audio_candidates(audio_value.get(key))
            return

        text = str(audio_value).strip()
        if not text:
            return
        if text[:1] in ("[", "{"):
            try:
                parsed = json.loads(text)
            except Exception:
                parsed = None
            if parsed is not None:
                yield from self._iter_audio_candidates(parsed)
                return
        for part in re.split(r"[\s,;|]+", text):
            candidate = part.strip().strip("\"'")
            if candidate:
                yield candidate

    def _candidate_to_local_path(self, candidate, word):
        if candidate.startswith("//"):
            candidate = "https:" + candidate
        if candidate.startswith(("http://", "https://")):
            suffix = os.path.splitext(urllib.parse.urlparse(candidate).path)[1] or ".mp3"
            if len(suffix) > 8 or not re.match(r"^\.[A-Za-z0-9]+$", suffix):
                suffix = ".mp3"
            filename = "dict_%s%s" % (hashlib.sha1(candidate.encode("utf-8")).hexdigest(), suffix)
            return self._download_to_cache(candidate, filename)

        expanded = os.path.expandvars(os.path.expanduser(candidate))
        paths = [expanded]
        if not os.path.isabs(expanded):
            paths.append(os.path.join(self.data_dir, expanded))
            paths.append(os.path.abspath(expanded))
        for path in paths:
            if os.path.isfile(path):
                return path
        return None

    def _online_audio_urls(self, word):
        encoded = urllib.parse.quote(word)
        return (
            f"https://dict.youdao.com/dictvoice?audio={encoded}&type=2",
            f"https://dict.youdao.com/dictvoice?audio={encoded}&type=1",
        )

    def _download_to_cache(self, url, filename):
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            filename = self._safe_filename(filename)
            path = os.path.join(self.cache_dir, filename)
            if os.path.isfile(path) and os.path.getsize(path) > 0:
                return path
            request = urllib.request.Request(url, headers={"User-Agent": "LinglanDict/1.0"})
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = response.read()
            if not data:
                return None
            temp_path = path + ".tmp"
            with open(temp_path, "wb") as f:
                f.write(data)
            os.replace(temp_path, path)
            return path
        except Exception:
            return None

    def _play_audio_file(self, path):
        if not path or not os.path.isfile(path):
            return False
        if sys.platform.startswith("win"):
            return self._play_with_mci(path)
        return False

    def _play_with_mci(self, path):
        alias = "linglan_%s" % uuid.uuid4().hex
        winmm = ctypes.windll.winmm

        def send(command):
            buffer = ctypes.create_unicode_buffer(256)
            code = winmm.mciSendStringW(command, buffer, len(buffer), None)
            return code == 0

        ext = os.path.splitext(path)[1].lower()
        if ext == ".mp3":
            open_command = f'open "{path}" type mpegvideo alias {alias}'
        elif ext == ".wav":
            open_command = f'open "{path}" type waveaudio alias {alias}'
        else:
            open_command = f'open "{path}" alias {alias}'
        if not send(open_command) and not send(f'open "{path}" alias {alias}'):
            return False
        try:
            return send(f"play {alias} wait")
        finally:
            send(f"close {alias}")

    def _speak_with_system_tts(self, word):
        if not sys.platform.startswith("win"):
            return False
        script = (
            "Add-Type -AssemblyName System.Speech;"
            "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            "$speaker.Rate = -1;"
            "$speaker.Speak($env:LINGLAN_TTS_TEXT);"
            "$speaker.Dispose();"
        )
        env = os.environ.copy()
        env["LINGLAN_TTS_TEXT"] = word
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
                timeout=max(8, self.timeout + 4),
            )
            return result.returncode == 0
        except Exception:
            return False

    def _clean_word(self, word):
        text = (word or "").strip()
        text = re.sub(r"^[^A-Za-z]+|[^A-Za-z]+$", "", text)
        if not re.match(r"^[A-Za-z][A-Za-z'-]*$", text):
            return ""
        return text

    def _safe_filename(self, filename):
        name = re.sub(r"[^A-Za-z0-9_.-]+", "_", filename or "audio.mp3").strip("._")
        return name or "audio.mp3"

    def _notify(self, callback, ok, status):
        if callback:
            callback(ok, status)
