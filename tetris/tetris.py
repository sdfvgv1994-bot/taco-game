"""俄羅斯方塊對戰。

選單：1~3 對電腦（簡單 / 普通 / 困難），4 雙人對戰，Esc 離開。
消行會把垃圾行送給對手：雙行 1、三行 2、四行 4，T 轉、連擊與連續四行有加成；全清會閃綠光；
自己落地前可以用消行抵銷對方送來的垃圾（左側紅條）。先被頂到頂的人輸。
"""
from __future__ import annotations

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
from engine import COLS, GARBAGE, ROWS, SHAPES, Match  # noqa: E402
from sound import Audio  # noqa: E402

CELL = 28
BOARD_W, BOARD_H = COLS * CELL, ROWS * CELL
TOP = 70
SIDE = 110       # 板子兩側（暫存 / 下一個）的寬度
METER = 12       # 垃圾條寬度
GAP = 40
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
DAS, ARR = 0.16, 0.04  # 長按多久開始連續移動、之後每幾秒一格


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
    if alpha is not None:
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(s, (*color, alpha), (1, 1, size - 2, size - 2), border_radius=4)
        screen.blit(s, rect)
        return
    pygame.draw.rect(screen, color, rect.inflate(-2, -2), border_radius=4)
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


def draw_player(screen, p, left, fonts, name, tint):
    big, small = fonts
    hold_x = left
    meter_x = left + SIDE
    bx = meter_x + METER + 6
    next_x = bx + BOARD_W + 10

    # 板子
    pygame.draw.rect(screen, GRID_BG, (bx, TOP, BOARD_W, BOARD_H))
    for i in range(1, COLS):
        pygame.draw.line(screen, GRID_LINE, (bx + i * CELL, TOP), (bx + i * CELL, TOP + BOARD_H))
    for i in range(1, ROWS):
        pygame.draw.line(screen, GRID_LINE, (bx, TOP + i * CELL), (bx + BOARD_W, TOP + i * CELL))
    for y, row in enumerate(p.grid):
        for x, c in enumerate(row):
            if c:
                draw_cell(screen, bx + x * CELL, TOP + y * CELL, COLORS[c])
    if p.alive:
        gy = p.ghost_y()
        for cx, cy in [(x, y + gy - p.y) for x, y in p.cells()]:
            if cy >= 0:
                draw_cell(screen, bx + cx * CELL, TOP + cy * CELL, COLORS[p.kind], alpha=70)
        for cx, cy in p.cells():
            if cy >= 0:
                draw_cell(screen, bx + cx * CELL, TOP + cy * CELL, COLORS[p.kind])
    pygame.draw.rect(screen, tint, (bx - 2, TOP - 2, BOARD_W + 4, BOARD_H + 4), 2, border_radius=3)

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
    info = f"消行 {p.lines}   送出 {p.sent}"
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
    if not p.alive:
        shade = pygame.Surface((BOARD_W, BOARD_H), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 150))
        screen.blit(shade, (bx, TOP))


def center_text(screen, text, font, y, color=TEXT):
    surf = font.render(text, True, color)
    screen.blit(surf, surf.get_rect(center=(WIDTH // 2, y)))


def draw_menu(screen, fonts):
    big, small = fonts
    screen.fill(BG)
    center_text(screen, "俄羅斯方塊對戰", big, 130, (120, 220, 235))
    items = [f"{i}  對電腦（{n}）" for i, n in enumerate(DIFFICULTY, 1)] + ["4  雙人對戰（同一台電腦）"]
    for i, t in enumerate(items):
        center_text(screen, t, small, 230 + i * 44)
    center_text(screen, "Esc 離開", small, 230 + len(items) * 44 + 10, DIM)
    lines = ["玩家 1：A D 移動　S 軟降　W 順轉　Q 逆轉　空白 硬降　左 Shift 暫存",
             "玩家 2：← → 移動　↓ 軟降　↑ 順轉　/ 逆轉　Enter 硬降　右 Shift 暫存",
             "對電腦時兩組按鍵都能用　P 暫停　M 音效 / 音樂開關"]
    for i, t in enumerate(lines):
        center_text(screen, t, small, HEIGHT - 110 + i * 28, DIM)
    pygame.display.flip()


MODES = {pygame.K_1: ("簡單", True), pygame.K_2: ("普通", True), pygame.K_3: ("困難", True),
         pygame.K_4: (None, False)}


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("俄羅斯方塊對戰")
    fonts = (load_font(30), load_font(18))
    clock = pygame.time.Clock()
    audio = Audio()

    state, mode = "menu", None
    match = ai = controls = None
    wins = [0, 0]
    countdown, paused, scored = 0.0, False, False
    last_beep = 0
    alive_before = [True, True]

    def flush_sfx():
        """取走兩邊玩家這一步的音效事件並播放（對電腦時，電腦只發出攻擊相關的聲音）。"""
        for i, p in enumerate(match.players):
            events, p.sfx = p.sfx, []
            for name in dict.fromkeys(events):  # 同一類聲音一次只播一個
                if i == 1 and mode[1]:
                    if name.startswith("clear") or name in ("tspin", "perfect"):
                        audio.play(name, 0.4)
                else:
                    audio.play(name)

    def start(m):
        nonlocal match, ai, controls, state, mode, countdown, paused, scored, last_beep
        mode, state, countdown, paused, scored = m, "play", 3.0, False, False
        last_beep = 0
        alive_before[:] = [True, True]
        audio.stop_music(0)
        match = Match()
        if m[1]:
            ai = AI(DIFFICULTY[m[0]])
            controls = [Controls([P1_KEYS, P2_KEYS])]
        else:
            ai = None
            controls = [Controls([P1_KEYS]), Controls([P2_KEYS])]

    while True:
        dt = min(clock.tick(60) / 1000, 0.05)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                return
            if ev.type != pygame.KEYDOWN:
                continue
            if ev.key == pygame.K_ESCAPE:
                if state == "menu":
                    pygame.quit()
                    return
                state = "menu"
                audio.stop_music()
            elif ev.key == pygame.K_m:
                audio.toggle_mute(paused)
            elif state == "menu" and ev.key in MODES:
                start(MODES[ev.key])
            elif state == "play":
                if ev.key == pygame.K_p and not match.over:
                    paused = not paused
                    audio.pause_music(paused)
                elif match.over and ev.key in (pygame.K_SPACE, pygame.K_RETURN):
                    start(mode)
                elif countdown <= 0 and not paused and not match.over:
                    for i, c in enumerate(controls):
                        c.keydown(ev.key, match, i)
                    flush_sfx()

        if state == "menu":
            draw_menu(screen, fonts)
            continue

        if countdown > 0:
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
            if ai:
                ai.update(dt, match.players[1])
            match.update(dt)
            flush_sfx()

        # 勝負、死亡音效：硬降也可能結束比賽，所以不放在上面的更新區塊裡
        for i, p in enumerate(match.players):
            if alive_before[i] and not p.alive and (i == 0 or not mode[1]):
                audio.play("dead")
            alive_before[i] = p.alive
        if match.over and not scored:
            scored = True
            audio.stop_music(1200)
            if match.winner in (0, 1):
                wins[match.winner] += 1
                if match.winner == 0 or not mode[1]:
                    audio.play("win")

        screen.fill(BG)
        names = ("玩家 1", "電腦（%s）" % mode[0]) if mode[1] else ("玩家 1", "玩家 2")
        tints = ((90, 190, 255), (255, 130, 90))
        left1 = 20
        left2 = left1 + PANEL_W + GAP
        draw_player(screen, match.players[0], left1, fonts, names[0], tints[0])
        draw_player(screen, match.players[1], left2, fonts, names[1], tints[1])
        center_text(screen, f"{wins[0]} : {wins[1]}", fonts[0], 40, TEXT)
        if countdown > 0:
            center_text(screen, str(int(countdown) + 1), fonts[0], TOP + BOARD_H // 2, (255, 220, 90))
        elif paused:
            center_text(screen, "暫停中（P 繼續）", fonts[0], TOP + BOARD_H // 2)
        elif match.over:
            msg = "平手" if match.winner == -1 else f"{names[match.winner]} 獲勝！"
            center_text(screen, msg, fonts[0], TOP + BOARD_H // 2 - 20, (255, 220, 90))
            center_text(screen, "空白鍵 / Enter 再來一局，Esc 回選單", fonts[1], TOP + BOARD_H // 2 + 20)
        pygame.display.flip()


if __name__ == "__main__":
    main()
