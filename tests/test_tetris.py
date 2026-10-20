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


def test_engine_emits_sound_events():
    p = new_player("O")
    p.move(-1)
    p.rotate(1)
    p.hard_drop()
    assert p.sfx[:1] == ["move"] and "drop" in p.sfx and "lock" in p.sfx
    p.sfx.clear()
    p.receive(2)
    assert p.sfx == ["warn"]


def test_clear_and_perfect_events():
    p = new_player("I")
    stack_with_gap(p, 4)
    drop_vertical_i_at_right(p)
    assert "clear4" in p.sfx
    q = new_player("I")
    q.grid[ROWS - 1] = ["G"] * COLS
    for x in range(3, 7):
        q.grid[ROWS - 1][x] = None
    q.x, q.rot, q.y = 3, 0, 0
    q.hard_drop()
    assert "perfect" in q.sfx


def test_synthesised_sounds_are_valid_and_audio_can_be_disabled():
    import sound
    for name, samples in sound.build_sfx().items():
        assert samples and max(abs(s) for s in samples) <= 1.5, name
    assert len(sound.to_bytes(samples)) == 2 * len(samples)
    assert sound.freq("A4") == 440.0 and sound.freq("A5") == 880.0
    a = sound.Audio(enabled=False)
    a.play("move")
    a.start_music()
    a.stop_music()
    assert not a.ok and a.toggle_mute() is True


# ---- 多人 / 模式 ----
def test_battle_ko_revives_and_credits_attacker():
    m = Match(1, n=3, mode="battle", time_limit=120)
    a, b, c = m.players
    b.receive(2, src=0)
    b.alive = False
    m.transfer()
    assert a.ko == 1 and b.deaths == 1 and b.alive and b.pending == []
    assert all(c is None for row in b.grid for c in row)


def test_battle_without_attacker_gives_no_ko():
    m = Match(1, n=2, mode="battle", time_limit=120)
    m.players[0].alive = False
    m.transfer()
    assert m.players[1].ko == 0 and m.players[0].alive


def test_battle_timeout_ranks_by_ko_then_sent_then_height():
    m = Match(1, n=3, mode="battle", time_limit=10)
    m.players[0].ko, m.players[1].ko, m.players[2].ko = 1, 1, 0
    m.players[0].sent, m.players[1].sent = 3, 5
    m.update(10.0)
    assert m.over and m.ranks == [1, 0, 2] and m.winner == 1


def test_battle_exact_tie_is_a_draw():
    m = Match(1, n=2, mode="battle", time_limit=1)
    m.update(1.0)
    assert m.over and m.winner == -1


def test_ko_limit_ends_match_early():
    m = Match(1, n=2, mode="battle", time_limit=120, ko_limit=2)
    m.players[0].ko = 2
    m.transfer()
    assert m.over and m.winner == 0


def test_garbage_goes_to_chosen_target():
    m = Match(1, n=4, mode="battle", time_limit=120)
    m.set_target(0, 3)
    m.players[0].outbox = 4
    m.transfer()
    assert m.players[3].pending == [4] and m.players[3].last_attacker == 0
    assert m.players[1].pending == [] and m.players[2].pending == []


def test_cycle_target_skips_self():
    m = Match(1, n=3, mode="battle")
    seen = set()
    for _ in range(6):
        m.cycle_target(1)
        seen.add(m.players[1].target)
    assert seen == {0, 2}


def test_sprint_finishes_at_forty_lines():
    m = Match(1, n=1, mode="sprint")
    p = m.players[0]
    p.lines = 40
    m.elapsed = 55.5
    m.transfer()
    assert m.over and m.success and m.finish[0] == 55.5 and p.done
    assert not p.move(1)  # 完成後不能再操作


def test_sprint_race_ranks_by_finish_time():
    m = Match(1, n=3, mode="sprint")
    m.elapsed = 30
    m.players[2].lines = 40
    m.transfer()
    assert not m.over
    m.elapsed = 45
    m.players[1].lines = 40
    m.transfer()
    m.players[0].alive = False
    m.transfer()
    assert m.over and m.ranks[:2] == [2, 1] and m.winner == 2


def test_marathon_levels_and_goal():
    m = Match(1, n=1, mode="marathon")
    p = m.players[0]
    assert p.level == 1 and m.goal_lines == 150
    p.lines = 25
    assert p.level == 3 and p.gravity() < Player(random.Random(1)).gravity()
    p.lines = 150
    m.transfer()
    assert m.over and m.success


def test_marathon_game_over_when_dead():
    m = Match(1, n=1, mode="marathon")
    m.players[0].alive = False
    m.transfer()
    assert m.over and m.success is False


def test_ai_targets_alive_opponents_only():
    m = Match(1, n=4, mode="battle")
    m.players[2].alive = False
    ai = AI(0.1)
    for _ in range(40):
        ai.retarget_timer = 0
        ai.choose_target(0.1, m, 1)
        assert m.players[1].target in (0, 3)


def test_six_player_battle_with_ais_runs():
    m = Match(2, n=6, mode="battle", time_limit=30, ko_limit=10)
    ais = {i: AI(0.0) for i in range(6)}
    for _ in range(700):
        for i, a in ais.items():
            a.update(0.05, m.players[i])
            a.choose_target(0.05, m, i)
        m.update(0.05)
        if m.over:
            break
    assert m.over and sorted(m.ranks) == list(range(6))


# ---- 選單按鍵、設定（tetris.py 需要 pygame） ----
def _tetris_ui():
    import os
    import pytest
    pytest.importorskip("pygame")
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import tetris as ui
    return ui


def test_number_row_and_keypad_both_select():
    ui = _tetris_ui()
    import pygame
    for i in range(10):
        assert ui.digit(getattr(pygame, f"K_{i}")) == i
        assert ui.digit(getattr(pygame, f"K_KP{i}")) == i
    assert ui.digit(pygame.K_a) is None


def test_settings_toggle_and_save(tmp_path):
    ui = _tetris_ui()
    path = tmp_path / "settings.json"
    s = ui.Settings(path)
    assert s["ghost"] and s["speed"] == "中"
    s.toggle("ghost")
    s.toggle("speed")
    assert not s["ghost"] and s["speed"] == "快"
    s.toggle("speed")
    assert s["speed"] == "慢"
    again = ui.Settings(path)          # 重開遊戲還記得
    assert not again["ghost"] and again["speed"] == "慢"
    assert again.label("ghost") == "關" and again.label("speed") == "慢"


def test_settings_ignore_broken_file(tmp_path):
    ui = _tetris_ui()
    path = tmp_path / "settings.json"
    path.write_text('{"ghost": "yes", "speed": "超快", "other": 1}', encoding="utf-8")
    s = ui.Settings(path)
    assert s["ghost"] is True and s["speed"] == "中" and "other" not in s.data


def test_speed_presets():
    ui = _tetris_ui()
    ui.set_speed("快")
    assert (ui.DAS, ui.ARR) == ui.SPEEDS["快"]
    ui.set_speed("不存在")
    assert (ui.DAS, ui.ARR) == ui.SPEEDS["中"]


def test_hold_key_setting():
    ui = _tetris_ui()
    import pygame
    ui.set_hold("C / .")
    assert ui.P1_KEYS["hold"] == pygame.K_c and ui.P2_KEYS["hold"] == pygame.K_PERIOD
    ui.set_hold("Shift")
    assert ui.P1_KEYS["hold"] == pygame.K_LSHIFT and ui.P2_KEYS["hold"] == pygame.K_RSHIFT
    assert ui.hold_names("Shift") == ("左 Shift", "右 Shift")
    ui.set_hold("C / .")


def test_hold_defaults_to_c_not_shift(tmp_path):
    ui = _tetris_ui()
    s = ui.Settings(tmp_path / "settings.json")
    assert s["hold"] == "C / ."      # 預設不用 Shift，避免切到中英文
    s.toggle("hold")
    assert s["hold"] == "Shift"
