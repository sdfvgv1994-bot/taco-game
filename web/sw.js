// taco 方塊對戰 App 的 service worker：有網路就拿最新的，沒網路時用上一次存下來的檔案
// （單機、對電腦都能玩；線上對戰本來就要網路）。
// - 只處理這個網站自己的檔案；PeerJS、字型等外部網址直接連線，不經過這裡
// - 音樂檔（mp3，約 12MB）不存，邊播邊下載；沒網路時改用程式合成的音樂風格
// - 存的時候不看 ?v= 版本號，每個檔案只留最新的一份
const PREFIX = "taco-blocks";
const CACHE = PREFIX + "-v3";   // v3：換新的存放區，把舊版可能存錯的首頁清掉
// 安裝時先存好：畫面、樣式和全部程式檔都要在，升級後第一次沒網路打開才玩得動
const CORE = ["./", "./manifest.json", "./style.css", "./app/icon-192.png",
  "./js/engine.js", "./js/ai.js", "./js/settings.js", "./js/audio.js", "./js/draw.js", "./js/state.js",
  "./js/panels.js", "./js/input.js", "./js/net.js", "./js/main.js", "./js/pwa.js"];
const abs = (u) => new URL(u, self.registration.scope).href;

// 新版的存放區把 CORE 全部存齊了，才清掉自己舊版的存放區（taco-blocks 開頭的）。
// 同一個網域底下還有歌單、試算表、星際戰機，手機上的存放區是大家共用的，不能刪到別人的。
// 存不齊（例如更新那一刻剛好斷網）就先留著舊的，之後首頁存成功時會再檢查一次。
function cleanOldWhenReady() {
  return caches.open(CACHE)
    .then((c) => Promise.all(CORE.map((u) => c.match(abs(u)))))
    .then((hits) => hits.every(Boolean) && caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k.startsWith(PREFIX) && k !== CACHE).map((k) => caches.delete(k)))));
}

self.addEventListener("install", (e) => {
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then((c) => Promise.allSettled(CORE.map((u) => c.add(u)))));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(cleanOldWhenReady().catch(() => {}).then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.endsWith(".mp3") || req.headers.has("range")) return;
  if (url.pathname.startsWith(new URL("./player/", self.registration.scope).pathname)) return;   // taco 歌單有自己的 service worker
  const nav = req.mode === "navigate";
  // 只有「打開首頁」才存到首頁的位置；直接開 manifest.json、圖示這類網址時，各自存在自己的位置，
  // 不然會把首頁蓋掉，沒網路打開 App 就變成一堆設定檔文字
  const root = new URL("./", self.registration.scope);   // App 的根目錄，例如 /taco-game/
  const home = nav && (url.pathname === root.pathname || url.pathname === root.pathname + "index.html");
  const key = home ? root.href : url.origin + url.pathname;
  // 網頁本身和 version.json 每次都跟伺服器確認（不用瀏覽器存了 10 分鐘的舊版），按「更新」才真的拿到新版
  const fresh = nav || url.pathname.endsWith("version.json");
  e.respondWith(fetch(fresh ? new Request(req.url, { cache: "no-cache", credentials: "same-origin" }) : req).then((res) => {
    const html = (res.headers.get("content-type") || "").includes("text/html");
    if (res.ok && res.status === 200 && (!home || html)) {
      const copy = res.clone();
      caches.open(CACHE).then((c) => c.put(key, copy)).then(() => home && cleanOldWhenReady()).catch(() => {});
    }
    return res;
  // 沒網路：先找自己這一版的存放區，找不到才看舊版的
  }).catch(() => caches.open(CACHE).then((c) => c.match(key)).then((hit) => hit || caches.match(key))
    .then((hit) => hit || Promise.reject(new Error("offline")))));
});
