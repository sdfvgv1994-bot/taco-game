/* taco 方塊對戰：手機桌面 App（PWA）。註冊 service worker（離線也能玩），處理主選單的「安裝到桌面」。
   Android 的 Chrome、Edge 會給「安裝」事件；iPhone 的 Safari 沒有，改成說明「分享 → 加入主畫面」。 */
"use strict";
const PWA = (() => {
  let prompt = null;
  const standalone = () => matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  const ios = /iphone|ipad|ipod/i.test(navigator.userAgent);
  if ("serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "localhost"))
    addEventListener("load", () => navigator.serviceWorker.register("sw.js").catch(() => {}));
  const refresh = () => { if (state === "menu") showMenu(); };
  addEventListener("beforeinstallprompt", (e) => { e.preventDefault(); prompt = e; refresh(); });
  addEventListener("appinstalled", () => { prompt = null; refresh(); });
  // 有新版本：開著的時候每 10 分鐘、切回 App 時各查一次 version.json，不一樣就在主選單上方提示
  let latest = null;
  async function check() {
    if (APP_VERSION === "dev") return;            // 本機開的版本不檢查
    try {
      const r = await fetch("version.json?t=" + Date.now(), { cache: "no-store" });
      const j = r.ok ? await r.json() : null;
      if (j && j.v && j.v !== APP_VERSION && latest !== j.v) { latest = j.v; refresh(); }
    } catch (e) { /* 沒網路：下次再查 */ }
  }
  addEventListener("load", () => setTimeout(check, 3000));
  setInterval(check, 10 * 60 * 1000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) check(); });
  return {
    hasUpdate: () => latest !== null,
    canInstall: () => !standalone() && (prompt !== null || ios),
    async install() {
      if (prompt) {
        const p = prompt; prompt = null;
        p.prompt();
        try { await p.userChoice; } catch (e) { /* 使用者關掉視窗 */ }
        refresh();
        return;
      }
      showPanel(`<div class="card"><h2>安裝到桌面</h2>
        <p>iPhone / iPad：按 Safari 下方的「分享」按鈕 <b>⬆</b>，往下找「加入主畫面」，再按「新增」。</p>
        <p class="hint">裝好之後從桌面的方塊圖示打開，就是全螢幕、沒有網址列。</p>
        <div class="row-btns"><button type="button" data-act="menu">← 返回主選單</button></div></div>`);
    },
  };
})();
// 主選單比這個檔案早畫好：iPhone 不會有「安裝」事件，所以載入後可以安裝就重畫一次，按鈕才會出現
if (PWA.canInstall() && state === "menu") showMenu();
