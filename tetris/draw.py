"""俄羅斯方塊：畫面（tetris.py 拆出來的積木）。

- 版面尺寸、顏色
- 板子、方塊、暫存／下一個、垃圾條、多人小板子、準星
- 選單、設定、難度畫面，上方計時字樣，結算面板
"""
from __future__ import annotations

import pygame

from ai import DIFFICULTY
from controls import HOLD_NAME, hold_names
from engine import COLS, GARBAGE, LINES_PER_LEVEL, MAX_LEVEL, ROWS, SHAPES
from options import MODE_LIST, Settings

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


def load_font(size):
    for name in ("microsoftjhenghei", "pingfangtc", "notosanscjktc", "notosanscjk",
                 "wenquanyizenhei", "arialunicodems"):
        path = pygame.font.match_font(name)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.Font(None, size + 6)


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
