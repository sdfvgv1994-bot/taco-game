/* taco 方塊對戰：主迴圈：每一幀更新、畫圖，以及開場。
   所有檔案依 index.html 的順序載入，共用同一個全域範圍。 */
"use strict";
/* ================= 主迴圈 ================= */
let last=performance.now();
function frame(now){const dt=Math.min((now-last)/1000,.05);last=now;
  if(state==="play"&&!paused&&match){
    if(countdown>0){countdown-=dt;const b=countdown>0?Math.ceil(countdown):0;if(b!==lastBeep){audio.play(b?"count":"go");if(!b){if(NET.resuming){NET.resuming=false;audio.paused=false}else audio.startMusic()}lastBeep=b}}
    else if(!match.over){const [das,arr]=SPEEDS[settings.speed];
      for(const i in held){const h=held[i];h.t+=dt;while(h.t>=das+arr){h.t-=arr;match.players[i].move(h.d)}}
      for(const i in ais)ais[i].update(dt,match.players[i],match,+i);match.update(dt);flush()}
    if(match.over&&!scored){scored=true;audio.stopMusic();const m=match;
      if(cfg.kind==="sprint"&&m.success&&(records.sprint==null||m.finish[0]<records.sprint)){records.sprint=+m.finish[0].toFixed(2);note="新紀錄！"}
      if(cfg.kind==="marathon"&&(records.marathon==null||m.players[0].lines>records.marathon)){records.marathon=m.players[0].lines;note="新紀錄！"}
      if(cfg.kind==="score"&&(records.score==null||m.players[0].score>records.score)&&!(diff===null)){records.score=m.players[0].score;note="新的最高分！"}
      save("taco-blocks-records",records);
      if(m.players.length===2&&(m.winner===0||m.winner===1))wins[m.winner]++;
      audio.play(m.winner===0||m.success||(diff===null&&m.winner===1)?"win":"dead");setTimeout(()=>{if(state==="play"&&match===m)showResult()},1000)}}
  render(dt);requestAnimationFrame(frame)}

const GOALS={battle:"2 分鐘內盡量把對手頂到頂（KO）",score:"2 分鐘內拿最高分",attack:`先送出 ${ATTACK_GOAL} 行攻擊`,survival:"別被頂到頂，撐到對手倒下",sprint:"盡快消掉 40 行",marathon:"撐過 15 關"};
function render(dt){ctx.clearRect(0,0,W,H);const T=th();canvasBtns=[];
  if(T.frame==="sky")drawSkyBg(dt);else if(T.frame)drawToonBg();
  if(!match){if(T.frame!=="sky")drawAttract();return}
  const n=match.players.length,pad=22,unitW=(4.2*2+COLS)+2,unitH=ROWS+6.2,gap=n>1?Math.max(30,W*.06):0;
  let ox,oy,cx;
  const wide=Math.floor(Math.min((W-pad*2-(n-1)*gap)/(unitW*n),(H-pad)/unitH));
  const compact=n===2&&wide<15;   // 兩個完整板子放不下（手機直式）
  if(compact){
    // 自己的板子用掉大部分寬度，右邊留一條給對手的小板子
    const smallW=COLS*.48+1.2;CELL=Math.floor(Math.min((W-16)/(unitW+smallW),(H-pad)/unitH));CELL=Math.max(8,Math.min(CELL,32));
    const total=(unitW+smallW)*CELL;ox=Math.max(4,(W-total)/2);oy=(H-ROWS*CELL)/2+CELL*1.8;
    const p0=match.players[0];drawPlayer(p0,ox,oy,CELL,names[0],T.tints[0],({battle:`KO ${p0.ko}　送出 ${p0.sent}`,attack:`送出 ${p0.sent} / ${ATTACK_GOAL}`,score:`消行 ${p0.lines}`,survival:`送出 ${p0.sent}`}[cfg.kind]||""));
    const ss=Math.max(4,Math.floor(CELL*.48));drawSmallBoard(match.players[1],ox+unitW*CELL+CELL*.4,oy+CELL*1.2,ss,names[1],T.tints[1]);
    cx=ox+(unitW*CELL)/2;
  }else{
    CELL=Math.max(8,Math.min(wide,32));
    const total=n*unitW*CELL+(n-1)*gap;ox=(W-total)/2;oy=(H-ROWS*CELL)/2+CELL*1.8;
    match.players.forEach((p,i)=>{const info={battle:`KO ${p.ko}　送出 ${p.sent}`,attack:`送出 ${p.sent} / ${ATTACK_GOAL}`,score:`消行 ${p.lines}`,survival:`送出 ${p.sent}`}[cfg.kind]||`消行 ${p.lines}　等級 ${Math.min(p.level,MAX_LEVEL)}`;
      drawPlayer(p,ox+i*(unitW*CELL+gap),oy,CELL,names[i],T.tints[i],info,i===1)});
    cx=n===2?ox+unitW*CELL+gap/2:W/2;
  }
  drawShots(paused?0:dt);
  if(T.frame==="sky"){const last=match.players[compact?0:n-1]._btn;if(last){const r=Math.min(last.w/4.6,CELL*1.15);roundBtn(last.x+last.w/2-r*1.15,last.y+last.h-r,r,"pause",paused);roundBtn(last.x+last.w/2+r*1.15,last.y+last.h-r,r,"mute",audio.muted)}}
  // 上方正中央的計時器
  let hud="",lab="TIME";const t=match.timeLeft;
  if(t!=null){const s=Math.ceil(t);hud=`${String(Math.floor(s/60)).padStart(2,"0")}:${String(s%60).padStart(2,"0")}`}
  if(cfg.kind==="sprint"){hud=fmt(match.elapsed);lab=`剩 ${Math.max(0,40-match.players[0].lines)} 行`}
  else if(cfg.kind==="marathon"){const p=match.players[0];hud=`${Math.min(p.level,MAX_LEVEL)}/${MAX_LEVEL}`;lab="LEVEL"}
  else if(cfg.kind==="survival"&&n===2){hud=`${wins[0]} : ${wins[1]}`;lab="WINS"}
  const cy=Math.max(26,oy-CELL*3.6),fs=Math.max(16,CELL*.95),pw=Math.max(110,fs*4.6),ph=fs*1.7;
  if(hud){if(T.frame==="sky"){skyBox(cx-pw/2,cy-ph/2,pw,ph,"")}else if(T.frame){rr(cx-pw/2,cy-ph/2,pw,ph,ph/2);ctx.fillStyle="#1d1d2b";ctx.fill();rr(cx-pw/2+4,cy-ph/2+4,pw-8,ph-8,ph/2-4);ctx.fillStyle="#fff7d6";ctx.fill()}
    text(lab,cx,cy-ph/2-8,Math.max(10,CELL*.45),T.frame==="sky"?"#fff":T.frame?"#14304a":T.label,"center",T.font);
    text(hud,cx,cy+1,fs,t!=null&&t<=10?"#ff4d6a":(T.frame==="sky"?"#fff":T.frame?"#ff8a1f":T.gold),"center",T.font)}
  if(cfg.kind==="attack"&&n===2){const bw=Math.min(200,W*.22),x=cx-bw/2,y=cy+ph/2+8;
    match.players.forEach((p,i)=>{ctx.fillStyle=T.well;ctx.fillRect(x,y+i*9,bw,6);ctx.fillStyle=T.tints[i];ctx.fillRect(x,y+i*9,bw*Math.min(1,p.sent/ATTACK_GOAL),6)})}
  // 倒數：數字＋這局的目標
  if(countdown>0){const by=oy+ROWS*CELL/2,bw2=Math.min(W-40,CELL*16),bh2=CELL*6.5;ctx.save();
    if(T.frame){rr(W/2-bw2/2,by-bh2/2,bw2,bh2,18);ctx.fillStyle="#1d1d2bee";ctx.fill();ctx.lineWidth=4;ctx.strokeStyle="#ffd23f";ctx.stroke()}
    else{ctx.fillStyle="#0b0920dd";ctx.fillRect(W/2-bw2/2,by-bh2/2,bw2,bh2);ctx.strokeStyle="#ff3fd0";ctx.lineWidth=2;ctx.strokeRect(W/2-bw2/2,by-bh2/2,bw2,bh2)}
    text(NET.resuming?"READY":"GOAL",W/2,by-bh2/2+CELL*.9,Math.max(12,CELL*.6),T.gold,"center",T.font);
    text(NET.resuming?"兩邊一起繼續":GOALS[cfg.kind]||"",W/2,by-bh2/2+CELL*1.9,Math.max(13,CELL*.62),"#fff");
    if(!T.frame){ctx.shadowColor="#ffc933";ctx.shadowBlur=20}text(String(Math.ceil(countdown)),W/2,by+CELL*1.2,CELL*2.6,T.gold,"center",T.font==="toon"?"toon":"pixel");ctx.restore()}}

const rain=Array.from({length:22},()=>({k:KINDS[Math.floor(Math.random()*7)],x:Math.random(),y:Math.random(),v:.03+Math.random()*.05,r:Math.floor(Math.random()*4)}));
function drawAttract(){const s=Math.max(14,Math.min(W,H)/24);
  for(const d of rain){d.y+=d.v/60;if(d.y>1.1){d.y=-.1;d.x=Math.random()}
    ctx.globalAlpha=.35;for(const [x,y] of SHAPES[d.k][d.r])block(d.x*W+x*s,d.y*H+y*s,s,COLORS[d.k]);ctx.globalAlpha=1}}

applyTheme();showMenu();requestAnimationFrame(frame);
