"""網頁版（web/）的基本檢查：放在 GitHub Pages 上，沒有 claude.ai 的頁面外框幫忙。"""
import re
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"


def test_hidden_panels_stay_hidden():
    """選單、暫停、結算面板用 hidden 藏起來；面板本身是 display:flex，沒有這條規則會蓋在遊戲上。"""
    css = (WEB / "style.css").read_text(encoding="utf-8")
    assert re.search(r"\[hidden\][^{]*\{\s*display\s*:\s*none\s*!important", css)


def test_page_loads_every_script_in_order():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert '<meta name="viewport"' in html and 'href="style.css"' in html
    scripts = re.findall(r'<script src="(js/[^"]+)"', html)
    assert scripts[0] == "js/engine.js" and scripts[-2:] == ["js/main.js", "js/pwa.js"]
    for s in scripts:
        assert (WEB / s).is_file(), s
    assert sorted(p.name for p in (WEB / "js").glob("*.js")) == sorted(Path(s).name for s in scripts)


def test_installable_app_files():
    """手機桌面 App：manifest 的圖示都在，service worker 在網站最上層（才管得到整個網站）。"""
    import json
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert 'rel="manifest" href="manifest.json"' in html and 'rel="apple-touch-icon"' in html
    m = json.loads((WEB / "manifest.json").read_text(encoding="utf-8"))
    assert m["display"] == "standalone" and m["start_url"] == "./"
    sizes = {i["sizes"] for i in m["icons"]}
    assert {"192x192", "512x512"} <= sizes and any(i.get("purpose") == "maskable" for i in m["icons"])
    for i in m["icons"]:
        assert (WEB / i["src"]).is_file(), i["src"]
    assert (WEB / "sw.js").is_file() and (WEB / "app" / "apple-touch-icon.png").is_file()


def test_version_is_filled_in_on_deploy():
    """更新提示靠 app-version：repo 裡是 dev，部署時換成提交代號並寫出 version.json。"""
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert '<meta name="app-version" content="dev">' in html and '<meta name="app-built" content="">' in html
    flow = (WEB.parent / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
    assert "app-version" in flow and "version.json" in flow and "app-built" in flow


def test_web_combo_matches_python():
    """網頁版和 Python 版的連擊攻擊要一樣（線上對戰兩邊各自算）。"""
    import shutil
    import subprocess
    import sys
    if not shutil.which("node"):
        return
    sys.path.insert(0, str(WEB.parent / "tetris"))
    from engine import BURST_ATTACK, COMBO_BONUS, COMBO_BURST
    js = (WEB / "js" / "engine.js").read_text(encoding="utf-8") + """
    const out=[];for(let k=0;k<=15;k++){const p=new Player(rng(1));p.spawn("I");const xs=new Set(p.cells().map(c=>c[0]));
      p.grid[ROWS-1]=Array.from({length:COLS},(_,x)=>xs.has(x)?null:"G");p.grid[ROWS-2][0]="G";p.combo=k-1;p.hardDrop();out.push([p.sent,p.event,p.sfx.includes("burst")])}
    console.log(JSON.stringify(out));"""
    import json
    res = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    for k, (sent, label, burst) in enumerate(res):
        want = COMBO_BONUS[min(k, len(COMBO_BONUS) - 1)] + (BURST_ATTACK if k and k % COMBO_BURST == 0 else 0)
        assert sent == want, (k, sent, want)
        assert burst == (k > 0 and k % COMBO_BURST == 0) and (("爆發" in label) == burst)



def test_player_moved():
    """taco 歌單搬到自己的網站（taco-music）：舊網址只留轉址，遊戲的 service worker 不管 /player/。"""
    html = (WEB / "player" / "index.html").read_text(encoding="utf-8")
    assert "https://sdfvgv1994-bot.github.io/taco-music/" in html
    assert "unregister" in (WEB / "player" / "sw.js").read_text(encoding="utf-8")
    assert "./player/" in (WEB / "sw.js").read_text(encoding="utf-8")


def test_end_countdown_before_result():
    """結算前倒數：限時模式最後 5 秒提醒；結束後倒數 3 秒才出結算，這段時間按鍵不會直接開下一局。"""
    import json
    import shutil
    import subprocess
    js_dir = WEB / "js"
    main = (js_dir / "main.js").read_text(encoding="utf-8")
    inp = (js_dir / "input.js").read_text(encoding="utf-8")
    state = (js_dir / "state.js").read_text(encoding="utf-8")
    assert "setTimeout(()=>{if(state===\"play\"&&match===m)showResult()" not in main   # 舊的 1 秒後直接結算
    assert "settle=SETTLE_SECS" in main and "showResult()" in main
    over = inp[inp.index("if(match.over){"):]
    assert over.index('e.preventDefault()') < over.index("start(cfg,diff)")            # Enter 不會被瀏覽器當成點結算面板的按鈕
    assert "if(settle>0||e.repeat||performance.now()<panelGuard)return;" in over       # 倒數中、按住不放、結算剛出來：都不重開
    assert "settle=0;lastWarn=0;" in state                                             # 開新局一定清掉
    net = (js_dir / "net.js").read_text(encoding="utf-8")
    assert "settle=0;lastWarn=0;" in net[net.index("function netBegin"):]              # 線上開新局也清掉
    assert "match.ending&&!match.over" in main                                          # 線上等對手結果時就先顯示 FINISH
    if not shutil.which("node"):
        return
    js = (js_dir / "engine.js").read_text(encoding="utf-8") + """
    console.log(JSON.stringify({w:[null,0,-1,0.01,1,4.2,5,5.01,60].map(warnSecond),warn:END_WARN,settle:SETTLE_SECS}));"""
    out = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    assert out["w"] == [0, 0, 0, 1, 1, 5, 5, 0, 0]
    assert out["warn"] == 5 and out["settle"] == 3


def test_offline_cache_is_safe():
    """離線快取：直接開 manifest.json 不會把首頁蓋掉；升級後第一次離線也玩得動；
    只清自己（taco-blocks）的舊存放區，不會刪到同網域歌單、試算表、星際戰機的離線檔案。"""
    import re
    sw = (WEB / "sw.js").read_text(encoding="utf-8")
    html = (WEB / "index.html").read_text(encoding="utf-8")
    # 只有打開首頁才存到首頁的位置（直接開 manifest.json 不會把首頁蓋掉）
    assert "const home = nav &&" in sw and 'includes("text/html")' in sw
    # 換新存放區；只清自己舊版的（同網域其他 App 的不能刪），而且要新版存齊了才清
    assert 'const PREFIX = "taco-blocks"' in sw and 'const CACHE = PREFIX + "-v3"' in sw
    assert "k.startsWith(PREFIX) && k !== CACHE" in sw and "hits.every(Boolean)" in sw
    # 沒網路時先找自己這一版的存放區
    assert "caches.open(CACHE).then((c) => c.match(key))" in sw
    # 網頁用到的每個程式檔、樣式檔都要預先存好，升級後第一次離線才打得開
    core = re.search(r"const CORE = \[(.*?)\];", sw, re.S).group(1)
    for f in re.findall(r'<script src="([^"]+)"', html) + re.findall(r'<link rel="stylesheet" href="([^"]+)"', html):
        if not f.startswith("http"):
            assert '"./' + f + '"' in core, f
    # 舊網址 /player/ 收掉自己時，只刪自己網址底下的檔案，不能整個刪掉新歌單的存放區
    player = (WEB / "player" / "sw.js").read_text(encoding="utf-8")
    assert "r.url.startsWith(scope)" in player and "caches.delete(k)" not in player
