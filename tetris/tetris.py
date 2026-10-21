"""俄羅斯方塊對戰（仿 Tetris Battle 的玩法）。

選單：1 Battle 2P 限時賽、2 Battle 6P、3 Sprint、4 Sprint 4P、5 Marathon、6 生死戰。
消行會把垃圾行送給對手：雙行 1、三行 2、四行 4，T 轉、連擊與連續四行有加成；全清會閃綠光；
自己落地前可以用消行抵銷對方送來的垃圾（左側紅條）。
限時對戰被頂到頂 = 對手 +1 KO，清空重來；多人對戰用 Tab 或滑鼠點小板子換攻擊目標。
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
from engine import COLS, MAX_LEVEL, Match  # noqa: E402
from sound import Audio  # noqa: E402
# 拆出來的積木；舊的名字（tetris.Settings、tetris.digit…）照樣能用
from controls import (  # noqa: E402,F401
    BACK_KEYS, DIGIT_KEYS, HOLD_KEYS, HOLD_NAME, P1_KEYS, P2_KEYS, SPEEDS, Controls, digit,
    hold_names, set_hold, set_speed,
)
from draw import (  # noqa: E402,F401
    BG, BOARD_H, BOARD_W, CELL, DIM, GAP, HEIGHT, PANEL_W, SMALL, TEXT, TOP, WIDTH, center_text, draw_menu,
    draw_player, draw_result, draw_small, fmt_time, hud_text, load_font, player_info,
)
from options import MODE_KEYS, MODE_LIST, Records, Settings  # noqa: E402,F401


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
