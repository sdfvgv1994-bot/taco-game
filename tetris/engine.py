"""俄羅斯方塊對戰的遊戲邏輯（不含畫面，方便測試）。"""
from __future__ import annotations

import random

COLS, ROWS = 10, 20
LOCK_DELAY = 0.5
MAX_LOCK_RESETS = 15
SOFT_INTERVAL = 0.03
MAX_GARBAGE_PER_LOCK = 8
ATTACK = {0: 0, 1: 0, 2: 1, 3: 2, 4: 4}  # 消幾行 -> 送出幾行垃圾
COMBO_BONUS = [0, 0, 1, 1, 2, 2, 3, 3, 4]
PERFECT_CLEAR = 6
TSPIN_ATTACK = {1: 2, 2: 4, 3: 6}  # T 轉消幾行 -> 送出幾行垃圾
GARBAGE = "G"

_BASE = {
    "I": (4, [(0, 1), (1, 1), (2, 1), (3, 1)]),
    "O": (2, [(0, 0), (1, 0), (0, 1), (1, 1)]),
    "T": (3, [(1, 0), (0, 1), (1, 1), (2, 1)]),
    "S": (3, [(1, 0), (2, 0), (0, 1), (1, 1)]),
    "Z": (3, [(0, 0), (1, 0), (1, 1), (2, 1)]),
    "J": (3, [(0, 0), (0, 1), (1, 1), (2, 1)]),
    "L": (3, [(2, 0), (0, 1), (1, 1), (2, 1)]),
}
KINDS = list(_BASE)
KICKS = [(0, 0), (-1, 0), (1, 0), (-2, 0), (2, 0), (0, -1), (-1, -1), (1, -1)]


def _build_shapes():
    shapes = {}
    for kind, (size, cells) in _BASE.items():
        rots = [cells]
        for _ in range(3):
            cells = [(size - 1 - y, x) for x, y in cells]  # 順時針轉 90 度
            rots.append(cells)
        shapes[kind] = rots
    return shapes


SHAPES = _build_shapes()


def piece_cells(kind, rot, x, y):
    return [(x + cx, y + cy) for cx, cy in SHAPES[kind][rot % 4]]


class Player:
    def __init__(self, rng: random.Random | None = None):
        self.rng = rng or random.Random()
        self.grid = [[None] * COLS for _ in range(ROWS)]
        self.bag: list[str] = []
        self.queue = [self._draw() for _ in range(5)]
        self.hold_kind: str | None = None
        self.can_hold = True
        self.alive = True
        self.lines = 0
        self.combo = -1
        self.b2b = False
        self.pending: list[int] = []  # 對手送來、還沒落下的垃圾行
        self.outbox = 0               # 這一步要送給對手的垃圾行
        self.sent = 0
        self.soft = False
        self.last_event = ""          # 畫面上顯示的提示，例如「四行消除」
        self.event_age = 0.0
        self.glow = 99.0              # 全清後經過的秒數，畫面用來顯示綠光
        self.sfx: list[str] = []      # 這一步發生的音效事件，由畫面取走播放
        self.last_rotate = False      # 最後一個動作是不是旋轉（T 轉判定用）
        self.piece_no = 0
        self.spawn()

    # ---- 方塊 ----
    def _draw(self) -> str:
        if not self.bag:
            self.bag = KINDS[:]
            self.rng.shuffle(self.bag)
        return self.bag.pop()

    def spawn(self, kind: str | None = None):
        self.piece_no += 1
        self.kind = kind or self._next()
        self.rot = 0
        self.x = (COLS - _BASE[self.kind][0]) // 2
        self.y = -1 if self.kind == "I" else 0
        self.fall_acc = 0.0
        self.lock_timer = 0.0
        self.lock_resets = 0
        if not self.valid(self.kind, self.rot, self.x, self.y):
            self.alive = False

    def _next(self) -> str:
        kind = self.queue.pop(0)
        self.queue.append(self._draw())
        return kind

    def valid(self, kind, rot, x, y) -> bool:
        for cx, cy in piece_cells(kind, rot, x, y):
            if cx < 0 or cx >= COLS or cy >= ROWS:
                return False
            if cy >= 0 and self.grid[cy][cx] is not None:
                return False
        return True

    def cells(self):
        return piece_cells(self.kind, self.rot, self.x, self.y)

    def on_ground(self) -> bool:
        return not self.valid(self.kind, self.rot, self.x, self.y + 1)

    def ghost_y(self) -> int:
        y = self.y
        while self.valid(self.kind, self.rot, self.x, y + 1):
            y += 1
        return y

    def gravity(self) -> float:
        return max(0.06, 0.9 * 0.85 ** (self.lines // 10))

    # ---- 操作（回傳是否成功）----
    def _moved(self):
        if self.on_ground():
            if self.lock_resets < MAX_LOCK_RESETS:
                self.lock_timer = 0.0
                self.lock_resets += 1
        else:
            self.lock_timer = 0.0

    def move(self, dx: int) -> bool:
        if not self.alive or not self.valid(self.kind, self.rot, self.x + dx, self.y):
            return False
        self.x += dx
        self.last_rotate = False
        self.sfx.append("move")
        self._moved()
        return True

    def rotate(self, d: int = 1) -> bool:
        if not self.alive or self.kind == "O":
            return False
        rot = (self.rot + d) % 4
        for kx, ky in KICKS:
            if self.valid(self.kind, rot, self.x + kx, self.y + ky):
                self.rot, self.x, self.y = rot, self.x + kx, self.y + ky
                self.last_rotate = True
                self.sfx.append("rotate")
                self._moved()
                return True
        return False

    def hold(self) -> bool:
        if not self.alive or not self.can_hold:
            return False
        old, self.hold_kind = self.hold_kind, self.kind
        self.spawn(old)
        self.can_hold = False
        self.sfx.append("hold")
        return True

    def hard_drop(self):
        if not self.alive:
            return
        if self.ghost_y() != self.y:
            self.last_rotate = False
        self.y = self.ghost_y()
        self.sfx.append("drop")
        self.lock()

    # ---- 時間 ----
    def update(self, dt: float):
        self.event_age += dt
        self.glow += dt
        if not self.alive:
            return
        if self.on_ground():
            self.lock_timer += dt
            if self.lock_timer >= LOCK_DELAY:
                self.lock()
            return
        interval = min(self.gravity(), SOFT_INTERVAL) if self.soft else self.gravity()
        self.fall_acc += dt
        while self.fall_acc >= interval and not self.on_ground():
            self.fall_acc -= interval
            self.y += 1
            self.last_rotate = False
        if self.on_ground():
            self.fall_acc = 0.0

    # ---- 落地、消行、攻擊 ----
    def lock(self):
        color = self.kind
        tspin = self._is_tspin()  # 要在方塊寫進格子前判定
        for cx, cy in self.cells():
            if cy < 0:
                self.alive = False
                return
            self.grid[cy][cx] = color
        cleared = self._clear_lines()
        if not cleared:
            self.sfx.append("tspin" if tspin else "lock")
        if tspin and not cleared:
            self._event("T 轉！")
        if cleared:
            self.combo += 1
            attack = (TSPIN_ATTACK[cleared] if tspin else ATTACK[cleared]) + COMBO_BONUS[min(self.combo, len(COMBO_BONUS) - 1)]
            label = {1: "單行", 2: "雙行", 3: "三行", 4: "四行消除！"}[cleared]
            if tspin:
                label = f"T 轉{label}"
            if cleared == 4 or tspin:
                if self.b2b:
                    attack += 1
                    label = "連續 " + label
                self.b2b = True
            else:
                self.b2b = False
            if all(c is None for row in self.grid for c in row):
                attack += PERFECT_CLEAR
                label = "全清！"
                self.glow = 0.0
            if self.combo >= 1:
                label += f" 連擊 x{self.combo}"
            self._event(label)
            self.sfx.append("perfect" if self.glow == 0.0 else "tspin" if tspin else f"clear{cleared}")
            while attack and self.pending:  # 先抵銷自己身上的垃圾
                take = min(attack, self.pending[0])
                attack -= take
                self.pending[0] -= take
                if self.pending[0] == 0:
                    self.pending.pop(0)
            self.outbox += attack
            self.sent += attack
        else:
            self.combo = -1
            self._apply_garbage()
        self.can_hold = True
        if self.alive:
            self.spawn()

    def _is_tspin(self) -> bool:
        """T 方塊以旋轉落地，且中心四個斜角至少三個被牆或方塊佔住。"""
        if self.kind != "T" or not self.last_rotate:
            return False
        cx, cy = self.x + 1, self.y + 1
        filled = 0
        for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            x, y = cx + dx, cy + dy
            if x < 0 or x >= COLS or y >= ROWS or (y >= 0 and self.grid[y][x] is not None):
                filled += 1
        return filled >= 3

    def _event(self, text):
        self.last_event, self.event_age = text, 0.0

    def _clear_lines(self) -> int:
        kept = [row for row in self.grid if any(c is None for c in row)]
        n = ROWS - len(kept)
        if n:
            self.grid = [[None] * COLS for _ in range(n)] + kept
            self.lines += n
        return n

    def receive(self, lines: int):
        if lines > 0:
            self.pending.append(lines)
            self.sfx.append("warn")

    def _apply_garbage(self):
        budget = MAX_GARBAGE_PER_LOCK
        while self.pending and budget:
            n = min(self.pending[0], budget)
            budget -= n
            self.pending[0] -= n
            if self.pending[0] == 0:
                self.pending.pop(0)
            hole = self.rng.randrange(COLS)
            for _ in range(n):
                if any(c is not None for c in self.grid[0]):
                    self.alive = False  # 被頂出畫面
                row = [GARBAGE] * COLS
                row[hole] = None
                self.grid = self.grid[1:] + [row]

    def take_outbox(self) -> int:
        n, self.outbox = self.outbox, 0
        return n


class Match:
    """兩個玩家的對戰：一邊送出的垃圾行會變成另一邊的 pending。"""

    def __init__(self, seed: int | None = None):
        seed = random.randrange(1 << 30) if seed is None else seed
        # 兩邊用同樣的方塊順序，比較公平
        self.players = [Player(random.Random(seed)), Player(random.Random(seed))]
        self.winner: int | None = None  # 0 / 1，平手為 -1
        self.over = False

    def update(self, dt: float):
        if self.over:
            return
        a, b = self.players
        a.update(dt)
        b.update(dt)
        self.transfer()

    def transfer(self):
        a, b = self.players
        out_a, out_b = a.take_outbox(), b.take_outbox()
        b.receive(out_a)
        a.receive(out_b)
        if not a.alive or not b.alive:
            self.over = True
            self.winner = -1 if not a.alive and not b.alive else (1 if not a.alive else 0)

    def hard_drop(self, i: int):
        self.players[i].hard_drop()
        self.transfer()
