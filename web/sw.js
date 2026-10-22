// taco 方塊對戰 App 的 service worker：有網路就拿最新的，沒網路時用上一次存下來的檔案
// （單機、對電腦都能玩；線上對戰本來就要網路）。
// - 只處理這個網站自己的檔案；PeerJS、字型等外部網址直接連線，不經過這裡
// - 音樂檔（mp3，約 12MB）不存，邊播邊下載；沒網路時改用程式合成的音樂風格
// - 存的時候不看 ?v= 版本號，每個檔案只留最新的一份
const CACHE = "taco-blocks-v2";
const CORE = ["./", "./manifest.json", "./app/icon-192.png"];

self.addEventListener("install", (e) => {
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then((c) => Promise.allSettled(CORE.map((u) => c.add(u)))));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.endsWith(".mp3") || req.headers.has("range")) return;
  if (url.pathname.startsWith(new URL("./player/", self.registration.scope).pathname)) return;   // taco 歌單有自己的 service worker
  const nav = req.mode === "navigate";
  const key = nav ? new URL("./", self.registration.scope).href : url.origin + url.pathname;
  // 網頁本身和 version.json 每次都跟伺服器確認（不用瀏覽器存了 10 分鐘的舊版），按「更新」才真的拿到新版
  const fresh = nav || url.pathname.endsWith("version.json");
  e.respondWith(fetch(fresh ? new Request(req.url, { cache: "no-cache", credentials: "same-origin" }) : req).then((res) => {
    if (res.ok && res.status === 200) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(key, copy)); }
    return res;
  }).catch(() => caches.match(key).then((hit) => hit || Promise.reject(new Error("offline")))));
});
