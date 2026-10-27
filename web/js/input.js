/* taco 方塊對戰：鍵盤與觸控：用實體按鍵位置（e.code），注音輸入法開著也能玩。
   所有檔案依 index.html 的順序載入，共用同一個全域範圍。 */
"use strict";
/* ================= 鍵盤：用實體按鍵位置（e.code），注音輸入法開著也能玩 ================= */
const digitOf=c=>{const m=/^(?:Digit|Numpad)(\d)$/.exec(c);return m?+m[1]:null};
window.addEventListener("keydown",e=>{audio.init();const c=e.code,d=digitOf(c);
  if(state==="keys"&&waitKey){e.preventDefault();bindKey(c);return}
  if(["Space","ArrowUp","ArrowDown","ArrowLeft","ArrowRight","Backspace","Slash","Tab"].includes(c))e.preventDefault();
  if(c==="KeyM"){audio.muted=!audio.muted;muteBtn();return}
  if(state==="menu"){if(d===0)showSettings();else if(d===7)showOnline();else if(d&&MODES.some(x=>x.key===d))handle("mode"+d);return}
  if(state==="online"||state==="room"){if((c==="Escape"||c==="Backspace")&&!(e.target&&e.target.tagName==="INPUT")){netLeave();showMenu()}else if(state==="room"&&NET.host&&d>=1&&d<=4&&NET.opp)netHostStart(d);return}
  if(state==="diff"){if(c==="Escape"||c==="Backspace")showMenu();else if(d>=1&&d<=4)handle("diff"+d);return}
  if(state==="settings"){if(c==="Escape"||c==="Backspace")showMenu();else if(d>=1&&d<=ITEMS.length)handle("set"+ITEMS[d-1][0]);else if(d===ITEMS.length+1)showKeys();return}
  if(state==="keys"){if(c==="Escape"||c==="Backspace")showSettings();return}
  if(state!=="play")return;
  if(match.over){if(c==="Enter"||c==="NumpadEnter")e.preventDefault();   // 不讓瀏覽器把 Enter 當成「點一下結算面板上有焦點的按鈕」
    if(settle>0||e.repeat||performance.now()<panelGuard)return;   // 結束倒數中、按住不放、結算剛出來 0.8 秒內：都不會重開
    if(["Space","Enter","NumpadEnter","KeyR"].includes(c)){if(match.net){if(NET.host)netHostStart(NET.modeKey)}else start(cfg,diff)}else if(c==="Escape"||c==="Backspace"){if(match.net)netLeave();showMenu()}return}
  if(c==="Escape"||c==="KeyP"){setPause(!paused);return}
  if(paused&&match.net){if(c==="Backspace"){netLeave();showMenu()}return}   // 線上暫停中：只能繼續（Esc / P）或離開房間
  if(paused){if(c==="KeyR")start(cfg,diff);else if(c==="Backspace"){paused=false;showMenu()}return}
  if(countdown>0||e.repeat)return;
  for(const [i,a] of controllers(c)){if(ais[i])continue;e.preventDefault();act(i,a)}});
window.addEventListener("keyup",e=>{if(state!=="play"||!match)return;for(const [i,a] of controllers(e.code))release(i,a)});
window.addEventListener("blur",()=>{if(state==="play"&&match&&!match.net&&!match.over&&!paused)setPause(true)});

document.querySelectorAll("#touch button").forEach(b=>{const a=b.dataset.a;
  const down=e=>{e.preventDefault();audio.init();if(state!=="play"||paused||match.over||countdown>0)return;act(0,a);b.setPointerCapture?.(e.pointerId)};
  const up=e=>{e.preventDefault();if(state==="play"&&match)release(0,a)};
  b.addEventListener("pointerdown",down);b.addEventListener("pointerup",up);b.addEventListener("pointercancel",up)});
document.getElementById("btn-pause").addEventListener("click",()=>{if(state==="play"&&!match.over)setPause(!paused)});
document.getElementById("btn-menu").addEventListener("click",()=>{audio.init();waitKey=null;
  if(state==="play"&&match&&match.net){if(paused||match.over||!netSetPause(true)){netLeave();showMenu()}}   // 線上：先兩邊一起暫停，暫停畫面有「離開房間」
  else if(state==="play"&&match&&!match.over&&!paused)setPause(true);   // 玩到一半先暫停，暫停畫面裡有「回主選單」
  else if(state!=="menu"){if(state==="online"||state==="room")netLeave();paused=false;showMenu()}});
const mb=document.getElementById("btn-mute");function muteBtn(){mb.textContent=audio.muted?"取消靜音 M":"靜音 M"}
mb.addEventListener("click",()=>{audio.init();audio.muted=!audio.muted;muteBtn()});

