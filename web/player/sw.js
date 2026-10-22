// taco 歌單搬到 https://sdfvgv1994-bot.github.io/taco-music/ ：舊的 service worker 收掉自己
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k.startsWith("taco-playlist")).map((k) => caches.delete(k))))
    .then(() => self.registration.unregister()));
});
