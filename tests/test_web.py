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
