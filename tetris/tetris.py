"""俄羅斯方塊對戰（仿 Tetris Battle 的玩法）。

選單：1 Battle 2P 限時賽、2 Battle 6P、3 Sprint、4 Sprint 4P、5 Marathon、6 生死戰。
消行會把垃圾行送給對手：雙行 1、三行 2、四行 4，T 轉、連擊與連續四行有加成；全清會閃綠光；
自己落地前可以用消行抵銷對方送來的垃圾（左側紅條）。
限時對戰被頂到頂 = 對手 +1 KO，清空重來；多人對戰用 Tab 或滑鼠點小板子換攻擊目標。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

if __name__ == "__main__":  # 先自動更新，再匯入 pygame
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from common.updater import check_and_update
    check_and_update()

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ai import AI, DIFFICULTY  # noqa: E402
from engine import COLS, GARBAGE, LINES_PER_LEVEL, MAX_LEVEL, ROWS, SHAPES, Match  # noqa: E402
from sound import Audio  # noqa: E402

CELL = 28
BOARD_W, BOARD_H = COLS * CELL, ROWS * CELL
TOP = 70
SIDE = 110       # 板子兩側（暫存 / 下一個）的寬度
METER = 12       # 垃圾條寬度
GAP = 40
SMALL = 12       # 多人對戰右側小板子的格子大小
ENEMY_TINT = (255, 130, 90)
PANEL_W = SIDE + METER + 6 + BOARD_W + 10 + SIDE
WIDTH = 2 * PANEL_W + GAP + 40
HEIGHT = TOP + BOARD_H + 30

BG, GRID_BG, GRID_LINE = (16, 18, 26), (24, 27, 38), (32, 36, 50)
TEXT, DIM = (230, 230, 240), (140, 145, 165)
COLORS = {"I": (80, 220, 230), "O": (240, 210, 60), "T": (180, 90, 220), "S": (90, 210, 100),
          "Z": (235, 80, 80), "J": (80, 120, 235), "L": (240, 150, 50), GARBAGE: (110, 115, 130)}

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


def load_font(size):
    for name in ("microsoftjhenghei", "pingfangtc", "notosanscjktc", "notosanscjk",
                 "wenquanyizenhei", "arialunicodems"):
        path = pygame.font.match_font(name)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.Font(None, size + 6)


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


def draw_cell(screen, x, y, color, size=CELL, alpha=None):
    rect = pygame.Rect(x, y, size, size)
    radius = 4 if size >= 20 else 2
    if alpha is not None:
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(s, (*color, alpha), (1, 1, size - 2, size - 2), border_radius=radius)
        screen.blit(s, rect)
        return
    pygame.draw.rect(screen, color, rect.inflate(-2, -2), border_radius=radius)
    if size >= 20:
        light = tuple(min(255, c + 50) for c in color)
        pygame.draw.rect(screen, light, (x + 3, y + 3, size - 6, 4), border_radius=2)


def draw_mini(screen, kind, cx, cy, size=18):
    """在 (cx, cy) 為中心畫縮小的方塊。"""
    cells = SHAPES[kind][0]
    xs, ys = [c[0] for c in cells], [c[1] for c in cells]
    w, h = (max(xs) - min(xs) + 1) * size, (max(ys) - min(ys) + 1) * size
    for x, y in cells:
        draw_cell(screen, cx - w // 2 + (x - min(xs)) * size, cy - h // 2 + (y - min(ys)) * size,
                  COLORS[kind], size)


def draw_board(screen, p, bx, by, cell, tint, ghost=True):
    """畫一塊 10x20 的板子（含目前方塊、落點預覽、外框、死亡遮罩）。"""
    w, h = COLS * cell, ROWS * cell
    pygame.draw.rect(screen, GRID_BG, (bx, by, w, h))
    if cell >= 20:
        for i in range(1, COLS):
            pygame.draw.line(screen, GRID_LINE, (bx + i * cell, by), (bx + i * cell, by + h))
        for i in range(1, ROWS):
            pygame.draw.line(screen, GRID_LINE, (bx, by + i * cell), (bx + w, by + i * cell))
    for y, row in enumerate(p.grid):
        for x, c in enumerate(row):
            if c:
                draw_cell(screen, bx + x * cell, by + y * cell, COLORS[c], cell)
    if p.alive and not p.done:
        if ghost:
            dy = p.ghost_y() - p.y
            for cx, cy in p.cells():
                if cy + dy >= 0:
                    draw_cell(screen, bx + cx * cell, by + (cy + dy) * cell, COLORS[p.kind], cell, alpha=70)
        for cx, cy in p.cells():
            if cy >= 0:
                draw_cell(screen, bx + cx * cell, by + cy * cell, COLORS[p.kind], cell)
    pygame.draw.rect(screen, tint, (bx - 2, by - 2, w + 4, h + 4), 2, border_radius=3)
    if not p.alive:
        shade = pygame.Surface((w, h), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 150))
        screen.blit(shade, (bx, by))


def draw_player(screen, p, left, fonts, name, tint, info, ghost=True):
    """大板子：暫存、下一個、垃圾條、提示文字。"""
    big, small = fonts
    hold_x = left
    meter_x = left + SIDE
    bx = meter_x + METER + 6
    next_x = bx + BOARD_W + 10

    draw_board(screen, p, bx, TOP, CELL, tint, ghost)

    # 垃圾條
    pygame.draw.rect(screen, GRID_BG, (meter_x, TOP, METER, BOARD_H))
    incoming = min(sum(p.pending), ROWS)
    if incoming:
        pygame.draw.rect(screen, (230, 60, 60),
                         (meter_x, TOP + BOARD_H - incoming * CELL, METER, incoming * CELL))

    # 暫存、下一個
    screen.blit(small.render("暫存", True, DIM), (hold_x + 10, TOP))
    pygame.draw.rect(screen, GRID_BG, (hold_x + 6, TOP + 28, SIDE - 16, 70), border_radius=6)
    if p.hold_kind:
        draw_mini(screen, p.hold_kind, hold_x + 6 + (SIDE - 16) // 2, TOP + 63)
        if not p.can_hold:
            s = pygame.Surface((SIDE - 16, 70), pygame.SRCALPHA)
            s.fill((0, 0, 0, 120))
            screen.blit(s, (hold_x + 6, TOP + 28))
    screen.blit(small.render("下一個", True, DIM), (next_x + 10, TOP))
    for i, kind in enumerate(p.queue[:4]):
        draw_mini(screen, kind, next_x + SIDE // 2, TOP + 55 + i * 62, 16 if i else 20)

    # 文字
    screen.blit(big.render(name, True, tint), (bx, 14))
    screen.blit(small.render(info, True, TEXT), (bx, TOP + BOARD_H + 4))
    if p.last_event and p.event_age < 1.5:
        s = small.render(p.last_event, True, (255, 220, 90))
        screen.blit(s, s.get_rect(center=(bx + BOARD_W // 2, TOP + BOARD_H // 2 - 60)))
    if p.glow < 1.6:  # 全清：綠光由亮漸隱
        k = 1 - p.glow / 1.6
        glow = pygame.Surface((BOARD_W + 60, BOARD_H + 60), pygame.SRCALPHA)
        for i in range(30):
            pygame.draw.rect(glow, (60, 255, 120, int(200 * k * (1 - i / 30) ** 2)),
                             (i, i, BOARD_W + 60 - 2 * i, BOARD_H + 60 - 2 * i), 1, border_radius=14)
        screen.blit(glow, (bx - 30, TOP - 30))
        shade = pygame.Surface((BOARD_W, BOARD_H), pygame.SRCALPHA)
        shade.fill((60, 255, 120, int(90 * k)))
        screen.blit(shade, (bx, TOP))


def draw_reticle(screen, cx, cy, r):
    """鎖定目標的準星。"""
    pygame.draw.circle(screen, (90, 230, 255), (cx, cy), r, 3)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        pygame.draw.line(screen, (90, 230, 255), (cx + dx * (r - 8), cy + dy * (r - 8)),
                         (cx + dx * (r + 10), cy + dy * (r + 10)), 3)


def draw_small(screen, p, x, y, small, name, info, targeted):
    """右側的小板子；回傳它的範圍，讓滑鼠點擊可以選目標。"""
    w, h = COLS * SMALL, ROWS * SMALL
    screen.blit(small.render(name, True, ENEMY_TINT), (x, y))
    by = y + 26
    draw_board(screen, p, x, by, SMALL, ENEMY_TINT, ghost=False)
    incoming = min(sum(p.pending), ROWS)
    if incoming:
        pygame.draw.rect(screen, (230, 60, 60), (x - 8, by + h - incoming * SMALL, 5, incoming * SMALL))
    screen.blit(small.render(info, True, TEXT), (x, by + h + 4))
    if targeted:
        draw_reticle(screen, x + w // 2, by + h // 2, 34)
    if p.last_event and p.event_age < 1.2:
        s = small.render(p.last_event, True, (255, 220, 90))
        screen.blit(s, s.get_rect(center=(x + w // 2, by + h // 2 - 30)))
    return pygame.Rect(x, by, w, h)


def center_text(screen, text, font, y, color=TEXT, x=None):
    surf = font.render(text, True, color)
    screen.blit(surf, surf.get_rect(center=(WIDTH // 2 if x is None else x, y)))


def fmt_time(t):
    return f"{int(t) // 60}:{t % 60:05.2f}"


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


def draw_menu(screen, fonts, state, cfg=None):
    big, small = fonts
    screen.fill(BG)
    center_text(screen, "俄羅斯方塊對戰", big, 90, (120, 220, 235))
    if state == "menu":
        for i, (label, _) in enumerate(MODE_LIST, 1):
            center_text(screen, f"{i}  {label}", small, 170 + (i - 1) * 42)
        center_text(screen, "0  設定", small, 170 + len(MODE_LIST) * 42, (120, 220, 235))
        center_text(screen, "數字鍵選擇（上排或數字鍵盤都可以）　Esc 離開　M 全部靜音",
                    small, 170 + len(MODE_LIST) * 42 + 40, DIM)
    elif state == "settings":
        center_text(screen, "設定", big, 170, TEXT)
        for i, (k, key, name) in enumerate(Settings.ITEMS):
            center_text(screen, f"{k}  {name}：{cfg.label(key)}", small, 240 + i * 44)
        center_text(screen, "按數字切換（會自動存檔）　Esc / Backspace 返回",
                    small, 240 + len(Settings.ITEMS) * 44 + 10, DIM)
    else:
        center_text(screen, cfg["title"], big, 180, TEXT)
        items = [f"{i}  對電腦（{n}）" for i, n in enumerate(DIFFICULTY, 1)]
        if cfg.get("two"):
            items.append("4  雙人同機")
        for i, t in enumerate(items):
            center_text(screen, t, small, 260 + i * 44)
        center_text(screen, "Esc / Backspace 返回", small, 260 + len(items) * 44 + 10, DIM)
    h1, h2 = hold_names(HOLD_NAME[0])
    lines = [f"玩家 1：A D 移動　S 軟降　W 順轉　Q 逆轉　空白 硬降　{h1} 暫存",
             f"玩家 2：← → 移動　↓ 軟降　↑ 順轉　/ 逆轉　Enter 硬降　{h2} 暫存",
             "對電腦時兩組按鍵都能用　P 或 Esc 暫停　Tab / 滑鼠點小板子：換攻擊目標"]
    for i, t in enumerate(lines):
        center_text(screen, t, small, HEIGHT - 90 + i * 26, DIM)
    pygame.display.flip()


def hud_text(match, cfg):
    """上方正中央的計時 / 進度字樣。"""
    p = match.players[0]
    if cfg["kind"] == "battle":
        t = int(match.time_left + 0.999)
        return f"{t // 60}:{t % 60:02d}"
    if cfg["kind"] == "sprint":
        return f"{fmt_time(match.elapsed)}　剩 {max(0, match.goal_lines - p.lines)} 行"
    if cfg["kind"] == "marathon":
        lvl = min(p.level, MAX_LEVEL)
        return f"第 {lvl}/{MAX_LEVEL} 關　本關剩 {LINES_PER_LEVEL - p.lines % LINES_PER_LEVEL} 行"
    return ""


def player_info(p, match, cfg):
    if cfg["kind"] == "battle":
        return f"KO {p.ko}　送出 {p.sent}"
    if cfg["kind"] in ("sprint", "marathon"):
        return f"消行 {p.lines}　等級 {min(p.level, MAX_LEVEL)}"
    return f"消行 {p.lines}　送出 {p.sent}"


def draw_result(screen, fonts, match, cfg, names, wins, records_note):
    big, small = fonts
    lines = []
    kind = cfg["kind"]
    if kind in ("survival",) or (kind == "battle" and match.winner == -1 and len(names) == 2):
        lines.append("平手" if match.winner == -1 else f"{names[match.winner]} 獲勝！")
    elif kind == "battle":
        lines.append("平手" if match.winner == -1 else f"{names[match.winner]} 獲勝！")
        for rank, i in enumerate(match.ranks, 1):
            p = match.players[i]
            lines.append(f"{rank}. {names[i]}　KO {p.ko}　送出 {p.sent}　行高 {p.height()}")
    elif len(match.players) == 1:
        if match.success:
            lines.append(f"完成！用時 {fmt_time(match.finish[0])}")
        else:
            lines.append("遊戲結束")
            lines.append(f"消了 {match.players[0].lines} 行（第 {min(match.players[0].level, MAX_LEVEL)} 關）")
    else:
        lines.append("你完成了！" if match.winner == 0 else "比賽結束")
        for rank, i in enumerate(match.ranks, 1):
            t = match.finish[i]
            lines.append(f"{rank}. {names[i]}　" + (fmt_time(t) if t is not None else "未完成"))
    if records_note:
        lines.append(records_note)
    lines.append("空白鍵 / Enter / R 再來一局，Esc / Backspace 回選單")
    h = 70 + 30 * len(lines)
    panel = pygame.Surface((620, h), pygame.SRCALPHA)
    panel.fill((10, 12, 20, 225))
    rect = panel.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    screen.blit(panel, rect)
    pygame.draw.rect(screen, (255, 220, 90), rect, 2, border_radius=6)
    for i, t in enumerate(lines):
        font = big if i == 0 else small
        color = (255, 220, 90) if i == 0 else (DIM if i >= len(lines) - 1 else TEXT)
        center_text(screen, t, font, rect.top + 40 + i * 30 + (8 if i else 0), color)


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("俄羅斯方塊對戰")
    fonts = (load_font(30), load_font(18))
    clock = pygame.time.Clock()
    audio = Audio()
    records = Records(Path(__file__).parent / "records.json")
    settings = Settings(Path(__file__).parent / "settings.json")
    set_speed(settings["speed"])
    set_hold(settings["hold"])
    audio.apply(settings["sfx"], settings["music"])

    state, cfg, diff = "menu", None, None  # state: menu / diff / settings / play
    match = controls = None
    ais: dict[int, AI] = {}
    names: list[str] = []
    wins = [0, 0]
    countdown, paused, scored = 0.0, False, False
    last_beep, last_tick, records_note = 0, None, ""
    seen = []  # 每位玩家上一幀的 (alive, deaths)，用來播「死亡」音效
    small_rects: list[tuple[pygame.Rect, int]] = []

    def flush_sfx():
        """取走各玩家這一步的音效事件並播放；電腦的聲音只在 2 人對戰時以小音量播攻擊音效。"""
        n = len(match.players)
        for i, p in enumerate(match.players):
            events, p.sfx = p.sfx, []
            for name in dict.fromkeys(events):  # 同一類聲音一次只播一個
                if i in ais:
                    if name == "ko":
                        audio.play(name, 0.5)
                    elif n == 2 and (name.startswith("clear") or name in ("tspin", "perfect")):
                        audio.play(name, 0.4)
                else:
                    audio.play(name)

    def start(c, d):
        nonlocal match, controls, ais, names, state, cfg, diff, countdown, paused, scored
        nonlocal last_beep, last_tick, records_note, seen
        cfg, diff, state = c, d, "play"
        countdown, paused, scored, last_beep, last_tick, records_note = 3.0, False, False, 0, None, ""
        audio.stop_music(0)
        if not settings["countdown"]:  # 設定關掉倒數：直接開始
            countdown = 0.0
            audio.play("go")
            audio.start_music()
        match = Match(n=c["n"], mode=c["kind"], time_limit=c.get("time"), ko_limit=c.get("ko"))
        seen = [(True, 0)] * c["n"]
        two_humans = d is None
        if two_humans:
            ais, names = {}, ["玩家 1", "玩家 2"]
            controls = [Controls([P1_KEYS]), Controls([P2_KEYS])]
        else:
            interval = DIFFICULTY[d]
            ais = {i: AI(interval) for i in range(1, c["n"]) } if c.get("ai") else {}
            names = ["玩家 1"] + [f"電腦 {i}" if c["n"] > 2 else f"電腦（{d}）" for i in range(1, c["n"])]
            controls = [Controls([P1_KEYS, P2_KEYS])]
        if c["n"] > 2:
            match.players[0].target = 1

    def draw_scene():
        nonlocal small_rects
        n = len(match.players)
        small_rects = []
        tints = ((90, 190, 255), (255, 130, 90))
        left1 = 20
        if n == 2:
            left2 = left1 + PANEL_W + GAP
            for i, left in enumerate((left1, left2)):
                draw_player(screen, match.players[i], left, fonts, names[i], tints[i],
                            player_info(match.players[i], match, cfg), settings["ghost"])
            if cfg["kind"] != "battle":
                center_text(screen, f"{wins[0]} : {wins[1]}", fonts[0], 40, TEXT)
        else:
            draw_player(screen, match.players[0], left1, fonts, names[0], tints[0],
                        player_info(match.players[0], match, cfg), settings["ghost"])
            x0 = left1 + PANEL_W + 40
            for k in range(1, n):
                col, row = (k - 1) % 3, (k - 1) // 3
                x, y = x0 + col * (COLS * SMALL + 36), 56 + row * 288
                if cfg["kind"] == "battle":
                    info = player_info(match.players[k], match, cfg)
                else:
                    t = match.finish[k]
                    info = fmt_time(t) if t is not None else f"剩 {max(0, match.goal_lines - match.players[k].lines)} 行"
                rect = draw_small(screen, match.players[k], x, y, fonts[1], names[k], info,
                                  match.players[0].target == k)
                small_rects.append((rect, k))
            if cfg["kind"] == "battle" and n > 3:  # 右下角：即時排名
                x, y = x0 + 2 * (COLS * SMALL + 36), 56 + 288
                order = sorted(range(n), key=match._rank_key, reverse=True)
                fonts[1].set_bold(False)
                screen.blit(fonts[1].render("排名", True, DIM), (x, y))
                for r, i in enumerate(order):
                    color = tints[0] if i == 0 else TEXT
                    screen.blit(fonts[1].render(f"{r + 1}. {names[i]}  KO {match.players[i].ko}", True, color),
                                (x, y + 26 + r * 24))
        if n == 1:
            x = left1 + PANEL_W + 60
            rows = [("用時", fmt_time(match.elapsed)), ("消行", str(match.players[0].lines)),
                    ("等級", f"{min(match.players[0].level, MAX_LEVEL)} / {MAX_LEVEL}" if cfg["kind"] == "marathon" else "-"),
                    ("最佳", fmt_time(records.data["sprint"]) if cfg["kind"] == "sprint" and "sprint" in records.data
                     else (f"{records.data['marathon']} 行" if cfg["kind"] == "marathon" and "marathon" in records.data else "-"))]
            for i, (k, v) in enumerate(rows):
                screen.blit(fonts[1].render(k, True, DIM), (x, TOP + i * 70))
                screen.blit(fonts[0].render(v, True, TEXT), (x, TOP + 24 + i * 70))
        center_text(screen, hud_text(match, cfg), fonts[0], 28 if n > 2 else 40)

    while True:
        dt = min(clock.tick(60) / 1000, 0.05)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                return
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and state == "play":
                for rect, k in small_rects:
                    if rect.collidepoint(ev.pos):
                        match.set_target(0, k)
                continue
            if ev.type != pygame.KEYDOWN:
                continue
            num = digit(ev.key)
            if ev.key == pygame.K_m:
                audio.toggle_mute(paused)
            elif state == "menu":
                if ev.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return
                if num == 0:
                    state = "settings"
                elif num is not None and 1 <= num <= len(MODE_LIST):
                    c = MODE_LIST[num - 1][1]
                    if c.get("ai"):
                        cfg, state = c, "diff"
                    else:
                        start(c, "普通")
            elif state == "settings":
                if ev.key in BACK_KEYS:
                    state = "menu"
                else:
                    item = next((key for k, key, _ in Settings.ITEMS if k == num), None)
                    if item:
                        settings.toggle(item)
                        set_speed(settings["speed"])
                        set_hold(settings["hold"])
                        audio.apply(settings["sfx"], settings["music"])
            elif state == "diff":
                names_d = list(DIFFICULTY)
                if ev.key in BACK_KEYS:
                    state = "menu"
                elif num in (1, 2, 3):
                    start(cfg, names_d[num - 1])
                elif num == 4 and cfg.get("two"):
                    start(cfg, None)
            elif state == "play":
                if match.over:
                    if ev.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_r):
                        start(cfg, diff)
                    elif ev.key in BACK_KEYS:
                        state = "menu"
                        audio.stop_music()
                elif ev.key in (pygame.K_p, pygame.K_ESCAPE):
                    paused = not paused
                    audio.pause_music(paused)
                elif paused:
                    if ev.key == pygame.K_r:
                        start(cfg, diff)
                    elif ev.key == pygame.K_BACKSPACE:
                        state, paused = "menu", False
                        audio.stop_music()
                elif ev.key in (pygame.K_TAB, pygame.K_t) and len(match.players) > 2:
                    match.cycle_target(0)
                elif countdown <= 0 and not paused and not match.over:
                    for i, c in enumerate(controls):
                        c.keydown(ev.key, match, i)
                    flush_sfx()

        if state in ("menu", "diff", "settings"):
            draw_menu(screen, fonts, state, settings if state == "settings" else cfg)
            continue

        if countdown > 0 and not paused:
            countdown -= dt
            beep = int(countdown) + 1 if countdown > 0 else 0
            if beep != last_beep:  # 3、2、1 各響一聲，開始時響「Go」並開音樂
                audio.play("countdown" if beep else "go")
                if not beep:
                    audio.start_music()
                last_beep = beep
        elif not paused and not match.over:
            pressed = pygame.key.get_pressed()
            for i, c in enumerate(controls):
                c.update(dt, match.players[i], pressed)
            for i, a in ais.items():
                a.update(dt, match.players[i])
                if len(match.players) > 2 and cfg["kind"] == "battle":
                    a.choose_target(dt, match, i)
            match.update(dt)
            flush_sfx()
            left = match.time_left
            if left is not None and left <= 5 and int(left) != last_tick:  # 最後 5 秒倒數
                last_tick = int(left)
                audio.play("countdown", 0.6)

        # 死亡、勝負音效：硬降也可能結束比賽，所以不放在上面的更新區塊裡
        for i, p in enumerate(match.players):
            was_alive, deaths = seen[i]
            if (was_alive and not p.alive or p.deaths > deaths) and (i == 0 or i not in ais):
                audio.play("dead")
            seen[i] = (p.alive, p.deaths)
        if match.over and not scored:
            scored = True
            audio.stop_music(1200)
            if cfg["kind"] == "sprint" and match.finish[0] is not None:
                if records.submit("sprint", round(match.finish[0], 2), True):
                    records_note = "新紀錄！"
            elif cfg["kind"] == "marathon":
                if records.submit("marathon", match.players[0].lines, False):
                    records_note = "新紀錄！"
            if len(match.players) == 2 and match.winner in (0, 1):
                wins[match.winner] += 1
            win = match.winner == 0 or (match.winner == 1 and not ais)
            audio.play("win" if win or match.success else "dead")

        screen.fill(BG)
        draw_scene()
        if paused:
            shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 150))
            screen.blit(shade, (0, 0))
            center_text(screen, "暫停中", fonts[0], TOP + BOARD_H // 2 - 40)
            center_text(screen, "Esc 或 P：返回遊戲　R：重新開始　Backspace：回主選單",
                        fonts[1], TOP + BOARD_H // 2 + 10)
        elif countdown > 0:
            center_text(screen, str(int(countdown) + 1), fonts[0], TOP + BOARD_H // 2, (255, 220, 90),
                        x=20 + PANEL_W // 2 if len(match.players) != 2 else None)
        elif match.over:
            draw_result(screen, fonts, match, cfg, names, wins, records_note)
        pygame.display.flip()


if __name__ == "__main__":
    main()
