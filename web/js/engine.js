/* taco 方塊對戰：規則：方塊、消行、垃圾行、T 轉、連擊、分數、各模式的勝負（和 Python 版 engine.py 一樣）。
   所有檔案依 index.html 的順序載入，共用同一個全域範圍。 */
"use strict";
/* ================= 規則（和 Python 版 engine.py 一樣，另外加上分數） ================= */
const COLS=10, ROWS=20, LOCK_DELAY=.5, LINES_PER_LEVEL=10, MAX_LEVEL=15, MAX_LOCK_RESETS=15, SOFT_INTERVAL=.03, MAX_GARBAGE=8;
const ATTACK=[0,0,1,2,4], COMBO_BONUS=[0,1,1,2,2,3,3,4,4,5], COMBO_BURST=5, BURST_ATTACK=2, PERFECT=6, TSPIN_ATTACK=[0,2,4,6], G="G";
const LINE_SCORE=[0,100,300,500,800], TSPIN_SCORE=[400,800,1200,1600], PERFECT_SCORE=3000;  // 分數 × 等級
const ATTACK_GOAL=30;   // 攻擊對戰：先送出幾行垃圾就贏
const BASE={I:[4,[[0,1],[1,1],[2,1],[3,1]]],O:[2,[[0,0],[1,0],[0,1],[1,1]]],T:[3,[[1,0],[0,1],[1,1],[2,1]]],
  S:[3,[[1,0],[2,0],[0,1],[1,1]]],Z:[3,[[0,0],[1,0],[1,1],[2,1]]],J:[3,[[0,0],[0,1],[1,1],[2,1]]],L:[3,[[2,0],[0,1],[1,1],[2,1]]]};
const KINDS=Object.keys(BASE);
const KICKS=[[0,0],[-1,0],[1,0],[-2,0],[2,0],[0,-1],[-1,-1],[1,-1]];
const SHAPES={};
for(const k of KINDS){const [n,c]=BASE[k];let cells=c;const r=[cells];for(let i=0;i<3;i++){cells=cells.map(([x,y])=>[n-1-y,x]);r.push(cells)}SHAPES[k]=r}
const COLORS={I:"#3ff2ff",O:"#ffd23f",T:"#c25bff",S:"#45ff8a",Z:"#ff4d6a",J:"#4d7bff",L:"#ff9a3f",G:"#5c5880"};
const cellsOf=(k,r,x,y)=>SHAPES[k][((r%4)+4)%4].map(([cx,cy])=>[x+cx,y+cy]);
function rng(seed){return()=>{seed|=0;seed=seed+0x6D2B79F5|0;let t=Math.imul(seed^seed>>>15,1|seed);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}

class Player{
  constructor(rand){this.rand=rand;this.grid=Array.from({length:ROWS},()=>Array(COLS).fill(null));this.bag=[];
    this.queue=[];for(let i=0;i<5;i++)this.queue.push(this.draw());
    Object.assign(this,{hold:null,canHold:true,alive:true,lines:0,combo:-1,b2b:false,pending:[],outbox:0,sent:0,ko:0,deaths:0,
      lastAttacker:null,target:null,done:false,soft:false,event:"",eventAge:9,glow:99,sfx:[],lastRotate:false,pieceNo:0,
      score:0,received:0,maxCombo:0,tetrises:0,tspins:0,pieces:0,shake:0,book:{}});
    this.spawn()}
  draw(){if(!this.bag.length){this.bag=KINDS.slice();for(let i=this.bag.length-1;i>0;i--){const j=Math.floor(this.rand()*(i+1));[this.bag[i],this.bag[j]]=[this.bag[j],this.bag[i]]}}return this.bag.pop()}
  spawn(kind){this.pieceNo++;this.kind=kind||this.next();this.rot=0;this.x=Math.floor((COLS-BASE[this.kind][0])/2);this.y=this.kind==="I"?-1:0;
    this.fall=0;this.lockT=0;this.resets=0;if(!this.valid(this.kind,this.rot,this.x,this.y))this.alive=false}
  next(){const k=this.queue.shift();this.queue.push(this.draw());return k}
  valid(k,r,x,y){for(const [cx,cy] of cellsOf(k,r,x,y)){if(cx<0||cx>=COLS||cy>=ROWS)return false;if(cy>=0&&this.grid[cy][cx])return false}return true}
  cells(){return cellsOf(this.kind,this.rot,this.x,this.y)}
  onGround(){return!this.valid(this.kind,this.rot,this.x,this.y+1)}
  ghostY(){let y=this.y;while(this.valid(this.kind,this.rot,this.x,y+1))y++;return y}
  get active(){return this.alive&&!this.done}
  get level(){return Math.floor(this.lines/LINES_PER_LEVEL)+1}
  gravity(){return Math.max(.05,.9*Math.pow(.82,this.level-1))}
  height(){if(this.remote&&this._h!=null)return this._h;const t=this.grid.findIndex(r=>r.some(Boolean));return t<0?0:ROWS-t}
  revive(){this.grid=Array.from({length:ROWS},()=>Array(COLS).fill(null));this.pending=[];this.combo=-1;this.b2b=false;this.canHold=true;this.lastAttacker=null;this.alive=true;this.spawn()}
  moved(){if(this.onGround()){if(this.resets<MAX_LOCK_RESETS){this.lockT=0;this.resets++}}else this.lockT=0}
  move(d){if(!this.active||!this.valid(this.kind,this.rot,this.x+d,this.y))return false;this.x+=d;this.lastRotate=false;this.sfx.push("move");this.moved();return true}
  rotate(d){if(!this.active||this.kind==="O")return false;const r=(this.rot+d+4)%4;
    for(const [kx,ky] of KICKS){if(this.valid(this.kind,r,this.x+kx,this.y+ky)){this.rot=r;this.x+=kx;this.y+=ky;this.lastRotate=true;this.sfx.push("rotate");this.moved();return true}}return false}
  doHold(){if(!this.active||!this.canHold)return false;const old=this.hold;this.hold=this.kind;this.spawn(old);this.canHold=false;this.sfx.push("hold");return true}
  hardDrop(){if(!this.active)return;const gy=this.ghostY();if(gy!==this.y)this.lastRotate=false;this.add("hard",2*(gy-this.y),gy-this.y);this.y=gy;this.sfx.push("drop");this.lock()}
  update(dt){this.eventAge+=dt;this.glow+=dt;if(this.koAge!=null)this.koAge+=dt;this.shake=Math.max(0,this.shake-dt);if(!this.active)return;
    if(this.onGround()){this.lockT+=dt;if(this.lockT>=LOCK_DELAY)this.lock();return}
    const iv=this.soft?Math.min(this.gravity(),SOFT_INTERVAL):this.gravity();this.fall+=dt;
    while(this.fall>=iv&&!this.onGround()){this.fall-=iv;this.y++;this.lastRotate=false;if(this.soft)this.add("soft",1)}if(this.onGround())this.fall=0}
  isTspin(){if(this.kind!=="T"||!this.lastRotate)return false;const cx=this.x+1,cy=this.y+1;let f=0;
    for(const [dx,dy] of [[-1,-1],[1,-1],[-1,1],[1,1]]){const x=cx+dx,y=cy+dy;if(x<0||x>=COLS||y>=ROWS||(y>=0&&this.grid[y][x]))f++}return f>=3}
  ev(t){this.event=t;this.eventAge=0}
  add(kind,pts,count=1){if(!pts)return;const b=this.book[kind]||(this.book[kind]={n:0,pts:0});b.n+=count;b.pts+=pts;this.score+=pts}
  lock(){const ts=this.isTspin(),lvl=Math.min(this.level,MAX_LEVEL);this.pieces++;
    for(const [cx,cy] of this.cells()){if(cy<0){this.alive=false;return}this.grid[cy][cx]=this.kind}
    const kept=this.grid.filter(r=>r.some(c=>!c)),n=ROWS-kept.length;
    if(n){this.grid=Array.from({length:n},()=>Array(COLS).fill(null)).concat(kept);this.lines+=n}
    if(ts)this.tspins++;
    if(!n){this.sfx.push(ts?"tspin":"lock");if(ts){this.ev("T 轉！");this.add("tspin0",TSPIN_SCORE[0]*lvl)}this.combo=-1;this.applyGarbage()}
    else{this.combo++;this.maxCombo=Math.max(this.maxCombo,this.combo);if(n===4)this.tetrises++;
      let atk=(ts?TSPIN_ATTACK[n]:ATTACK[n])+COMBO_BONUS[Math.min(this.combo,COMBO_BONUS.length-1)];
      const burst=this.combo>0&&this.combo%COMBO_BURST===0;if(burst)atk+=BURST_ATTACK;   // 連擊 x5、x10…：連擊爆發
      const base=(ts?TSPIN_SCORE[n]:LINE_SCORE[n])*lvl;let bonus=0;
      let label=["","單行","雙行","三行","四行消除！"][n];if(ts)label="T 轉"+label;
      if(n===4||ts){if(this.b2b){atk++;bonus=Math.round(base*.5);label="連續 "+label}this.b2b=true}else this.b2b=false;
      this.add((ts?"tspin":"line")+n,base);this.add("b2b",bonus);this.add("combo",50*this.combo*lvl);
      let perfect=false;if(this.grid.every(r=>r.every(c=>!c))){atk+=PERFECT;this.add("perfect",PERFECT_SCORE*lvl);label="全清！";this.glow=0;perfect=true}
      if(this.combo>=1)label+=` 連擊 x${this.combo}`;if(burst)label+=" 爆發！";this.ev(label);this.sfx.push(perfect?"perfect":ts?"tspin":"clear"+n);if(burst)this.sfx.push("burst");
      while(atk&&this.pending.length){const t=Math.min(atk,this.pending[0]);atk-=t;this.pending[0]-=t;if(!this.pending[0])this.pending.shift()}
      this.outbox+=atk;this.sent+=atk}
    this.canHold=true;if(this.alive)this.spawn()}
  receive(n,src){if(n>0){this.pending.push(n);this.received+=n;this.lastAttacker=src;this.sfx.push("warn")}}
  applyGarbage(){let b=MAX_GARBAGE;if(this.pending.length)this.shake=.35;while(this.pending.length&&b){const n=Math.min(this.pending[0],b);b-=n;this.pending[0]-=n;if(!this.pending[0])this.pending.shift();
    const hole=Math.floor(this.rand()*COLS);for(let i=0;i<n;i++){if(this.grid[0].some(Boolean))this.alive=false;const row=Array(COLS).fill(G);row[hole]=null;this.grid=this.grid.slice(1).concat([row])}}}
}

/* 模式：battle（限時 KO）、score（限時比分數）、attack（先送出 30 行）、survival（先頂到頂輸）、sprint、marathon */
class Match{
  constructor(n,mode,timeLimit,seed){seed=seed??Math.floor(Math.random()*2**30);this.players=Array.from({length:n},()=>new Player(rng(seed)));
    Object.assign(this,{mode,timeLimit,elapsed:0,finish:Array(n).fill(null),winner:null,success:null,over:false,shots:[]})}
  get goal(){return this.mode==="sprint"?40:MAX_LEVEL*LINES_PER_LEVEL}
  get timeLeft(){return this.timeLimit?Math.max(0,this.timeLimit-this.elapsed):null}
  get attacks(){return["battle","attack","survival"].includes(this.mode)}
  update(dt){if(this.over)return;if(this.net){netUpdate(this,dt);return}this.elapsed+=dt;this.players.forEach(p=>p.update(dt));this.transfer()}
  hardDrop(i){this.players[i].hardDrop();if(this.net)netAfterLocal(this);else this.transfer()}
  transfer(){if(this.over)return;this.players.forEach((p,i)=>{const o=p.outbox;p.outbox=0;if(o&&this.attacks){const t=this.players.findIndex((q,j)=>j!==i&&q.alive);
      if(t>=0){this.players[t].receive(o,i);this.shots.push({from:i,to:t,n:o,age:0})}}});
    ({battle:this.checkKO,attack:this.checkAttack,score:this.checkScore,survival:this.checkSurvival}[this.mode]||this.checkRace).call(this)}
  end(order){this.over=true;this.ranks=order;const a=this.key(order[0]),b=order[1]!=null?this.key(order[1]):null;this.winner=b&&a.every((v,i)=>v===b[i])?-1:order[0]}
  sortBy(){return this.players.map((_,i)=>i).sort((x,y)=>{const a=this.key(x),b=this.key(y);for(let k=0;k<a.length;k++)if(a[k]!==b[k])return b[k]-a[k];return 0})}
  key(i){const p=this.players[i];return this.mode==="score"?[p.score,p.lines]:this.mode==="attack"?[p.sent,p.ko,-p.height()]:[p.ko,p.sent,-p.height()]}
  knockouts(){this.players.forEach((p,i)=>{if(p.alive)return;p.deaths++;const k=p.lastAttacker;if(k!=null&&k!==i){const a=this.players[k];a.ko++;a.koAge=0;a.ev("KO！");a.sfx.push("ko")}p.ev("被擊倒");p.revive()})}
  timeUp(){return this.timeLimit&&this.elapsed>=this.timeLimit}
  checkKO(){this.knockouts();if(this.timeUp())this.end(this.sortBy())}
  checkAttack(){this.knockouts();if(this.players.some(p=>p.sent>=ATTACK_GOAL)||this.timeUp())this.end(this.sortBy())}
  checkScore(){const alive=this.players.filter(p=>p.alive).length;if(this.timeUp()||alive===0)this.end(this.sortBy())}   // 頂到頂就停在那個分數
  checkSurvival(){const alive=this.players.map((p,i)=>p.alive?i:-1).filter(i=>i>=0);if(alive.length<this.players.length){this.over=true;this.winner=alive.length===1?alive[0]:-1}}
  checkRace(){const p=this.players[0];if(this.finish[0]==null&&p.alive&&p.lines>=this.goal){this.finish[0]=this.elapsed;p.done=true;p.ev("完成！")}
    if(!p.alive||this.finish[0]!=null){this.over=true;this.success=this.finish[0]!=null}}
}

