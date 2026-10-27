// taco 歌單搬到 https://sdfvgv1994-bot.github.io/taco-music/ ：舊的 service worker 收掉自己
// 只刪舊網址（/taco-game/player/）底下存的檔案。新歌單的存放區也叫 taco-playlist 開頭，
// 整個刪掉的話會連新歌單的離線檔案一起不見。
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => {
  const scope = self.registration.scope;   // 例如 https://…/taco-game/player/
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k.startsWith("taco-playlist")).map((k) =>
    caches.open(k).then((c) => c.keys().then((reqs) => Promise.all(reqs.filter((r) => r.url.startsWith(scope)).map((r) => c.delete(r))))))))
    .catch(() => {})
    .then(() => self.registration.unregister()));
});
