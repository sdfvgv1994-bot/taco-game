"""電腦對手：列舉所有落點，用簡單的評分挑最好的，再一步一步操作過去。"""
from __future__ import annotations

from engine import COLS, ROWS, piece_cells

DIFFICULTY = {  # 名稱: 每次動作的間隔（秒）
    "簡單": 0.40,
    "普通": 0.18,
    "困難": 0.07,
}


def _evaluate(grid, cells) -> float:
    board = [row[:] for row in grid]
    for x, y in cells:
        if y >= 0:
            board[y][x] = "X"
    full = [i for i, row in enumerate(board) if all(c is not None for c in row)]
    lines = len(full)
    board = [row for i, row in enumerate(board) if i not in full]
    board = [[None] * COLS for _ in range(lines)] + board

    heights, holes = [], 0
    for x in range(COLS):
        top = next((y for y in range(ROWS) if board[y][x] is not None), ROWS)
        heights.append(ROWS - top)
        holes += sum(1 for y in range(top, ROWS) if board[y][x] is None)
    bump = sum(abs(heights[i] - heights[i + 1]) for i in range(COLS - 1))
    return (-0.51 * sum(heights) + 0.76 * lines * lines - 0.36 * holes * 2 - 0.18 * bump
            - 0.3 * max(heights))


def best_placement(player) -> tuple[int, int]:
    """回傳 (旋轉次數, 目標 x)。"""
    best, best_score = (0, player.x), float("-inf")
    for rot in range(4):
        for x in range(-2, COLS):
            if not player.valid(player.kind, rot, x, -2):
                continue
            y = -2
            while player.valid(player.kind, rot, x, y + 1):
                y += 1
            cells = piece_cells(player.kind, rot, x, y)
            if any(cy < 0 for _, cy in cells):
                continue
            score = _evaluate(player.grid, cells)
            if score > best_score:
                best, best_score = (rot, x), score
    return best


class AI:
    def __init__(self, interval: float):
        self.interval = interval
        self.timer = 0.0
        self.target: tuple[int, int] | None = None
        self.piece_no = -1

    def update(self, dt: float, player):
        if not player.alive:
            return
        self.timer += dt
        if self.timer < self.interval:
            return
        self.timer = 0.0
        if self.target is None or self.piece_no != player.piece_no:
            self.target, self.piece_no = best_placement(player), player.piece_no
        rot, x = self.target
        if player.rot != rot:
            ok = player.rotate(1)
        elif player.x != x:
            ok = player.move(1 if x > player.x else -1)
        else:
            ok = False
        if not ok:  # 到位了，或被擋住了：直接放下
            player.hard_drop()
