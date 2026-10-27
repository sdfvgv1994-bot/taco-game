/* taco 方塊對戰：線上對戰：PeerJS 點對點連線（不用登入），房號、互傳狀態、垃圾行。
   所有檔案依 index.html 的順序載入，共用同一個全域範圍。 */
"use strict";
/* ================= 線上對戰：用 room 的「presence」互傳自己的狀態 =================
   每個人只模擬自己的板子，把畫面（板子、分數、送出的總攻擊行數…）放在自己的 presence；
   對手的「送出總行數」變多了，多出來的就是打過來的垃圾行。房主決定模式和開始時間；方塊順序兩邊各自隨機（presence 裡的 seed 只留給舊版用）。 */
const NET={api:null,room:null,code:null,host:false,opp:null,round:0,seen:0,sent:0,startAt:0,modeKey:1,lastPub:0,evn:0,unsub:null,
  nick:(()=>{try{return localStorage.getItem("taco-blocks-nick")||""}catch(e){return""}})()};

/* PeerJS 版連線：不用登入，房主用「taco-blocks-房號」當自己的代號，朋友直接連過去。
   做成跟 room 一樣的樣子（join / onPeers / presence / leave），下面的對戰程式完全不用改。 */
const PEER_PREFIX="taco-blocks-v1-";
const PEER_BEAT=2000,PEER_TIMEOUT=15000;   // 心跳間隔、多久沒聲音算離開（毫秒）
const peerApi={join:(name,host)=>new Promise((res,rej)=>{
  const id=PEER_PREFIX+name;let peer;
  try{peer=host?new Peer(id,{debug:0}):new Peer({debug:0})}catch(e){rej({code:"no_peer"});return}
  let conn=null,theirs=null,mine=null,peersFn=null,discFn=null,done=false,closed=false,lastSeen=0,hb=null;
  const emit=()=>{if(peersFn)peersFn({peers:conn&&conn.open&&theirs?[{peer:conn.peer,presence:theirs,sameTab:false}]:[]})};
  // 對方不見了（說了再見、連線關閉、或太久沒聲音）：當成離開
  const lost=c=>{if(conn!==c)return;conn=null;theirs=null;try{c.close()}catch(e){}emit();if(!host&&!closed&&discFn&&state==="room")discFn()};
  // 心跳：手機上對方關掉時連線常常不會通知，所以每 PEER_BEAT 毫秒把自己的 presence 再送一次，
  // 超過 PEER_TIMEOUT 毫秒都沒收到對方任何東西，就當成對方離開（暫停中也照樣在送，不會誤判）
  const beat=()=>{if(!conn||!conn.open)return;if(mine)try{conn.send(mine)}catch(e){}if(Date.now()-lastSeen>PEER_TIMEOUT)lost(conn)};
  const wire=c=>{if(host&&conn&&conn.open){c.on("open",()=>c.close());return}
    conn=c;theirs=null;lastSeen=Date.now();
    c.on("open",()=>{lastSeen=Date.now();if(mine)try{c.send(mine)}catch(e){}emit()});
    c.on("data",d=>{lastSeen=Date.now();if(!d||typeof d!=="object")return;if(d.bye){lost(c);return}theirs=d;emit()});
    c.on("close",()=>lost(c));
    c.on("error",()=>{})};
  hb=setInterval(beat,PEER_BEAT);
  const room={onPeers(fn,onDisc){peersFn=fn;discFn=onDisc||null;emit();return()=>{peersFn=null;discFn=null}},
    presence(p){mine=p;if(conn&&conn.open)try{conn.send(p)}catch(e){}return Promise.resolve()},
    leave(){closed=true;clearInterval(hb);if(conn&&conn.open)try{conn.send({bye:true})}catch(e){}   // 先說再見，對方馬上知道
      setTimeout(()=>{try{peer.destroy()}catch(e){}},200);return Promise.resolve()}};
  const fail=code=>{if(done)return;done=true;closed=true;clearInterval(hb);try{peer.destroy()}catch(e){}rej({code})};
  const timer=setTimeout(()=>fail("timeout"),12000);
  peer.on("open",()=>{if(host){done=true;clearTimeout(timer);res(room);return}
    const c=peer.connect(id,{reliable:true,serialization:"json"});wire(c);
    c.on("open",()=>{if(!done){done=true;clearTimeout(timer);res(room)}})});
  if(host)peer.on("connection",wire);
  peer.on("error",e=>{if(!done){clearTimeout(timer);fail(e&&e.type)}});
  peer.on("disconnected",()=>{if(!closed)try{peer.reconnect()}catch(e){}});
})};
if(window.Peer)NET.api=peerApi;
(async()=>{if(NET.api)return;try{if(window.claude&&claude.use)NET.api=await claude.use("room")}catch(e){NET.api=null}if(state==="online")showOnline()})();
const esc=t=>String(t??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const oppName=()=>NET.opp?String(NET.opp.presence.nick||"對手").slice(0,12):"對手";
function showOnline(msg=""){state="online";audio.lobbyMusic();
  if(!NET.api){showPanel(`<div class="card"><h2>線上對戰</h2><p>連線元件載入不了，請確認有網路後重新整理頁面再試一次。</p><div class="row-btns"><button type="button" data-act="menu">← 返回主選單</button></div></div>`);return}
  showPanel(`<div class="card"><h2>線上對戰</h2><p>你建立房間會拿到一組房號，朋友在他的手機或電腦打開這個遊戲，輸入同一組房號就能對打。</p>
    <label class="hint" for="net-nick" style="text-align:left">你的暱稱</label><div class="field"><input id="net-nick" maxlength="12" value="${esc(NET.nick)}" placeholder="例如：taco"></div>
    <ul class="menu">${kbtn("1","建立房間","你當房主，選模式、按開始","net-create")}</ul>
    <label class="hint" for="net-code" style="text-align:left">或輸入朋友的房號加入</label>
    <div class="field"><input id="net-code" inputmode="numeric" maxlength="4" placeholder="4 位數"><button type="button" data-act="net-join">加入</button></div>
    ${msg?`<p style="color:var(--amber)">${esc(msg)}</p>`:""}
    <div class="row-btns"><button type="button" data-act="menu">← 返回主選單</button></div>
    <p class="hint">不用登入：把這個網址傳給朋友，輸入同一組房號就好。暫停時兩邊會一起停。少數公司或學校網路可能連不上，換手機網路試試。</p></div>`);
  const nk=document.getElementById("net-nick");if(nk)nk.addEventListener("input",()=>{NET.nick=nk.value.trim();try{localStorage.setItem("taco-blocks-nick",NET.nick)}catch(e){}})}
function myNick(){return(NET.nick||"玩家").slice(0,12)}
async function netEnter(code,host,quiet){try{NET.room=await NET.api.join("taco-"+code,host)}catch(e){const c=e&&e.code;if(quiet&&c==="unavailable-id")return"taken";
    showOnline(c==="limit_reached"?"房間太多了，等一下再試":c==="peer-unavailable"?"找不到這個房號，確認朋友的房間還開著":c==="timeout"?"連線逾時，請再試一次":"連不上房間，請再試一次");return false}
  Object.assign(NET,{code,host,opp:null,round:0,seen:0,sent:0});
  NET.unsub=NET.room.onPeers(ch=>{const others=ch.peers.filter(p=>!p.sameTab);
      const keep=others.find(p=>NET.opp&&p.peer===NET.opp.peer)||others.find(p=>p.presence.role===(host?"guest":"host"))||null;
      const gone=NET.opp&&!keep,inMatch=state==="play"&&match&&match.net;NET.opp=keep;
      if(gone&&inMatch&&!match.over){netFinish(0,"對手離開了房間");return}            // 打到一半：你贏
      if(gone&&!host&&(state==="room"||inMatch)){netLeave();showOnline("房主離開了房間");return}   // 房間、結算畫面：沒有房主就退出
      if(gone&&host&&inMatch){showRoom();return}                                        // 房主看完結算：回房間等下一個朋友
      if(!host&&keep)netGuestCheck();if(state==="room")showRoom();if(state==="play"&&match&&match.net)netPauseCheck()},
    ()=>{if(state==="room"||(state==="play"&&match&&match.net)){netLeave();showOnline("連線中斷了")}});
  netPublish(true);return true}
async function netCreate(){audio.init();showPanel(`<div class="card"><h2>線上對戰</h2><p>建立房間中…</p></div>`);
  for(let i=0;i<5;i++){const code=String(1000+Math.floor(Math.random()*9000));const r=await netEnter(code,true,i<4);if(r==="taken")continue;if(r)showRoom();return}}
async function netJoin(){audio.init();const v=(document.getElementById("net-code")?.value||"").replace(/\D/g,"");if(v.length!==4){showOnline("房號是 4 位數字");return}
  showPanel(`<div class="card"><h2>線上對戰</h2><p>連線到房間 ${esc(v)}…</p></div>`);
  if(await netEnter(v,false))showRoom()}
function netLeave(){if(NET.unsub){NET.unsub();NET.unsub=null}if(NET.room){NET.room.leave().catch(()=>{});NET.room=null}NET.opp=null;NET.code=null;if(match&&match.net)match=null}
function showRoom(){state="room";if(match&&match.net&&!match.over)return;audio.lobbyMusic();
  const opp=NET.opp?`<span class="dot on"></span>${esc(oppName())} 已加入`:`<span class="dot"></span>等朋友加入…`;
  const modes=MODES.filter(m=>m.cfg.vs).map(m=>kbtn(m.key,m.title,m.desc,"net-mode"+m.key)).join("");
  showPanel(`<div class="card"><h2>房間</h2><div class="code">${esc(NET.code)}</div><p style="text-align:center">把這組房號告訴朋友<br>你是 ${esc(myNick())}${NET.host?"（房主）":""}</p>
    <p style="text-align:center">${opp}</p>
    ${NET.opp&&NET.opp.presence.ver!==APP_VERSION?`<p style="color:var(--amber);text-align:center">⚠ 你和對手的遊戲版本不同，可能會不同步。請兩邊都回主選單更新（或把 App 關掉重開）</p>`:""}
    ${NET.host?(NET.opp?`<p>選一個模式就開始：</p><ul class="menu">${modes}</ul>`:""):`<p class="hint">等房主選模式開始…</p>`}
    <div class="row-btns"><button type="button" data-act="net-leave">離開房間</button></div></div>`)}
function netHostStart(key){if(!NET.host||!NET.opp)return;const m=MODES.find(x=>x.key===key&&x.cfg.vs);if(!m)return;
  NET.round++;NET.modeKey=key;const seed=Math.floor(Math.random()*2**30),startAt=Date.now()+3500;
  NET.game={round:NET.round,seed,mode:key,startAt};netBegin(NET.game);netPublish(true)}
function netGuestCheck(){const g=NET.opp&&NET.opp.presence.game;if(!g||!(g.round>NET.round))return;
  if(Date.now()-g.startAt>8000)return;   // 錯過太久的局就不追了，等下一局
  NET.round=g.round;NET.modeKey=g.mode;netBegin(g)}
function netBegin(g){const m=MODES.find(x=>x.key===g.mode);cfg=m.cfg;diff="net";state="play";paused=false;scored=false;note="";settle=0;lastWarn=0;
  match=new Match(2,cfg.kind,cfg.time||null);match.net=true;   // 不帶 seed：自己的方塊順序自己抽
  match.startAt=g.startAt;ais={};
  const r=match.players[1];r.remote=true;r.queue=[];
  names=[myNick(),oppName()];NET.seen=0;NET.sent=0;NET.evn=0;NET.lastEv="";NET.pz={round:NET.round,seq:0,on:false,t:0,by:""};NET.pzKey="";NET.pausedAt=0;NET.resuming=false;
  countdown=Math.max(.5,(g.startAt-Date.now())/1000);lastBeep=0;audio.stopMusic();audio.paused=false;for(const k in held)delete held[k];hidePanel()}
/* 把對手 presence 裡的狀態套到畫面上的第 2 位玩家；多出來的送出行數 = 打過來的垃圾 */
function netApplyRemote(m){const o=NET.opp,s=o&&o.presence.st;if(!s||s.round!==NET.round)return;const r=m.players[1],me=m.players[0];
  if(typeof s.grid==="string"&&s.grid.length===COLS*ROWS)r.grid=Array.from({length:ROWS},(_,y)=>Array.from({length:COLS},(_,x)=>{const c=s.grid[y*COLS+x];return COLORS[c]?c:null}));
  r.score=+s.score||0;r.lines=+s.lines||0;r.sent=+s.sent||0;r.deaths=+s.deaths||0;r.alive=s.alive!==false;r.done=!!s.done;
  r.hold=COLORS[s.hold]?s.hold:null;r.queue=String(s.next||"").split("").filter(k=>SHAPES[k]).slice(0,5);r.pending=s.pend?[+s.pend]:[];
  r.maxCombo=+s.combo||0;r.tetrises=+s.tet||0;r.tspins=+s.ts||0;r.pieces=+s.pc||0;r.received=+s.recv||0;r.book=s.book&&typeof s.book==="object"?s.book:{};
  if(s.evn!==r._evn){r._evn=s.evn;if(s.ev){r.event=String(s.ev).slice(0,20);r.eventAge=0}}
  me.ko=r.deaths;r.ko=me.deaths;
  if(m.attacks&&r.sent>NET.seen){const d=r.sent-NET.seen;NET.seen=r.sent;me.receive(d,1);m.shots.push({from:1,to:0,n:d,age:0})}
  r._h=+s.h||0;r._over=!!s.over}
function netAfterLocal(m){const me=m.players[0],o=me.outbox;me.outbox=0;me.sent=NET.sent+o;if(o&&m.attacks){NET.sent+=o;m.shots.push({from:0,to:1,n:o,age:0})}}
function netUpdate(m,dt){const me=m.players[0],r=m.players[1];
  if(m.ending){netApplyRemote(m);netPublish(false,true);if(r._over||Date.now()-m.ending>1500){netApplyRemote(m);m.end(m.sortBy())}return}
  m.elapsed=Math.max(0,(Date.now()-m.startAt)/1000);
  netApplyRemote(m);me.update(dt);r.eventAge+=dt;r.glow+=dt;r.shake=Math.max(0,r.shake-dt);netAfterLocal(m);
  if(["battle","attack"].includes(m.mode)&&!me.alive){me.deaths++;me.ev("被擊倒");me.revive()}
  me.ko=r.deaths;r.ko=me.deaths;
  if(m.mode==="survival"){if(!me.alive)return netFinish(1);if(!r.alive)return netFinish(0)}
  if(m.mode==="attack"&&(me.sent>=ATTACK_GOAL||r.sent>=ATTACK_GOAL))return netFinish(null);
  if(m.mode==="score"&&!me.alive&&!r.alive)return netFinish(null);
  if(m.timeUp())netFinish(null);
  netPublish(false)}
function netFinish(winner,why){const m=match;if(!m||m.over||m.ending)return;if(paused){paused=false;audio.paused=false;hidePanel()}
  if(winner==null){m.ending=Date.now();netPublish(true,true)}else{netPublish(true,true);m.over=true;m.winner=winner}
  if(why)note=why}
function netPublish(force,over){if(!NET.room)return;const now=performance.now();if(!force&&now-NET.lastPub<60)return;NET.lastPub=now;
  const pres={nick:myNick(),role:NET.host?"host":"guest",game:NET.host?NET.game||null:null,st:null,ver:APP_VERSION,pz:NET.pz||null};
  if(match&&match.net){const me=match.players[0];const g=me.grid.map(r=>r.slice());if(me.active)for(const [x,y] of me.cells())if(y>=0&&y<ROWS)g[y][x]=me.kind;
    if(me.event!==NET.lastEv){NET.lastEv=me.event;NET.evn++}
    pres.st={round:NET.round,grid:g.map(r=>r.map(c=>c||".").join("")).join(""),score:me.score,lines:me.lines,sent:NET.sent,deaths:me.deaths,alive:me.alive,done:me.done,
      hold:me.hold||"",next:me.queue.slice(0,5).join(""),pend:me.pending.reduce((a,b)=>a+b,0),combo:Math.max(0,me.maxCombo),tet:me.tetrises,ts:me.tspins,pc:me.pieces,recv:me.received,
      book:me.book,h:me.height(),ev:me.eventAge<1.5?me.event:"",evn:NET.evn,over:!!(over||match.over||match.ending)}}
  NET.room.presence(pres).catch(()=>{})}


/* ================= 線上暫停：兩邊一起停、一起繼續 =================
   各自把最後一次的暫停／繼續指令（第幾局、第幾次、開或關、送出的時間）放在 presence 的 pz；
   兩邊都取「時間最晚」的那一個指令，所以畫面一定一致。繼續時兩邊都從指令時間起倒數 3 秒，
   計時器（match.startAt）往後挪「暫停的那段時間＋3 秒」，剩餘時間兩邊一樣。 */
function netPzList(){const o=NET.opp&&NET.opp.presence.pz;
  return [NET.pz,o].filter(p=>p&&p.round===NET.round&&p.seq>0&&typeof p.t==="number")}
function netSetPause(v){const m=match;if(!m||!m.net||m.over||m.ending)return false;
  if(v&&(paused||countdown>0))return false;if(!v&&!paused)return false;
  if(!(NET.opp&&NET.opp.presence.ver)){m.players[0].ev("對手是舊版，不能暫停");return false}   // 舊版不認得暫停指令
  NET.pz={round:NET.round,seq:(NET.pz&&NET.pz.round===NET.round?NET.pz.seq:0)+1,on:v,t:Date.now(),by:myNick()};
  netPublish(true);netPauseCheck();return true}
function netPauseCheck(){const m=match;if(!m||!m.net||m.over||m.ending)return;
  const list=netPzList();if(!list.length)return;
  const hostPz=NET.host?NET.pz:NET.opp&&NET.opp.presence.pz;   // 同一毫秒兩邊都按：聽房主的
  const c=list.reduce((a,b)=>b.t>a.t||(b.t===a.t&&b===hostPz)?b:a);
  const key=`${c.on}:${c.t}`;if(key===NET.pzKey)return;NET.pzKey=key;
  if(c.on){if(!paused){paused=true;audio.paused=true;NET.pausedAt=c.t;for(const k in held)delete held[k];m.players[0].soft=false}
    showNetPause(c===NET.pz?"你":c.by,c!==NET.pz)}
  else if(paused){const resumeAt=c.t+3000;m.startAt+=resumeAt-NET.pausedAt;
    paused=false;NET.resuming=true;countdown=Math.max(.3,(resumeAt-Date.now())/1000);lastBeep=0;hidePanel()}}
function showNetPause(by,guard){showPanel(`<div class="card"><div class="big">PAUSE</div><p style="text-align:center">${by==="你"?"你":esc(by)+" "}暫停了，兩邊都停住</p>
  <ul class="menu">${kbtn("Esc","繼續","兩邊一起倒數 3 秒，也可以按 P","resume")}${kbtn("⌫","離開房間","會算你棄權","net-leave")}</ul></div>`,guard)}
