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
