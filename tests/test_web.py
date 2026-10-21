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
    assert scripts[0] == "js/engine.js" and scripts[-1] == "js/main.js"
    for s in scripts:
        assert (WEB / s).is_file(), s
    assert sorted(p.name for p in (WEB / "js").glob("*.js")) == sorted(Path(s).name for s in scripts)
