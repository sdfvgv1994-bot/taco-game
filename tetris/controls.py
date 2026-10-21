"""俄羅斯方塊：按鍵設定與操作（tetris.py 拆出來的積木）。

- 兩位玩家的按鍵、暫存鍵（C / . 或 Shift）、長按移動速度（DAS / ARR）
- 選單用的數字鍵（上排、數字鍵盤都可以）與返回鍵
- Controls：把按鍵轉成對 Player 的操作，含長按連續移動
"""
from __future__ import annotations

import pygame

# 每位玩家的按鍵：左、右、軟降、順轉、逆轉、硬降、暫存
P1_KEYS = dict(left=pygame.K_a, right=pygame.K_d, down=pygame.K_s, cw=pygame.K_w, ccw=pygame.K_q,
               drop=pygame.K_SPACE, hold=pygame.K_LSHIFT)
P2_KEYS = dict(left=pygame.K_LEFT, right=pygame.K_RIGHT, down=pygame.K_DOWN, cw=pygame.K_UP,
               ccw=pygame.K_SLASH, drop=pygame.K_RETURN, hold=pygame.K_RSHIFT)
# 暫存鍵：Shift 在注音輸入法會切換中英文，所以預設用 C（玩家 1）和 .（玩家 2），設定裡可以換回 Shift
HOLD_KEYS = {"C / .": (pygame.K_c, pygame.K_PERIOD), "Shift": (pygame.K_LSHIFT, pygame.K_RSHIFT)}
DAS, ARR = 0.16, 0.04  # 長按多久開始連續移動、之後每幾秒一格（設定畫面可以改）
SPEEDS = {"慢": (0.22, 0.06), "中": (0.16, 0.04), "快": (0.10, 0.02)}  # 長按移動速度：(DAS, ARR)

# 上排數字鍵和右邊數字鍵盤都能選選單
DIGIT_KEYS = {getattr(pygame, f"K_{i}"): i for i in range(10)}
DIGIT_KEYS.update({getattr(pygame, f"K_KP{i}"): i for i in range(10)})
BACK_KEYS = (pygame.K_ESCAPE, pygame.K_BACKSPACE)


def digit(key) -> int | None:
    """按下的是數字鍵（上排或數字鍵盤）就回傳數字，不是就回傳 None。"""
    return DIGIT_KEYS.get(key)


HOLD_NAME = ["C / ."]  # 目前的暫存鍵設定（說明文字用）


def set_hold(name: str):
    """套用暫存鍵（C / . 或 Shift）。"""
    HOLD_NAME[0] = name if name in HOLD_KEYS else "C / ."
    P1_KEYS["hold"], P2_KEYS["hold"] = HOLD_KEYS[HOLD_NAME[0]]


def hold_names(name: str) -> tuple[str, str]:
    """說明文字用：玩家 1、玩家 2 的暫存鍵名稱。"""
    return ("左 Shift", "右 Shift") if name == "Shift" else ("C", ".")


def set_speed(name: str):
    """套用長按移動速度（慢 / 中 / 快）。"""
    global DAS, ARR
    DAS, ARR = SPEEDS.get(name, SPEEDS["中"])


class Controls:
    """把一組按鍵轉成對 Player 的操作，含長按連續移動。"""

    def __init__(self, keys_list):
        self.keys_list = keys_list
        self.held = {}  # 方向 -> 已按住的秒數

    def _match(self, key, name):
        return any(k[name] == key for k in self.keys_list)

    def keydown(self, key, match, i):
        p = match.players[i]
        if self._match(key, "left"):
            p.move(-1)
            self.held = {-1: 0.0}
        elif self._match(key, "right"):
            p.move(1)
            self.held = {1: 0.0}
        elif self._match(key, "cw"):
            p.rotate(1)
        elif self._match(key, "ccw"):
            p.rotate(-1)
        elif self._match(key, "hold"):
            p.hold()
        elif self._match(key, "drop"):
            match.hard_drop(i)

    def update(self, dt, player, pressed):
        player.soft = any(pressed[k["down"]] for k in self.keys_list)
        for d in list(self.held):
            name = "left" if d < 0 else "right"
            if not any(pressed[k[name]] for k in self.keys_list):
                del self.held[d]
                continue
            self.held[d] += dt
            while self.held[d] >= DAS + ARR:  # 超過 DAS 後，每 ARR 秒走一格
                self.held[d] -= ARR
                player.move(d)
