"""音效與背景音樂：全部用程式合成，不需要音檔。沒有音效裝置時自動靜音。"""
from __future__ import annotations

import array
import math
import random
import threading

RATE = 22050

NOTE_BASE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def freq(name: str) -> float:
    """'A4' -> 440.0；'R' 代表休止。"""
    if name == "R":
        return 0.0
    n = NOTE_BASE[name[0]]
    octave = int(name[1])
    return 440.0 * 2 ** ((n - 9 + 12 * (octave - 4)) / 12)


def _wave(kind: str, phase: float) -> float:
    if kind == "square":
        return 1.0 if phase % 1 < 0.5 else -1.0
    if kind == "triangle":
        return 4 * abs(phase % 1 - 0.5) - 1
    if kind == "noise":
        return random.uniform(-1, 1)
    return math.sin(2 * math.pi * phase)


def tone(f0: float, dur: float, vol: float = 0.4, kind: str = "square", f1: float | None = None,
         attack: float = 0.004) -> list[float]:
    """一個音：f0 到 f1 的滑音（f1 省略就是定音），尾端線性淡出。"""
    n = int(RATE * dur)
    out, phase = [], 0.0
    for i in range(n):
        t = i / n
        f = f0 + ((f1 if f1 is not None else f0) - f0) * t
        phase += f / RATE
        env = min(1.0, i / (attack * RATE + 1)) * (1 - t)
        out.append(_wave(kind, phase) * vol * env if f else 0.0)
    return out


def concat(parts: list[list[float]]) -> list[float]:
    return [s for part in parts for s in part]


def mix(*tracks: list[float]) -> list[float]:
    n = max(len(t) for t in tracks)
    return [sum(t[i] for t in tracks if i < len(t)) for i in range(n)]


def to_bytes(samples: list[float]) -> bytes:
    return array.array("h", [int(max(-1.0, min(1.0, s)) * 32000) for s in samples]).tobytes()


def arpeggio(names: list[str], step: float = 0.05, last: float = 0.12, vol: float = 0.35,
             kind: str = "square") -> list[float]:
    parts = [tone(freq(n), step, vol, kind) for n in names[:-1]]
    parts.append(tone(freq(names[-1]), last, vol, kind))
    return concat(parts)


def build_sfx() -> dict[str, list[float]]:
    return {
        "move": tone(260, 0.018, 0.18),
        "rotate": tone(520, 0.035, 0.22, f1=620),
        "hold": concat([tone(freq("E5"), 0.04, 0.25), tone(freq("A5"), 0.05, 0.25)]),
        "drop": mix(tone(140, 0.12, 0.7, "sine", f1=50), tone(300, 0.03, 0.2, "noise")),
        "lock": tone(180, 0.05, 0.3, "triangle"),
        "clear1": arpeggio(["C5", "E5"], 0.06, 0.12),
        "clear2": arpeggio(["C5", "E5", "G5"], 0.06, 0.14),
        "clear3": arpeggio(["C5", "E5", "G5", "C6"], 0.06, 0.16),
        "clear4": arpeggio(["C5", "E5", "G5", "C6", "E6", "G6"], 0.055, 0.35, 0.38),
        "tspin": mix(arpeggio(["A4", "C5", "E5", "A5", "C6"], 0.06, 0.25, 0.3, "triangle"),
                     tone(220, 0.5, 0.2, "square", f1=880)),
        "perfect": arpeggio(["C5", "E5", "G5", "C6", "E6", "G6", "C7", "E7"], 0.07, 0.6, 0.35, "triangle"),
        "warn": concat([tone(110, 0.09, 0.35), tone(0, 0.05, 0), tone(110, 0.09, 0.35)]),
        "dead": tone(440, 0.8, 0.4, "square", f1=70),
        "win": arpeggio(["C5", "E5", "G5", "C6", "G5", "C6", "E6"], 0.1, 0.5, 0.35),
        "countdown": tone(660, 0.1, 0.3, "triangle"),
        "go": tone(990, 0.25, 0.3, "triangle"),
    }


# 俄羅斯民謠 Korobeiniki（Tetris A 主題）：(音名, 拍數)
MELODY = [
    ("E5", 2), ("B4", 1), ("C5", 1), ("D5", 2), ("C5", 1), ("B4", 1),
    ("A4", 2), ("A4", 1), ("C5", 1), ("E5", 2), ("D5", 1), ("C5", 1),
    ("B4", 3), ("C5", 1), ("D5", 2), ("E5", 2),
    ("C5", 2), ("A4", 2), ("A4", 2), ("R", 2),
    ("R", 1), ("D5", 2), ("F5", 1), ("A5", 2), ("G5", 1), ("F5", 1),
    ("E5", 3), ("C5", 1), ("E5", 2), ("D5", 1), ("C5", 1),
    ("B4", 2), ("B4", 1), ("C5", 1), ("D5", 2), ("E5", 2),
    ("C5", 2), ("A4", 2), ("A4", 2), ("R", 2),
]
# 每 4 拍一個低音根音：A 小調的 Am / E / Am / Dm ... 簡單伴奏
BASS_ROOTS = ["A2", "E2", "A2", "A2", "D2", "C2", "E2", "A2", "A2", "A2"]


def build_music(beat: float = 0.2) -> list[float]:
    lead = concat([tone(freq(n), beat * d, 0.2, "square", attack=0.006) if n != "R"
                   else [0.0] * int(RATE * beat * d) for n, d in MELODY])
    total = sum(d for _, d in MELODY)
    bass_parts = []
    for b in range(0, total, 2):  # 每兩拍一個低音：根音、五度交替
        root = BASS_ROOTS[(b // 4) % len(BASS_ROOTS)]
        f = freq(root) * (1.5 if (b // 2) % 2 else 1.0)
        bass_parts.append(tone(f, beat * 2, 0.22, "triangle", attack=0.01))
    return mix(lead, concat(bass_parts))


class Audio:
    def __init__(self, enabled: bool = True):
        self.mixer = None
        self.muted = False
        self.sfx: dict = {}
        self.music = None
        self.music_channel = None
        self.want_music = False
        if enabled:  # 合成要一兩秒，放背景執行，不卡住選單
            threading.Thread(target=self._load, daemon=True).start()

    def _load(self):
        try:
            import pygame
            pygame.mixer.init(frequency=RATE, size=-16, channels=1, buffer=512)
            sfx = {k: pygame.mixer.Sound(buffer=to_bytes(v)) for k, v in build_sfx().items()}
            music = pygame.mixer.Sound(buffer=to_bytes(build_music()))
            music.set_volume(0.22)
            self.sfx, self.music, self.mixer = sfx, music, pygame.mixer
            if self.want_music:
                self.start_music()
        except Exception:  # 沒有音效裝置、或系統不支援：靜音繼續玩
            self.mixer = None

    @property
    def ok(self) -> bool:
        return self.mixer is not None

    def play(self, name: str, volume: float = 1.0):
        if self.ok and not self.muted and name in self.sfx:
            sound = self.sfx[name]
            sound.set_volume(volume)
            sound.play()

    def start_music(self):
        self.want_music = True
        if self.ok and self.music_channel is None:
            self.music_channel = self.music.play(loops=-1)
            if self.muted and self.music_channel:
                self.music_channel.pause()

    def stop_music(self, fade_ms: int = 600):
        self.want_music = False
        if self.ok:
            self.music.fadeout(fade_ms)
            self.music_channel = None

    def pause_music(self, paused: bool):
        """暫停遊戲或靜音時，音樂停住；恢復時從原處繼續。"""
        ch = self.music_channel
        if not (self.ok and ch):
            return
        if paused or self.muted:
            ch.pause()
        else:
            ch.unpause()

    def toggle_mute(self, game_paused: bool = False) -> bool:
        self.muted = not self.muted
        self.pause_music(game_paused)
        return self.muted
