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


def test_player_app_files():
    """taco 歌單（web/player/）：可以裝到桌面，有自己的 service worker，遊戲的 service worker 不管它。"""
    import json
    player = WEB / "player"
    m = json.loads((player / "manifest.json").read_text(encoding="utf-8"))
    assert m["scope"] == "./" and m["start_url"] == "./" and m["display"] == "standalone"
    for i in m["icons"]:
        assert (player / i["src"]).is_file(), i["src"]
    html = (player / "index.html").read_text(encoding="utf-8")
    assert re.findall(r'<script src="([^"]+)"', html) == ["core.js", "app.js"]
    assert '<meta name="app-version" content="dev">' in html
    assert (player / "sw.js").is_file() and "./player/" in (WEB / "sw.js").read_text(encoding="utf-8")
    flow = (WEB.parent / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
    assert "web/player/index.html" in flow


def test_player_core():
    """解析 YouTube 連結、歌單順序、備份碼（用 node 跑 core.js）。"""
    import json
    import shutil
    import subprocess
    if not shutil.which("node"):
        return
    js = """
    const c=require(process.argv[1]);const out={};
    const P=(t)=>c.parseYouTube(t);
    out.parse=[P("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30"),P("https://youtu.be/dQw4w9WgXcQ?si=abc"),P("m.youtube.com/shorts/dQw4w9WgXcQ"),
      P("https://music.youtube.com/watch?v=dQw4w9WgXcQ&list=PLx0sYbCqOb8TBPRdmBHs5Iftvv9TPboYG"),P("https://www.youtube.com/playlist?list=PLx0sYbCqOb8TBPRdmBHs5Iftvv9TPboYG"),
      P("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=RDdQw4w9WgXcQ"),P("https://evil.com/watch?v=dQw4w9WgXcQ"),P("https://youtube.com.evil.com/watch?v=dQw4w9WgXcQ"),P("hello"),P("dQw4w9WgXcQ")];
    out.all=c.parseAll("聽這首 https://youtu.be/dQw4w9WgXcQ，還有\\nhttps://www.youtube.com/watch?v=9bZkp7q19f0)\\nprogramming\\nkJQP7kiw5Fk").map(r=>r.video);
    const st=c.newState();out.added=[c.addSongs(st,["aaaaaaaaaaa","bbbbbbbbbbb","ccccccccccc","aaaaaaaaaaa","bad"])];
    st.cur=0;out.next=[c.nextIndex(st,1),c.nextIndex(st,-1)];st.cur=2;out.wrap=c.nextIndex(st,1,true);
    st.repeat="off";out.off=c.nextIndex(st,1,true);out.offManual=c.nextIndex(st,1,false);
    st.repeat="one";out.one=c.nextIndex(st,1,true);out.oneManual=c.nextIndex(st,1,false);
    st.repeat="all";st.cur=0;st.songs[1].bad=true;out.skipBad=c.nextIndex(st,1,true);delete st.songs[1].bad;
    let seed=7;const rand=()=>((seed=seed*16807%2147483647)/2147483647);
    st.shuffle=true;st.cur=1;st.order=c.shuffled(3,1,rand);const seen=new Set([1]);let i=1;
    for(let k=0;k<2;k++){st.cur=c.nextIndex(st,1,true);seen.add(st.cur)}out.shuffleAll=seen.size;out.shuffleFirst=st.order[0];
    c.moveSong(st,0,1);out.moved=st.songs.map(s=>s.id[0]).join("");c.removeSong(st,0);out.removed=st.songs.map(s=>s.id[0]).join("");
    st.songs[0].title="歌名";out.back=c.importCode(c.exportCode(st));out.importLinks=c.importCode("https://youtu.be/dQw4w9WgXcQ").map(s=>s.id);
    out.importJunk=c.importCode('{"app":"taco-playlist","songs":[["<script>",1],["dQw4w9WgXcQ"]]}').map(s=>s.id);
    console.log(JSON.stringify(out));"""
    out = json.loads(subprocess.run(["node", "-e", js, str(WEB / "player" / "core.js")], capture_output=True, text=True, check=True).stdout)
    v = {"video": "dQw4w9WgXcQ"}
    assert out["parse"] == [v, v, v, {"video": "dQw4w9WgXcQ", "list": "PLx0sYbCqOb8TBPRdmBHs5Iftvv9TPboYG"},
                            {"list": "PLx0sYbCqOb8TBPRdmBHs5Iftvv9TPboYG"}, v, None, None, None, v]
    assert out["all"] == ["dQw4w9WgXcQ", "9bZkp7q19f0", "kJQP7kiw5Fk"]
    assert out["added"] == [3]
    assert out["next"] == [1, 2] and out["wrap"] == 0
    assert out["off"] == -1 and out["offManual"] == 0
    assert out["one"] == 2 and out["oneManual"] == 0
    assert out["skipBad"] == 2
    assert out["shuffleAll"] == 3 and out["shuffleFirst"] == 1
    assert out["moved"] == "bac" and out["removed"] == "ac"
    assert out["back"] == [{"id": "aaaaaaaaaaa", "title": "歌名"}, {"id": "ccccccccccc", "title": ""}]
    assert out["importLinks"] == ["dQw4w9WgXcQ"] and out["importJunk"] == ["dQw4w9WgXcQ"]
