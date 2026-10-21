/* taco 方塊對戰：設定與按鍵（存在這個瀏覽器）。
   所有檔案依 index.html 的順序載入，共用同一個全域範圍。 */
"use strict";
/* ================= 設定與按鍵（存在這個瀏覽器） ================= */
const SPEEDS={"慢":[.22,.06],"中":[.16,.04],"快":[.10,.02]};
const DEFAULTS={sfx:true,music:true,style:"Cossack EDM",theme:"卡通",ghost:true,countdown:true,speed:"中"};
// 背景音樂：兩種程式合成的，加上老闆從 Pixabay 下載的四首（Pixabay 授權，可免費使用）
const TRACKS={"Cossack EDM":{file:"music/cossack-edm.mp3",by:"melodyayresgriffiths"},
  "Korobeiniki 弦樂版":{file:"music/korobeiniki-strings.mp3",by:"GregorQuendel"},
  "80s Unstoppable":{file:"music/80s-unstoppable.mp3",by:"DJ Maverik"},
  "Button Mash Velocity":{file:"music/button-mash-velocity.mp3",by:"Puriosity Studio"}};
const STYLES=["EDM","8-bit",...Object.keys(TRACKS),"隨機"],THEMES=["卡通","藍天","霓虹"];
const ITEMS=[["theme","畫面風格"],["sfx","音效"],["music","背景音樂"],["style","音樂風格"],["ghost","落點預覽"],["countdown","開局倒數 3 秒"],["speed","長按移動速度"]];
const ACTIONS=[["left","左移"],["right","右移"],["down","軟降"],["cw","順時針轉"],["ccw","逆時針轉"],["drop","硬降"],["hold","暫存"]];
// 暫存預設用 C / .：注音輸入法按 Shift 會切中英文
const DEFAULT_KEYS=[{left:"KeyA",right:"KeyD",down:"KeyS",cw:"KeyW",ccw:"KeyQ",drop:"Space",hold:"KeyC"},
  {left:"ArrowLeft",right:"ArrowRight",down:"ArrowDown",cw:"ArrowUp",ccw:"Slash",drop:"Enter",hold:"Period"}];
const RESERVED=["Escape","KeyP","KeyM","Backspace","KeyR"];   // 暫停、靜音、回選單、重來用的鍵
const settings=Object.assign({},DEFAULTS),records={sprint:null,marathon:null,score:null};
let keys=DEFAULT_KEYS.map(k=>Object.assign({},k));
const load=k=>{try{return JSON.parse(localStorage.getItem(k)||"null")}catch(e){return null}};
const save=(k,v)=>{try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}};
{const s=load("taco-blocks-settings");if(s){for(const k in DEFAULTS)if(typeof s[k]===typeof DEFAULTS[k])settings[k]=s[k];
   if(s.hold==="Shift"){keys[0].hold="ShiftLeft";keys[1].hold="ShiftRight"}}   // 舊版的暫存鍵設定
 if(!SPEEDS[settings.speed])settings.speed="中";if(!STYLES.includes(settings.style))settings.style="Cossack EDM";if(!THEMES.includes(settings.theme))settings.theme="卡通";
 const r=load("taco-blocks-records");if(r)Object.assign(records,r);
 const k=load("taco-blocks-keys");if(Array.isArray(k)&&k.length===2)k.forEach((m,i)=>{for(const [a] of ACTIONS)if(typeof m?.[a]==="string")keys[i][a]=m[a]})}
function toggleSetting(k){if(k==="speed"||k==="style"||k==="theme"){const n=k==="speed"?Object.keys(SPEEDS):k==="style"?STYLES:THEMES;settings[k]=n[(n.indexOf(settings[k])+1)%n.length]}else settings[k]=!settings[k];
  save("taco-blocks-settings",settings);applyTheme();audio.refresh()}
const label=k=>(k==="speed"||k==="style"||k==="theme")?settings[k]:(settings[k]?"開":"關");
function applyTheme(){document.body.classList.toggle("toon",settings.theme!=="霓虹")}
const KEY_NAMES={Space:"空白",Enter:"Enter",NumpadEnter:"數字 Enter",ShiftLeft:"左 Shift",ShiftRight:"右 Shift",ControlLeft:"左 Ctrl",ControlRight:"右 Ctrl",
  AltLeft:"左 Alt",AltRight:"右 Alt",ArrowLeft:"←",ArrowRight:"→",ArrowUp:"↑",ArrowDown:"↓",Slash:"/",Period:".",Comma:",",Semicolon:";",Quote:"'",
  BracketLeft:"[",BracketRight:"]",Backslash:"\\",Minus:"-",Equal:"=",Backquote:"`",Tab:"Tab",CapsLock:"Caps"};
function keyName(c){if(!c)return"（未設定）";if(KEY_NAMES[c])return KEY_NAMES[c];let m;
  if((m=/^Key(.)$/.exec(c)))return m[1];if((m=/^Digit(.)$/.exec(c)))return m[1];if((m=/^Numpad(.+)$/.exec(c)))return"數字 "+({Decimal:".",Add:"+",Subtract:"-",Multiply:"*",Divide:"/"}[m[1]]||m[1]);return c}

