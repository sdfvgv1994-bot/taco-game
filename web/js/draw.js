/* taco 方塊對戰：畫面：板子、玩家、主題（卡通／藍天／霓虹）、手機小板子、攻擊動畫。
   所有檔案依 index.html 的順序載入，共用同一個全域範圍。 */
"use strict";
/* ================= 畫面 ================= */
const cv=document.getElementById("cv"),ctx=cv.getContext("2d"),panel=document.getElementById("panel"),stage=document.getElementById("stage");
let W=960,H=640,CELL=26,DPR=1;
function fit(){const r=stage.getBoundingClientRect();DPR=Math.min(window.devicePixelRatio||1,2);W=Math.max(300,r.width);H=Math.max(300,r.height);
  cv.style.width=W+"px";cv.style.height=H+"px";cv.width=W*DPR;cv.height=H*DPR;ctx.setTransform(DPR,0,0,DPR,0,0)}
new ResizeObserver(fit).observe(stage);fit();

const THEME={
  "霓虹":{well:"#14112e",grid:"#231d4a",label:"#9a92c9",text:"#ece8ff",gold:"#ffc933",box:"#14112e",frame:null,tints:["#3ff2ff","#ff3fd0"],font:"pixel"},
  "藍天":{well:"#5c8fa8cc",grid:"#ffffff22",label:"#ffffff",text:"#ffffff",gold:"#ffffff",box:"#1f7fe0",frame:"sky",tints:["#ffffff","#ffe066"],font:"toon"},
  "卡通":{well:"#262a3b",grid:"#323750",label:"#ffffff",text:"#ffffff",gold:"#ffd23f",box:"#262a3b",frame:"#1d1d2b",tints:["#2f8cff","#ff5a7a"],font:"toon"}};
const th=()=>THEME[settings.theme]||THEME["卡通"];
function shade(hex,amt){const n=parseInt(hex.slice(1,7),16);const c=[n>>16,n>>8&255,n&255].map(v=>Math.max(0,Math.min(255,v+amt)));return`rgb(${c.join(",")})`}
function rr(x,y,w,h,r){ctx.beginPath();ctx.moveTo(x+r,y);ctx.arcTo(x+w,y,x+w,y+h,r);ctx.arcTo(x+w,y+h,x,y+h,r);ctx.arcTo(x,y+h,x,y,r);ctx.arcTo(x,y,x+w,y,r);ctx.closePath()}
function block(x,y,s,color,alpha=1){ctx.globalAlpha=alpha;
  if(color===COLORS.G){ctx.fillStyle="#7d8196";ctx.fillRect(x+1,y+1,s-2,s-2);ctx.fillStyle="#9ea2b6";ctx.fillRect(x+1,y+1,s-2,Math.max(2,s/6));   // 垃圾：灰底加斜紋
    ctx.save();ctx.beginPath();ctx.rect(x+1,y+1,s-2,s-2);ctx.clip();ctx.strokeStyle="#5f6378";ctx.lineWidth=Math.max(1,s/10);for(let k=-s;k<s;k+=s/3){ctx.beginPath();ctx.moveTo(x+k,y+s);ctx.lineTo(x+k+s,y);ctx.stroke()}ctx.restore();ctx.globalAlpha=1;return}
  if(settings.theme==="藍天"){const g=ctx.createLinearGradient(x,y,x,y+s);g.addColorStop(0,shade(color,40));g.addColorStop(.55,color);g.addColorStop(1,shade(color,-35));
    ctx.fillStyle=g;ctx.fillRect(x+1,y+1,s-2,s-2);ctx.fillStyle="#ffffff55";ctx.fillRect(x+1,y+1,s-2,Math.max(2,s/8));ctx.strokeStyle=shade(color,-55);ctx.lineWidth=1;ctx.strokeRect(x+1.5,y+1.5,s-3,s-3);ctx.globalAlpha=1;return}
  if(settings.theme==="卡通"){const r=Math.max(2,s/5);rr(x+1,y+1,s-2,s-2,r);ctx.fillStyle=color;ctx.fill();ctx.lineWidth=Math.max(1,s/14);ctx.strokeStyle="#1d1d2b";ctx.stroke();
    ctx.fillStyle="#ffffff66";rr(x+s*.18,y+s*.14,s*.64,s*.26,s*.12);ctx.fill();ctx.fillStyle="#00000030";rr(x+s*.14,y+s*.7,s*.72,s*.16,s*.08);ctx.fill();ctx.globalAlpha=1;return}
  ctx.fillStyle=color;ctx.fillRect(x+1,y+1,s-2,s-2);
  const p=Math.max(2,Math.round(s/7));ctx.fillStyle="#ffffff88";ctx.fillRect(x+1,y+1,s-2,p);ctx.fillRect(x+1,y+1,p,s-2);
  ctx.fillStyle="#00000055";ctx.fillRect(x+1,y+s-1-p,s-2,p);ctx.fillRect(x+s-1-p,y+1,p,s-2);ctx.globalAlpha=1}
function mini(kind,cx,cy,s){const c=SHAPES[kind][0],xs=c.map(a=>a[0]),ys=c.map(a=>a[1]);const w=(Math.max(...xs)-Math.min(...xs)+1)*s,h=(Math.max(...ys)-Math.min(...ys)+1)*s;
  for(const [x,y] of c)block(cx-w/2+(x-Math.min(...xs))*s,cy-h/2+(y-Math.min(...ys))*s,s,COLORS[kind])}
function text(t,x,y,size,color,align="center",font){const f=font==="pixel"?'"Silkscreen","DotGothic16",monospace':font==="toon"?'"Lilita One","DotGothic16","Microsoft JhengHei",sans-serif':'"DotGothic16","Microsoft JhengHei",sans-serif';
  ctx.font=`${size}px ${f}`;ctx.textAlign=align;ctx.textBaseline="middle";
  if(font==="toon"){ctx.lineWidth=Math.max(3,size/5);ctx.strokeStyle="#1d1d2b";ctx.lineJoin="round";ctx.strokeText(t,x,y)}
  ctx.fillStyle=color;ctx.fillText(t,x,y)}
/* 外框：霓虹是發光線；卡通是粗圓角深色框 */
function boardFrame(x,y,w,h,color,pad=6){const T=th();
  if(T.frame==="sky"){ctx.save();ctx.strokeStyle="#ffffffdd";ctx.lineWidth=3;ctx.strokeRect(x-2,y-2,w+4,h+4);ctx.restore();return}
  if(!T.frame){ctx.save();ctx.shadowColor=color;ctx.shadowBlur=14;ctx.strokeStyle=color;ctx.lineWidth=2;ctx.strokeRect(x-3,y-3,w+6,h+6);ctx.restore();return}
  rr(x-pad-3,y-pad-3,w+pad*2+6,h+pad*2+6,pad+8);ctx.fillStyle=T.frame;ctx.fill();
  rr(x-pad,y-pad,w+pad*2,h+pad*2,pad+5);ctx.fillStyle="#3b4058";ctx.fill();ctx.lineWidth=3;ctx.strokeStyle=color;ctx.stroke()}
function skyBox(x,y,w,h,label,value){const g=ctx.createLinearGradient(x,y,x,y+h);g.addColorStop(0,"#2f9bff");g.addColorStop(1,"#1567d3");
  ctx.save();ctx.shadowColor="#0b3d8a66";ctx.shadowBlur=10;ctx.shadowOffsetY=4;rr(x,y,w,h,Math.min(14,h/4));ctx.fillStyle=g;ctx.fill();ctx.restore();
  rr(x,y,w,h,Math.min(14,h/4));ctx.lineWidth=2;ctx.strokeStyle="#7cc4ff";ctx.stroke();
  ctx.save();ctx.font=`${Math.max(11,CELL*.55)}px "Lilita One","DotGothic16",sans-serif`;ctx.textAlign="center";ctx.textBaseline="middle";ctx.fillStyle="#d8ecff";ctx.fillText(label,x+w/2,y+Math.max(12,CELL*.7));
  if(value!=null){ctx.font=`${Math.max(14,CELL*1.05)}px "Lilita One","DotGothic16",sans-serif`;ctx.fillStyle="#fff";ctx.shadowColor="#0b3d8a";ctx.shadowOffsetY=2;ctx.fillText(value,x+w/2,y+h*.62)}ctx.restore()}
function box(x,y,w,h,label){const T=th();if(T.frame==="sky"){skyBox(x,y,w,h,label);return}boardFrame(x,y,w,h,T.frame?"#5b6180":"#2c2560",T.frame?4:0);ctx.fillStyle=T.box;ctx.fillRect(x,y,w,h);
  if(label)text(label,x+w/2,y-(T.frame?14:9),Math.max(10,CELL*(T.frame?.62:.5)),T.label,"center",T.font)}
function star(cx,cy,r,on){ctx.beginPath();for(let i=0;i<10;i++){const a=-Math.PI/2+i*Math.PI/5,rad=i%2?r*.45:r;ctx.lineTo(cx+Math.cos(a)*rad,cy+Math.sin(a)*rad)}ctx.closePath();
  ctx.fillStyle=on?"#ffd23f":"#00000055";ctx.fill();ctx.lineWidth=Math.max(1,r/5);ctx.strokeStyle="#1d1d2b";ctx.stroke()}

/* 一位玩家：上方名牌（名字、KO 星星）、左邊暫存與送出行數、中間板子、右邊下一個與分數 */
function drawPlayerSky(p,ox,oy,s,name,color,info){const bw=COLS*s,bh=ROWS*s,side=s*4.6;
  const sx=p.shake>0?Math.sin(p.shake*90)*p.shake*14:0;ox+=sx;const bx=ox+side+14;p._pos={cx:bx+bw/2,cy:oy+bh/2,meterX:bx-8,bottom:oy+bh};
  text(name,bx+bw/2,oy-s*.9,Math.max(13,s*.7),color,"center","toon");
  if(cfg.kind==="battle"||cfg.kind==="attack"){const r=Math.max(5,s*.36);for(let i=0;i<5;i++)star(bx+bw/2+(i-2)*r*2.4,oy-s*2,r,i<p.ko);if(p.ko>5)text(`+${p.ko-5}`,bx+bw/2+3*r*2.4,oy-s*2,Math.max(10,s*.45),"#fff","center","toon")}
  skyBox(ox,oy,side,s*3.6,"Hold");if(p.hold){ctx.globalAlpha=p.canHold?1:.35;mini(p.hold,ox+side/2,oy+s*2.3,s*.7);ctx.globalAlpha=1}
  const vs=match.attacks;const items=[["Score",p.score.toLocaleString()],vs?["Lines Sent",p.sent]:["Line Clears",p.lines],
    cfg.kind==="battle"||cfg.kind==="attack"?["KO",p.ko]:["Level",Math.min(p.level,MAX_LEVEL)]];
  items.forEach(([l,v],i)=>skyBox(ox,oy+s*(4.4+i*3.6),side,s*3,l,String(v)));
  if(p.koAge!=null&&p.koAge<1.6){const k=Math.min(1,p.koAge*5),r=s*1.3*(k<1?k*1.15:1);ctx.save();ctx.globalAlpha=Math.min(1,(1.6-p.koAge)*2);
    ctx.beginPath();ctx.arc(ox+side/2,oy+s*16.6,r,0,Math.PI*2);ctx.fillStyle="#ff4d6a";ctx.fill();ctx.lineWidth=3;ctx.strokeStyle="#fff";ctx.stroke();text("KO",ox+side/2,oy+s*16.4,r*.7,"#fff","center","toon");ctx.restore()}
  const inc=Math.min(p.pending.reduce((a,b)=>a+b,0),ROWS);ctx.fillStyle="#ffffff44";ctx.fillRect(bx-11,oy,6,bh);if(inc){ctx.fillStyle="#ff4d6a";ctx.fillRect(bx-11,oy+bh-inc*s,6,inc*s)}
  ctx.fillStyle="#5c8fa8d9";ctx.fillRect(bx,oy,bw,bh);ctx.strokeStyle="#ffffff26";ctx.lineWidth=1;ctx.beginPath();
  for(let i=1;i<COLS;i++){ctx.moveTo(bx+i*s+.5,oy);ctx.lineTo(bx+i*s+.5,oy+bh)}for(let i=1;i<ROWS;i++){ctx.moveTo(bx,oy+i*s+.5);ctx.lineTo(bx+bw,oy+i*s+.5)}ctx.stroke();
  p.grid.forEach((row,y)=>row.forEach((c,x)=>{if(c)block(bx+x*s,oy+y*s,s,COLORS[c])}));
  if(p.active&&!p.remote){if(settings.ghost){const dy=p.ghostY()-p.y;for(const [x,y] of p.cells())if(y+dy>=0){ctx.fillStyle="#ffffff22";ctx.fillRect(bx+x*s+1,oy+(y+dy)*s+1,s-2,s-2);ctx.strokeStyle="#ffffffaa";ctx.lineWidth=2;ctx.strokeRect(bx+x*s+2,oy+(y+dy)*s+2,s-4,s-4)}}
    for(const [x,y] of p.cells())if(y>=0)block(bx+x*s,oy+y*s,s,COLORS[p.kind])}
  boardFrame(bx,oy,bw,bh,p.shake>0?"#ff4d6a":"#fff");
  if(!p.alive||p.done){ctx.fillStyle="#00000066";ctx.fillRect(bx,oy,bw,bh)}
  if(p.glow<1.6){ctx.save();ctx.globalAlpha=(1-p.glow/1.6)*.5;ctx.fillStyle="#45ff8a";ctx.fillRect(bx,oy,bw,bh);ctx.restore()}
  const nx=bx+bw+14;skyBox(nx,oy,side,s*3.6,"Next");mini(p.queue[0],nx+side/2,oy+s*2.3,s*.72);
  skyBox(nx,oy+s*4.4,side,s*10.4,"");p.queue.slice(1,5).forEach((k,i)=>mini(k,nx+side/2,oy+s*6+i*s*2.4,s*.55));
  p._btn={x:nx,y:oy+s*15.6,w:side,h:s*4.4};
  if(p.event&&p.eventAge<1.5){ctx.save();ctx.globalAlpha=Math.min(1,(1.5-p.eventAge)*2);text(p.event,bx+bw/2,oy+bh/2-s*2,Math.max(16,s*.85),"#fff","center","toon");ctx.restore()}}

/* 藍天：板子右下的大顆暫停、靜音按鈕（畫在畫布上，點一下就有作用） */
let canvasBtns=[];
function roundBtn(cx,cy,r,kind,on){const g=ctx.createLinearGradient(0,cy-r,0,cy+r);g.addColorStop(0,"#3aa8ff");g.addColorStop(1,"#1567d3");
  ctx.save();ctx.shadowColor="#0b3d8a88";ctx.shadowBlur=8;ctx.shadowOffsetY=3;rr(cx-r,cy-r,r*2,r*2,r*.45);ctx.fillStyle=g;ctx.fill();ctx.restore();
  rr(cx-r,cy-r,r*2,r*2,r*.45);ctx.lineWidth=2;ctx.strokeStyle="#bfe2ff";ctx.stroke();ctx.fillStyle="#fff";
  if(kind==="pause"){if(on){ctx.beginPath();ctx.moveTo(cx-r*.3,cy-r*.45);ctx.lineTo(cx+r*.45,cy);ctx.lineTo(cx-r*.3,cy+r*.45);ctx.fill()}else{ctx.fillRect(cx-r*.38,cy-r*.45,r*.26,r*.9);ctx.fillRect(cx+r*.12,cy-r*.45,r*.26,r*.9)}}
  else{ctx.beginPath();ctx.moveTo(cx-r*.5,cy-r*.18);ctx.lineTo(cx-r*.25,cy-r*.18);ctx.lineTo(cx+r*.05,cy-r*.45);ctx.lineTo(cx+r*.05,cy+r*.45);ctx.lineTo(cx-r*.25,cy+r*.18);ctx.lineTo(cx-r*.5,cy+r*.18);ctx.fill();
    ctx.strokeStyle="#fff";ctx.lineWidth=Math.max(2,r*.12);ctx.beginPath();if(on){ctx.moveTo(cx+r*.2,cy-r*.22);ctx.lineTo(cx+r*.56,cy+r*.22);ctx.moveTo(cx+r*.56,cy-r*.22);ctx.lineTo(cx+r*.2,cy+r*.22)}else{ctx.arc(cx+r*.12,cy,r*.38,-.8,.8)}ctx.stroke()}
  canvasBtns.push({kind,x:cx-r,y:cy-r,w:r*2,h:r*2})}
cv.addEventListener("pointerdown",e=>{const r=cv.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;audio.init();
  for(const b of canvasBtns)if(x>=b.x&&x<=b.x+b.w&&y>=b.y&&y<=b.y+b.h){e.preventDefault();if(b.kind==="pause"){if(state==="play"&&match&&!match.over)setPause(!paused)}else{audio.muted=!audio.muted;muteBtn()}}});

/* 藍天的背景：亮藍漸層，後面慢慢飄著模糊的大方塊 */
const floaters=Array.from({length:14},(_,i)=>({k:KINDS[i%7],x:Math.random(),y:Math.random(),r:Math.floor(Math.random()*4),v:.004+Math.random()*.008,rot:Math.random()*6,vr:(Math.random()-.5)*.2,sz:.6+Math.random()*.7}));
function drawSkyBg(dt){const g=ctx.createLinearGradient(0,0,W,H);g.addColorStop(0,"#1ec8ff");g.addColorStop(.5,"#3fa9ff");g.addColorStop(1,"#1a6fe8");ctx.fillStyle=g;ctx.fillRect(0,0,W,H);
  const s=Math.max(24,Math.min(W,H)/11);ctx.save();ctx.filter="blur(5px)";
  for(const f of floaters){f.y-=f.v*(dt||0);f.rot+=f.vr*(dt||0);if(f.y<-.2){f.y=1.15;f.x=Math.random()}
    ctx.save();ctx.translate(f.x*W,f.y*H);ctx.rotate(f.rot);ctx.globalAlpha=.55;const z=s*f.sz;
    for(const [x,y] of SHAPES[f.k][f.r]){ctx.fillStyle=COLORS[f.k];ctx.fillRect((x-1.5)*z,(y-1.5)*z,z-2,z-2)}ctx.restore()}
  ctx.restore();ctx.fillStyle="#ffffff40";for(let i=0;i<40;i++){const x=(i*137.5%100)/100*W,y=(i*61.8%100)/100*H;ctx.beginPath();ctx.arc(x,y,2+(i%3),0,Math.PI*2);ctx.fill()}}

function drawPlayer(p,ox,oy,s,name,color,info,mirror){const T=th(),bw=COLS*s,bh=ROWS*s,side=s*4.2;
  if(T.frame==="sky")return drawPlayerSky(p,ox,oy,s,name,color,info);
  const sx=p.shake>0?Math.sin(p.shake*90)*p.shake*14:0;ox+=sx;
  const bx=ox+side+14;p._pos={cx:bx+bw/2,cy:oy+bh/2,meterX:bx-8,bottom:oy+bh};
  // 名牌
  const cardY=oy-s*2.3,cardH=s*1.5;
  if(T.frame){rr(bx-6,cardY,bw+12,cardH,cardH/2);ctx.fillStyle=color;ctx.fill();ctx.lineWidth=3;ctx.strokeStyle="#1d1d2b";ctx.stroke()}
  text(name,bx+bw/2,cardY+cardH/2,Math.max(12,s*.62),T.frame?"#fff":color,"center",T.font==="toon"?"toon":null);
  if(cfg.kind==="battle"||cfg.kind==="attack"){const r=Math.max(5,s*.38);for(let i=0;i<5;i++)star(bx+bw/2+(i-2)*r*2.4,cardY-r-3,r,i<p.ko);
    if(p.ko>5)text(`+${p.ko-5}`,bx+bw/2+3*r*2.4,cardY-r-3,Math.max(10,s*.45),T.gold,"center",T.font)}
  // 暫存、送出行數
  box(ox,oy+s*.6,side,s*3,"HOLD");if(p.hold){ctx.globalAlpha=p.canHold?1:.35;mini(p.hold,ox+side/2,oy+s*2.1,s*.7);ctx.globalAlpha=1}
  if(match.attacks||cfg.kind==="score"){const isScore=cfg.kind==="score";box(ox,oy+s*5.6,side,s*2.6,isScore?"LINES":"SENT");
    text(String(isScore?p.lines:p.sent),ox+side/2,oy+s*6.9,Math.max(14,s*1.1),T.gold,"center",T.font)}
  // KO 徽章
  if(p.koAge!=null&&p.koAge<1.6){const k=Math.min(1,p.koAge*5),r=s*1.3*(k<1?k*1.15:1);ctx.save();ctx.globalAlpha=Math.min(1,(1.6-p.koAge)*2);
    ctx.beginPath();ctx.arc(ox+side/2,oy+s*10.5,r,0,Math.PI*2);ctx.fillStyle="#ff4d6a";ctx.fill();ctx.lineWidth=3;ctx.strokeStyle="#fff";ctx.stroke();
    text("KO",ox+side/2,oy+s*10.2,r*.7,"#fff","center",T.font);text(String(p.ko),ox+side/2,oy+s*11.1,r*.45,"#fff","center",T.font);ctx.restore()}
  // 垃圾條
  const inc=Math.min(p.pending.reduce((a,b)=>a+b,0),ROWS);ctx.fillStyle=T.well;ctx.fillRect(bx-11,oy,6,bh);if(inc){ctx.fillStyle="#ff4d6a";ctx.fillRect(bx-11,oy+bh-inc*s,6,inc*s)}
  // 板子
  boardFrame(bx,oy,bw,bh,p.shake>0?"#ff4d6a":color);
  ctx.fillStyle=T.well;ctx.fillRect(bx,oy,bw,bh);ctx.strokeStyle=T.grid;ctx.lineWidth=1;ctx.beginPath();
  for(let i=1;i<COLS;i++){ctx.moveTo(bx+i*s+.5,oy);ctx.lineTo(bx+i*s+.5,oy+bh)}for(let i=1;i<ROWS;i++){ctx.moveTo(bx,oy+i*s+.5);ctx.lineTo(bx+bw,oy+i*s+.5)}ctx.stroke();
  p.grid.forEach((row,y)=>row.forEach((c,x)=>{if(c)block(bx+x*s,oy+y*s,s,COLORS[c])}));
  if(p.active&&!p.remote){if(settings.ghost){const dy=p.ghostY()-p.y;for(const [x,y] of p.cells())if(y+dy>=0){ctx.strokeStyle=COLORS[p.kind];ctx.lineWidth=2;ctx.globalAlpha=.6;ctx.strokeRect(bx+x*s+3,oy+(y+dy)*s+3,s-6,s-6);ctx.globalAlpha=1}}
    for(const [x,y] of p.cells())if(y>=0)block(bx+x*s,oy+y*s,s,COLORS[p.kind])}
  if(!p.alive||p.done){ctx.fillStyle="#000a";ctx.fillRect(bx,oy,bw,bh)}
  if(p.glow<1.6){ctx.save();ctx.globalAlpha=(1-p.glow/1.6)*.5;ctx.fillStyle="#45ff8a";ctx.fillRect(bx,oy,bw,bh);ctx.restore()}
  // 下一個、分數
  const nx=bx+bw+14;box(nx,oy+s*.6,side,s*10.6,"NEXT");p.queue.slice(0,4).forEach((k,i)=>mini(k,nx+side/2,oy+s*.6+s*1.4+i*s*2.6,i?s*.55:s*.72));
  box(nx,oy+s*13,side,s*2.2,"SCORE");text(p.score.toLocaleString(),nx+side/2,oy+s*14.1,Math.max(10,s*.6),T.gold,"center",T.font==="toon"?"toon":"pixel");
  text(info,bx+bw/2,oy+bh+(T.frame?22:16),Math.max(12,s*.52),T.frame?"#14304a":T.text);
  if(p.event&&p.eventAge<1.5){ctx.save();ctx.globalAlpha=Math.min(1,(1.5-p.eventAge)*2);if(!T.frame){ctx.shadowColor="#ffc933";ctx.shadowBlur=12}
    text(p.event,bx+bw/2,oy+bh/2-s*2,Math.max(16,s*.85),T.gold,"center",T.font==="toon"?"toon":null);ctx.restore()}}

/* 手機直式：對手縮成小板子（只有板子、名字、KO 和送出行數） */
function drawSmallBoard(p,x,y,s,name,color){const T=th(),bw=COLS*s,bh=ROWS*s;const sx=p.shake>0?Math.sin(p.shake*90)*p.shake*8:0;x+=sx;
  p._pos={cx:x+bw/2,cy:y+bh/2,meterX:x-5,bottom:y+bh};
  text(name,x+bw/2,y-12,Math.max(11,s*1.1),T.frame==="sky"?"#fff":color,"center",T.font==="toon"?"toon":null);
  ctx.fillStyle=T.frame==="sky"?"#5c8fa8d9":T.well;ctx.fillRect(x,y,bw,bh);
  p.grid.forEach((row,yy)=>row.forEach((c,xx)=>{if(c){ctx.fillStyle=COLORS[c];ctx.fillRect(x+xx*s,y+yy*s,s-1,s-1)}}));
  if(p.active&&!p.remote)for(const [cx,cy] of p.cells())if(cy>=0){ctx.fillStyle=COLORS[p.kind];ctx.fillRect(x+cx*s,y+cy*s,s-1,s-1)}
  const inc=Math.min(p.pending.reduce((a,b)=>a+b,0),ROWS);if(inc){ctx.fillStyle="#ff4d6a";ctx.fillRect(x-5,y+bh-inc*s,3,inc*s)}
  ctx.strokeStyle=p.shake>0?"#ff4d6a":(T.frame==="sky"?"#fff":color);ctx.lineWidth=2;ctx.strokeRect(x-1,y-1,bw+2,bh+2);
  if(!p.alive||p.done){ctx.fillStyle="#000a";ctx.fillRect(x,y,bw,bh)}
  const line=cfg.kind==="score"?`${p.score.toLocaleString()} 分`:cfg.kind==="survival"?`送出 ${p.sent}`:`KO ${p.ko}　送 ${p.sent}`;
  text(line,x+bw/2,y+bh+12,Math.max(10,s*.95),T.frame==="sky"||T.frame?"#fff":"#ece8ff","center");
  if(p.event&&p.eventAge<1.2)text(p.event,x+bw/2,y+bh/2,Math.max(10,s*1.1),T.gold,"center",T.font==="toon"?"toon":null)}

/* 卡通風格的畫布背景：放射光線＋圓點（我們自己的設計） */
function drawToonBg(){const g=ctx.createLinearGradient(0,0,0,H);g.addColorStop(0,"#5db6ea");g.addColorStop(1,"#bfe6f8");ctx.fillStyle=g;ctx.fillRect(0,0,W,H);
  ctx.save();ctx.translate(W/2,H*.45);ctx.fillStyle="#ffffff1c";for(let i=0;i<16;i++){ctx.rotate(Math.PI/8);ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(Math.max(W,H),-Math.max(W,H)*.12);ctx.lineTo(Math.max(W,H),Math.max(W,H)*.12);ctx.fill()}ctx.restore();
  ctx.fillStyle="#ffffff30";for(let y=12;y<H;y+=36)for(let x=(y/36%2)*18+8;x<W;x+=36){ctx.beginPath();ctx.arc(x,y,3,0,Math.PI*2);ctx.fill()}}

/* 攻擊動畫：發光的能量球從攻擊者飛到對手的垃圾條 */
function drawShots(dt){if(!match)return;const keep=[];
  for(const sh of match.shots){if(sh.age===0)audio.play("shot");sh.age+=dt;const a=match.players[sh.from]._pos,b=match.players[sh.to]._pos;if(!a||!b)continue;
    const k=Math.min(1,sh.age/.45),e=k<.5?2*k*k:1-Math.pow(-2*k+2,2)/2;
    const x=a.cx+(b.meterX-a.cx)*e,y=a.cy+(b.bottom-CELL*2-a.cy)*e-Math.sin(Math.PI*e)*CELL*5,r=CELL*(.45+Math.min(sh.n,10)*.06);
    ctx.save();ctx.shadowColor="#ff3fd0";ctx.shadowBlur=24;ctx.fillStyle="#ff3fd0";ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();
    ctx.fillStyle="#fff";ctx.beginPath();ctx.arc(x,y,r*.45,0,Math.PI*2);ctx.fill();ctx.restore();
    text("+"+sh.n,x,y-r-10,Math.max(12,CELL*.6),"#ffc933","center","pixel");
    if(k<1)keep.push(sh);else{audio.play("hit");match.players[sh.to].shake=Math.max(match.players[sh.to].shake,.25)}}
  match.shots=keep}

