import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tetris"))

from ai import AI, best_placement  # noqa: E402
from engine import COLS, ROWS, SHAPES, Match, Player  # noqa: E402


def new_player(kind="I"):
    p = Player(random.Random(1))
    p.spawn(kind)
    return p


def test_rotation_keeps_four_cells_inside_box():
    for kind, rots in SHAPES.items():
        assert len(rots) == 4 and all(len(set(r)) == 4 for r in rots), kind


def test_seven_bag_has_each_piece_once():
    p = Player(random.Random(2))
    kinds = [p.kind] + p.queue
    assert len(set(kinds[:5])) == 5


def test_move_stops_at_walls():
    p = new_player("O")
    while p.move(-1):
        pass
    assert min(x for x, _ in p.cells()) == 0
    assert not p.move(-1)


def test_hard_drop_lands_on_floor():
    p = new_player("O")
    p.hard_drop()
    assert p.grid[ROWS - 1][COLS // 2 - 1] == "O"


def stack_with_gap(p, rows):
    """底部 rows 行只留最右一格，另外在高處放一塊，避免觸發全清加成。"""
    for y in range(ROWS - rows, ROWS):
        p.grid[y] = ["G"] * (COLS - 1) + [None]
    p.grid[3][0] = "G"


def drop_vertical_i_at_right(p):
    p.rotate(1)
    while p.move(1):
        pass
    p.hard_drop()


def test_single_clear_sends_nothing():
    p = new_player("I")
    stack_with_gap(p, 1)
    drop_vertical_i_at_right(p)
    assert p.lines == 1 and p.outbox == 0


def test_tetris_sends_four():
    p = new_player("I")
    stack_with_gap(p, 4)
    drop_vertical_i_at_right(p)
    assert p.lines == 4 and p.outbox == 4


def test_attack_cancels_pending_garbage():
    p = new_player("I")
    p.receive(3)
    stack_with_gap(p, 4)
    drop_vertical_i_at_right(p)
    assert p.pending == [] and p.outbox == 1


def test_garbage_rises_after_a_lock_without_clear():
    p = new_player("O")
    p.receive(2)
    p.hard_drop()
    bottom = p.grid[ROWS - 1]
    assert bottom.count(None) == 1 and p.grid[ROWS - 2].count(None) == 1
    assert p.pending == []


def test_hold_swaps_once_per_piece():
    p = new_player("T")
    assert p.hold() and p.hold_kind == "T"
    assert not p.hold()
    p.hard_drop()
    assert p.hold()


def test_top_out_ends_game():
    p = Player(random.Random(3))
    for _ in range(40):
        p.hard_drop()
    assert not p.alive


def test_match_transfers_garbage_and_declares_winner():
    m = Match(5)
    a, b = m.players
    a.outbox = 3
    m.transfer()
    assert b.pending == [3]
    b.alive = False
    m.transfer()
    assert m.over and m.winner == 0


def test_ai_plays_a_full_match():
    m = Match(7)
    ais = [AI(0.0), AI(0.0)]
    for _ in range(5000):
        if m.over:
            break
        for ai, p in zip(ais, m.players):
            ai.update(0.05, p)
        m.update(0.05)
    assert sum(p.lines for p in m.players) > 20


def test_best_placement_clears_available_line():
    p = new_player("I")
    p.grid[ROWS - 1] = ["G"] * COLS
    for x in range(3, 7):
        p.grid[ROWS - 1][x] = None
    rot, x = best_placement(p)
    assert rot in (0, 2) and x == 3


def t_spin_setup():
    """T 朝下卡進凹槽，消兩行。"""
    p = new_player("T")
    p.grid[ROWS - 1] = ["G"] * COLS
    p.grid[ROWS - 1][4] = None
    p.grid[ROWS - 2] = ["G"] * COLS
    p.grid[ROWS - 2][3] = p.grid[ROWS - 2][4] = p.grid[ROWS - 2][5] = None
    p.grid[ROWS - 3][3] = p.grid[ROWS - 3][5] = "G"  # 上方有突出，四個斜角都被佔住
    p.grid[3][0] = "G"
    return p


def test_t_spin_double_sends_four():
    p = t_spin_setup()
    p.rot, p.x, p.y = 2, 3, ROWS - 3   # T 朝下，尖端對準缺口，從上方落到位
    assert p.valid("T", 2, 3, ROWS - 3)
    p.last_rotate = True
    p.hard_drop()
    assert p.lines == 2 and p.outbox == 4
    assert "T 轉" in p.last_event


def test_plain_drop_is_not_t_spin():
    p = t_spin_setup()
    p.rot, p.x, p.y = 2, 3, ROWS - 3
    p.last_rotate = False
    p.hard_drop()
    assert "T 轉" not in p.last_event


def test_perfect_clear_triggers_glow():
    p = new_player("I")
    p.grid[ROWS - 1] = ["G"] * COLS
    for x in range(3, 7):
        p.grid[ROWS - 1][x] = None
    p.x, p.rot, p.y = 3, 0, 0
    p.hard_drop()
    assert p.glow == 0.0 and p.outbox == 6 and "全清" in p.last_event
