/* taco 方塊對戰：遊戲狀態：目前的對局、玩家、按鍵對應。
   所有檔案依 index.html 的順序載入，共用同一個全域範圍。 */
"use strict";
/* ================= 遊戲狀態 ================= */
const MODES=[
  {key:1,title:"KO 對戰",desc:"限時 2 分鐘，把對手頂到頂得 1 KO；KO > 送出行數 > 行高",cfg:{kind:"battle",time:120,vs:true}},
  {key:2,title:"分數對戰",desc:"限時 2 分鐘比分數，不互相攻擊；頂到頂就停在那個分數",cfg:{kind:"score",time:120,vs:true}},
  {key:3,title:"攻擊對戰",desc:`先送出 ${ATTACK_GOAL} 行攻擊的人贏（最多 3 分鐘）`,cfg:{kind:"attack",time:180,vs:true}},
  {key:4,title:"生死戰",desc:"先被頂到頂的人輸",cfg:{kind:"survival",vs:true}},
  {key:5,title:"Sprint 40 行",desc:"單人，消 40 行比時間",cfg:{kind:"sprint"}},
  {key:6,title:"Marathon",desc:"單人 15 關，越來越快",cfg:{kind:"marathon"}},
];
let state="menu",cfg=null,diff=null,match=null,ais={},names=[],countdown=0,lastBeep=0,paused=false,scored=false,note="",wins=[0,0],waitKey=null;
const held={};

function start(c,d){cfg=c;diff=d;state="play";paused=false;scored=false;note="";
  const n=c.vs?2:1;match=new Match(n,c.kind,c.time||null);ais={};
  if(c.vs&&d===null)names=["玩家 1","玩家 2"];else if(c.vs){ais={1:new AI(DIFFICULTY[d])};names=["你",`電腦（${d}）`]}else names=["你"];
  countdown=settings.countdown?3:0;lastBeep=0;audio.stopMusic();audio.paused=false;if(!countdown){audio.play("go");audio.startMusic()}
  for(const k in held)delete held[k];hidePanel()}

/* 這個按鍵控制哪位玩家的哪個動作：對電腦或單人時，兩組按鍵都給玩家 1 */
function controllers(code){const out=[],two=cfg.vs&&diff===null;
  keys.forEach((m,set)=>{for(const [a] of ACTIONS)if(m[a]===code)out.push([two?set:0,a])});return out}
function act(i,a){const p=match.players[i];if(!p)return;
  if(a==="left"){p.move(-1);held[i]={d:-1,t:0}}else if(a==="right"){p.move(1);held[i]={d:1,t:0}}
  else if(a==="cw")p.rotate(1);else if(a==="ccw")p.rotate(-1);else if(a==="hold")p.doHold();else if(a==="drop")match.hardDrop(i);else if(a==="down")p.soft=true;flush()}
function release(i,a){const p=match&&match.players[i];if(!p)return;if(a==="down")p.soft=false;if((a==="left"&&held[i]&&held[i].d<0)||(a==="right"&&held[i]&&held[i].d>0))delete held[i]}
function flush(){match.players.forEach((p,i)=>{const ev=[...new Set(p.sfx)];p.sfx=[];for(const n of ev){if(ais[i]){if(n==="ko"||n.startsWith("clear")||n==="tspin")audio.play(n)}else if(n!=="warn")audio.play(n)}})}

/* 這一版的代號（部署時換成提交代號；本機開是 dev）：更新提示、線上對戰比對雙方版本用 */
const APP_VERSION=(document.querySelector('meta[name="app-version"]')||{}).content||"dev";
