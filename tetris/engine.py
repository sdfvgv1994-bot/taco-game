"""俄羅斯方塊對戰的遊戲邏輯（不含畫面，方便測試）。"""
from __future__ import annotations

import random

COLS, ROWS = 10, 20
LOCK_DELAY = 0.5
LINES_PER_LEVEL = 10
MAX_LEVEL = 15
MAX_LOCK_RESETS = 15
SOFT_INTERVAL = 0.03
MAX_GARBAGE_PER_LOCK = 8
ATTACK = {0: 0, 1: 0, 2: 1, 3: 2, 4: 4}  # 消幾行 -> 送出幾行垃圾
COMBO_BONUS = [0, 1, 1, 2, 2, 3, 3, 4, 4, 5]
COMBO_BURST = 5  # 連擊 x5、x10…：連擊爆發
BURST_ATTACK = 2
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
        self.ko = 0                   # 擊倒對手的次數（限時對戰用）
        self.deaths = 0
        self.last_attacker: int | None = None  # 最後一個送垃圾給我的人，被擊倒時算他的 KO
        self.target: int | None = None         # 我要攻擊誰（Match 裡的玩家編號）
        self.done = False             # 競速 / 馬拉松已完成，停止操作
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

    @property
    def active(self) -> bool:
        return self.alive and not self.done

    @property
    def level(self) -> int:
        return self.lines // LINES_PER_LEVEL + 1

    def gravity(self) -> float:
        return max(0.05, 0.9 * 0.82 ** (self.level - 1))

    def height(self) -> int:
        top = next((y for y in range(ROWS) if any(c is not None for c in self.grid[y])), ROWS)
        return ROWS - top

    def revive(self):
        """被擊倒後清空場地重新開始（限時對戰用）。"""
        self.grid = [[None] * COLS for _ in range(ROWS)]
        self.pending = []
        self.combo, self.b2b, self.can_hold = -1, False, True
        self.last_attacker = None
        self.alive = True
        self.spawn()

    # ---- 操作（回傳是否成功）----
    def _moved(self):
        if self.on_ground():
            if self.lock_resets < MAX_LOCK_RESETS:
                self.lock_timer = 0.0
                self.lock_resets += 1
        else:
            self.lock_timer = 0.0

    def move(self, dx: int) -> bool:
        if not self.active or not self.valid(self.kind, self.rot, self.x + dx, self.y):
            return False
        self.x += dx
        self.last_rotate = False
        self.sfx.append("move")
        self._moved()
        return True

    def rotate(self, d: int = 1) -> bool:
        if not self.active or self.kind == "O":
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
        if not self.active or not self.can_hold:
            return False
        old, self.hold_kind = self.hold_kind, self.kind
        self.spawn(old)
        self.can_hold = False
        self.sfx.append("hold")
        return True

    def hard_drop(self):
        if not self.active:
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
        if not self.active:
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
            burst = self.combo > 0 and self.combo % COMBO_BURST == 0
            if burst:
                attack += BURST_ATTACK
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
            if burst:
                label += " 爆發！"
                self.sfx.append("burst")
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

    def receive(self, lines: int, src: int | None = None):
        if lines > 0:
            self.pending.append(lines)
            self.last_attacker = src
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
    """多個玩家的比賽。mode：
    survival  先被頂到頂的人輸（兩人）
    battle    限時（或 KO 數）對戰，被頂到頂 = 對手 +1 KO，清空重來；依 KO > 送出行數 > 行高 排名
    sprint    先消完 SPRINT_LINES 行的人贏，不互相攻擊
    marathon  單人，消完 MAX_LEVEL 關（每關 LINES_PER_LEVEL 行）過關，頂到頂就結束
    """

    SPRINT_LINES = 40

    def __init__(self, seed: int | None = None, n: int = 2, mode: str = "survival",
                 time_limit: float | None = None, ko_limit: int | None = None):
        seed = random.randrange(1 << 30) if seed is None else seed
        # 大家用同樣的方塊順序，比較公平
        self.players = [Player(random.Random(seed)) for _ in range(n)]
        for i, p in enumerate(self.players):
            p.target = (i + 1) % n if n > 1 else None
        self.mode, self.time_limit, self.ko_limit = mode, time_limit, ko_limit
        self.elapsed = 0.0
        self.finish: list[float | None] = [None] * n  # 競速 / 馬拉松的完成時間
        self.winner: int | None = None  # 勝者編號，平手為 -1
        self.success: bool | None = None  # 單人模式有沒有完成
        self.ranks: list[int] = []
        self.over = False

    @property
    def goal_lines(self) -> int:
        return self.SPRINT_LINES if self.mode == "sprint" else MAX_LEVEL * LINES_PER_LEVEL

    @property
    def time_left(self) -> float | None:
        return None if not self.time_limit else max(0.0, self.time_limit - self.elapsed)

    def update(self, dt: float):
        if self.over:
            return
        self.elapsed += dt
        for p in self.players:
            p.update(dt)
        self.transfer()

    # ---- 目標 ----
    def target_of(self, i: int) -> int | None:
        t = self.players[i].target
        if t is not None and t != i and self.players[t].alive:
            return t
        others = [j for j, p in enumerate(self.players) if j != i and p.alive]
        return others[0] if others else None

    def set_target(self, i: int, j: int):
        if j != i and 0 <= j < len(self.players):
            self.players[i].target = j

    def cycle_target(self, i: int):
        n = len(self.players)
        t = self.players[i].target if self.players[i].target is not None else i
        self.players[i].target = (t + 1) % n if (t + 1) % n != i else (t + 2) % n

    # ---- 結算 ----
    def transfer(self):
        if self.over:
            return
        for i, p in enumerate(self.players):
            out = p.take_outbox()
            if out and self.mode in ("survival", "battle"):
                t = self.target_of(i)
                if t is not None:
                    self.players[t].receive(out, i)
        getattr(self, "_check_" + self.mode)()

    def hard_drop(self, i: int):
        self.players[i].hard_drop()
        self.transfer()

    def _check_survival(self):
        alive = [i for i, p in enumerate(self.players) if p.alive]
        if len(alive) < len(self.players):
            self.over = True
            self.winner = alive[0] if len(alive) == 1 else -1
            self.ranks = alive + [i for i in range(len(self.players)) if i not in alive]

    def _check_battle(self):
        for i, p in enumerate(self.players):
            if p.alive:
                continue
            p.deaths += 1
            killer = p.last_attacker
            if killer is not None and killer != i:
                a = self.players[killer]
                a.ko += 1
                a._event("KO！")
                a.sfx.append("ko")
            p._event("被擊倒")
            p.revive()
        timeout = self.time_limit is not None and self.elapsed >= self.time_limit
        ko_done = self.ko_limit is not None and max(p.ko for p in self.players) >= self.ko_limit
        if timeout or ko_done:
            self.over = True
            self.ranks = sorted(range(len(self.players)), key=self._rank_key, reverse=True)
            tie = len(self.ranks) > 1 and self._rank_key(self.ranks[0]) == self._rank_key(self.ranks[1])
            self.winner = -1 if tie else self.ranks[0]

    def _rank_key(self, i: int):
        p = self.players[i]
        return (p.ko, p.sent, -p.height())

    def _check_race(self):
        for i, p in enumerate(self.players):
            if self.finish[i] is None and p.alive and p.lines >= self.goal_lines:
                self.finish[i] = self.elapsed
                p.done = True
                p._event("完成！")
        solo = len(self.players) == 1
        running = [i for i, p in enumerate(self.players) if p.active]
        if solo:
            if not self.players[0].alive or self.finish[0] is not None:
                self.over, self.success = True, self.finish[0] is not None
                self.winner = 0 if self.success else None
        elif not self.players[0].alive or not running:
            self.over = True
            self.ranks = sorted(range(len(self.players)),
                                key=lambda i: (self.finish[i] is None, self.finish[i] or 0))
            if self.finish[self.ranks[0]] is not None:
                self.winner = self.ranks[0]

    _check_sprint = _check_race
    _check_marathon = _check_race
