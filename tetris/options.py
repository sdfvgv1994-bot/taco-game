"""俄羅斯方塊：模式清單、設定檔、最佳成績（tetris.py 拆出來的積木）。

- MODE_LIST：選單上的 6 種模式
- Settings：遊戲設定，存在 tetris/settings.json
- Records：Sprint 最快時間、Marathon 最多行數，存在 tetris/records.json
"""
from __future__ import annotations

import json
from pathlib import Path

import pygame

from controls import HOLD_KEYS, SPEEDS

# ---- 模式 ----
# kind 對應 engine.Match 的 mode；ai：有電腦對手；two：可選「雙人同機」
MODE_LIST = [
    ("Battle 2P 限時賽（2 分鐘，KO > 送出行數 > 行高）",
     dict(kind="battle", n=2, time=120, ko=None, ai=True, two=True, title="Battle 2P")),
    ("Battle 6P（你 vs 5 個電腦，10 KO 或 2 分鐘）",
     dict(kind="battle", n=6, time=120, ko=10, ai=True, title="Battle 6P")),
    ("Sprint（單人，消 40 行比時間）", dict(kind="sprint", n=1, title="Sprint")),
    ("Sprint 4P（對 3 個電腦競速）", dict(kind="sprint", n=4, ai=True, title="Sprint 4P")),
    ("Marathon（單人，15 關，越來越快）", dict(kind="marathon", n=1, title="Marathon")),
    ("生死戰（先被頂到頂的人輸）", dict(kind="survival", n=2, ai=True, two=True, title="生死戰")),
]
MODE_KEYS = [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6]


class Settings:
    """遊戲設定，存在 tetris/settings.json（不在 git 裡）。"""

    DEFAULTS = {"sfx": True, "music": True, "ghost": True, "countdown": True, "speed": "中", "hold": "C / ."}
    # 設定畫面上的順序：(按鍵數字, 欄位, 名稱)
    ITEMS = [(1, "sfx", "音效"), (2, "music", "背景音樂"), (3, "ghost", "落點預覽"),
             (4, "countdown", "開局倒數 3 秒"), (5, "speed", "長按移動速度"), (6, "hold", "暫存鍵")]

    def __init__(self, path: Path):
        self.path = path
        self.data = dict(self.DEFAULTS)
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                self.data.update({k: v for k, v in saved.items()
                                  if k in self.DEFAULTS and type(v) is type(self.DEFAULTS[k])})
        except (OSError, ValueError):
            pass
        if self.data["speed"] not in SPEEDS:
            self.data["speed"] = "中"
        if self.data["hold"] not in HOLD_KEYS:
            self.data["hold"] = "C / ."

    def __getitem__(self, key):
        return self.data[key]

    def toggle(self, key: str):
        """開關類切換開 / 關；速度在 慢 → 中 → 快 之間輪流。存檔失敗也照常用。"""
        if key in ("speed", "hold"):
            names = list(SPEEDS if key == "speed" else HOLD_KEYS)
            self.data[key] = names[(names.index(self.data[key]) + 1) % len(names)]
        else:
            self.data[key] = not self.data[key]
        try:
            self.path.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    def label(self, key: str) -> str:
        v = self.data[key]
        return v if key in ("speed", "hold") else ("開" if v else "關")



class Records:
    """最佳成績（Sprint 最快時間、Marathon 最多行數），存在 tetris/records.json。"""

    def __init__(self, path: Path):
        self.path = path
        try:
            self.data = json.loads(path.read_text())
        except (OSError, ValueError):
            self.data = {}

    def submit(self, key: str, value: float, lower_is_better: bool) -> bool:
        old = self.data.get(key)
        if old is not None and (value >= old if lower_is_better else value <= old):
            return False
        self.data[key] = value
        try:
            self.path.write_text(json.dumps(self.data))
        except OSError:
            pass
        return True
