/* taco 方塊對戰：聲音：Web Audio 合成的音效、背景音樂、音樂檔。
   所有檔案依 index.html 的順序載入，共用同一個全域範圍。 */
"use strict";
/* ================= 聲音（Web Audio 即時合成） ================= */
const audio={ctx:null,muted:false,timer:null,step:0,paused:false,wantMusic:false,
  init(){if(this.ctx)return;try{this.ctx=new (window.AudioContext||window.webkitAudioContext)();this.master=this.ctx.createGain();this.master.gain.value=.5;this.master.connect(this.ctx.destination)}catch(e){this.ctx=null}
    if(this.ctx&&this.wantLobby)this.lobbyMusic()},   // 瀏覽器要等使用者點一下才能出聲：大廳音樂等到這裡才開始
  tone(f,d,vol=.2,type="square",f2=null,when=0){if(!this.ctx||this.muted)return;const t=this.ctx.currentTime+when,o=this.ctx.createOscillator(),g=this.ctx.createGain();
    o.type=type;o.frequency.setValueAtTime(f,t);if(f2)o.frequency.exponentialRampToValueAtTime(f2,t+d);g.gain.setValueAtTime(vol,t);g.gain.exponentialRampToValueAtTime(.001,t+d);o.connect(g);g.connect(this.master);o.start(t);o.stop(t+d+.02)},
  play(n){if(!settings.sfx)return;const T=this.tone.bind(this);
    ({move:()=>T(330,.03,.06),rotate:()=>T(520,.04,.07,"triangle"),hold:()=>T(440,.08,.1,"triangle",660),drop:()=>T(180,.08,.15,"square",90),lock:()=>T(140,.05,.1),
      clear1:()=>T(660,.12,.15),clear2:()=>{T(660,.1,.15);T(880,.12,.15,"square",null,.08)},clear3:()=>{T(660,.08,.15);T(880,.08,.15,"square",null,.07);T(990,.14,.15,"square",null,.14)},
      clear4:()=>[523,659,784,1047].forEach((f,i)=>T(f,.14,.16,"square",null,i*.07)),tspin:()=>T(300,.25,.18,"sawtooth",900),perfect:()=>[523,659,784,1047,1319].forEach((f,i)=>T(f,.2,.15,"triangle",null,i*.06)),
      warn:()=>T(220,.15,.12,"sawtooth",160),shot:()=>T(900,.18,.08,"sawtooth",300),hit:()=>T(120,.2,.2,"square",60),
      ko:()=>{T(880,.1,.2);T(1320,.25,.2,"square",null,.1)},dead:()=>T(400,.6,.2,"sawtooth",60),win:()=>[523,659,784,1047].forEach((f,i)=>T(f,.25,.15,"triangle",null,i*.12)),
      count:()=>T(660,.12,.15),go:()=>T(1046,.3,.18)}[n]||(()=>{}))()},
  /* 背景音樂：Korobeiniki 旋律（俄羅斯民謠，公有領域），自己編的電子舞曲伴奏：
     大鼓四拍、2/4 拍手、反拍 Hi-hat、八分音符貝斯、十六分音符琶音；用排程器精準對拍 */
  melody:"E5 4 B4 2 C5 2 D5 4 C5 2 B4 2 A4 4 A4 2 C5 2 E5 4 D5 2 C5 2 B4 6 C5 2 D5 4 E5 4 C5 4 A4 4 A4 8 . 2 D5 4 F5 2 A5 4 G5 2 F5 2 E5 6 C5 2 E5 4 D5 2 C5 2 B4 4 B4 2 C5 2 D5 4 E5 4 C5 4 A4 4 A4 8",
  chords:[["A",[0,3,7]],["E",[0,4,7]],["A",[0,3,7]],["A",[0,3,7]],["D",[0,3,7]],["A",[0,3,7]],["E",[0,4,7]],["A",[0,3,7]]],  // 每小節一個和弦
  seq:null,
  freq(n){if(n===".")return 0;const m={C:0,D:2,E:4,F:5,G:7,A:9,B:11}[n[0]],o=+n.slice(-1);return 440*Math.pow(2,(m+12*(o-4)-9)/12)},
  root(name,oct){return 440*Math.pow(2,(({C:0,D:2,E:4,F:5,G:7,A:9,B:11}[name])+12*(oct-4)-9)/12)},
  score(text){const t=text.split(" ");let step=0;const seq={};for(let i=0;i<t.length;i+=2){const len=+t[i+1];if(t[i]!==".")seq[step]=[this.freq(t[i]),len];step+=len}return [seq,step]},
  build(){[this.seq,this.loopLen]=this.score(this.melody)},
  noise(){if(!this._noise){const b=this.ctx.createBuffer(1,this.ctx.sampleRate*.5,this.ctx.sampleRate),d=b.getChannelData(0);for(let i=0;i<d.length;i++)d[i]=Math.random()*2-1;this._noise=b}return this._noise},
  out(){if(!this.bus){this.bus=this.ctx.createGain();this.bus.gain.value=.55;this.bus.connect(this.master);
      this.duck=this.ctx.createGain();this.duck.connect(this.bus)}return this.bus},
  kick(t){const o=this.ctx.createOscillator(),g=this.ctx.createGain();o.frequency.setValueAtTime(150,t);o.frequency.exponentialRampToValueAtTime(42,t+.12);
    g.gain.setValueAtTime(.9,t);g.gain.exponentialRampToValueAtTime(.001,t+.28);o.connect(g);g.connect(this.out());o.start(t);o.stop(t+.3);
    const d=this.duck.gain;d.cancelScheduledValues(t);d.setValueAtTime(.25,t);d.linearRampToValueAtTime(1,t+.18)},   // 側鏈：大鼓一下，伴奏縮一下
  hiss(t,dur,vol,hp,bp){const s=this.ctx.createBufferSource(),f=this.ctx.createBiquadFilter(),g=this.ctx.createGain();s.buffer=this.noise();
    f.type=bp?"bandpass":"highpass";f.frequency.value=hp;g.gain.setValueAtTime(vol,t);g.gain.exponentialRampToValueAtTime(.001,t+dur);s.connect(f);f.connect(g);g.connect(this.out());s.start(t);s.stop(t+dur+.02)},
  synth(f,t,dur,vol,type,cut,dest,detune=0){const o=this.ctx.createOscillator(),fl=this.ctx.createBiquadFilter(),g=this.ctx.createGain();o.type=type;o.frequency.value=f;o.detune.value=detune;
    fl.type="lowpass";fl.frequency.setValueAtTime(cut,t);fl.Q.value=6;g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(vol,t+.008);g.gain.exponentialRampToValueAtTime(.001,t+dur);
    o.connect(fl);fl.connect(g);g.connect(dest);o.start(t);o.stop(t+dur+.03)},
  edmStep(st,t,u){const bar=Math.floor(st/16)%8,b=st%16,[cn,iv]=this.chords[bar],r=this.root(cn,2);
    if(b%4===0)this.kick(t);
    if(b===4||b===12){this.hiss(t,.18,.35,1400,true);this.hiss(t+.01,.12,.2,3000)}       // 拍手
    if(b%2===1)this.hiss(t,.04,.12,8000);if(b%4===2)this.hiss(t,.14,.08,7000);           // Hi-hat
    if(b%2===0)this.synth(b%4===0?r:r*2,t,u*1.8,.28,"sawtooth",700,this.duck);           // 貝斯
    const arp=iv.concat([12]);this.synth(this.root(cn,4)*Math.pow(2,arp[b%arp.length]/12),t,u*.9,.045,"square",2600,this.duck);  // 琶音
    if(b===0)iv.forEach(x=>this.synth(this.root(cn,3)*Math.pow(2,x/12),t,u*15,.035,"sawtooth",1200,this.duck,7));               // 鋪底和弦
    if(st%128===120)for(let k=0;k<8;k++)this.hiss(t+k*u,u,.05+k*.02,2000+k*800,true);    // 每 8 小節一次上升音效
    const m=this.seq[st%this.loopLen];if(m){const d=m[1]*u*.95;this.synth(m[0],t,d,.11,"square",3200,this.out());this.synth(m[0],t,d,.06,"sawtooth",2400,this.out(),9);this.synth(m[0]*2,t,d*.6,.025,"triangle",5000,this.out())}},
  chipStep(st,t,u){const m=this.seq[st%this.loopLen];if(m){const d=m[1]*u*.9;this.synth(m[0],t,d,.09,"square",6000,this.out());if(st%2===0)this.synth(m[0]/2,t,d,.07,"triangle",6000,this.out())}},
  /* 大廳音樂（主選單、設定、線上房間）：Korobeiniki（俄羅斯民謠，公有領域）的 Lo-fi 爵士改編，自己編的伴奏。
     88 拍、反拍搖擺；每半小節一個爵士和弦（Am9、E7♭9、Dm9、Cmaj9），電鋼琴和弦、木琴／鐘聲旋律、
     柔和大鼓與邊擊、沙鈴、黑膠雜音；第二輪旋律多一層低八度的電鋼琴 */
  lobbyBpm:88,lobbyBusy:false,   // 大廳音樂的速度；Busy＝鼓和沙鈴打兩倍密
  lobbyChords:(()=>{const Am=["A",[0,3,7,10,14]],E7=["E",[0,4,7,10,13]],Dm=["D",[0,3,7,10,14]],C=["C",[0,4,7,11,14]];
    return [Am,E7, Am,Am, E7,E7, Am,Am, Dm,Dm, C,Am, E7,E7, Am,Am]})(),   // 每半小節（8 步）一個
  softKick(t){const o=this.ctx.createOscillator(),g=this.ctx.createGain();o.frequency.setValueAtTime(110,t);o.frequency.exponentialRampToValueAtTime(45,t+.1);
    g.gain.setValueAtTime(.7,t);g.gain.exponentialRampToValueAtTime(.001,t+.22);o.connect(g);g.connect(this.out());o.start(t);o.stop(t+.25);
    const d=this.duck.gain;d.cancelScheduledValues(t);d.setValueAtTime(.6,t);d.linearRampToValueAtTime(1,t+.2)},
  ep(f,t,dur,vol){this.synth(f,t,dur,vol,"sine",2200,this.duck);this.synth(f*2,t,dur*.4,vol*.25,"triangle",3500,this.duck,4)},   // 電鋼琴：正弦波＋一點泛音
  lobbyStep(st,t,u){const half=Math.floor(st/8)%16,b=st%16,h=st%8,[cn,iv]=this.lobbyChords[half],r=this.root(cn,2),sw=b%4===2?u*.33:0,T=t+sw;
    // 鼓：大鼓在 1 和 3 拍後半（Lo-fi 常見的「咚—咚」），邊擊在 2、4 拍；沙鈴每個八分音符，反拍往後拖
    if(b===0||b===10||(this.lobbyBusy&&(b===7||b===14)))this.softKick(T);
    if(b===4||b===12)this.hiss(t,.07,.1,2400,true);
    if(this.lobbyBusy&&(b===15||b===9))this.hiss(t,.04,.04,2400,true);                      // 鬼音小鼓
    if(this.lobbyBusy)this.hiss(T,.03,b%4===0?.05:b%2===0?.035:.022,7500);                 // 十六分音符沙鈴
    else if(b%2===0)this.hiss(T,.035,b%4===0?.05:.035,7000);
    if(Math.random()<.12)this.hiss(t+Math.random()*u,.012,.025,3000,true);              // 黑膠雜音
    // 貝斯：每半小節根音＋五度
    if(h===0)this.synth(r,t,u*5,.32,"triangle",380,this.duck);
    if(h===6)this.synth(r*1.5,T,u*1.8,.2,"triangle",380,this.duck);
    // 電鋼琴：半小節開頭一下長的，第 6 步一下短的切分
    const v=iv.map(x=>this.root(cn,3)*Math.pow(2,x/12));
    if(h===0)v.forEach(f=>this.ep(f,t,u*7,.03));
    if(h===6&&half%2===1)v.slice(1).forEach(f=>this.ep(f,T,u*2,.022));
    // 旋律：木琴／鐘聲音色，跟著反拍搖擺；第二輪多一層低八度電鋼琴
    const m=this.seq[st%this.loopLen];if(m){const d=Math.min(m[1]*u*.95,u*6);
      this.synth(m[0],T,d,.11,"sine",5000,this.out());this.synth(m[0]*2,T,d*.3,.03,"triangle",6000,this.out());
      if(Math.floor(st/this.loopLen)%2===1)this.ep(m[0]/2,T,m[1]*u*.9,.05)}},
  /* 音樂檔：用 <audio> 循環播放，暫停、靜音時停住，回來從原處繼續 */
  startTrack(name){const t=TRACKS[name];if(!this.els)this.els={};let el=this.els[name];
    if(!el){el=new Audio(t.file);el.loop=true;el.preload="auto";el.volume=.45;this.els[name]=el}
    this.el=el;el.currentTime=0;this.nowPlaying=name;
    this.timer=setInterval(()=>{const stop=this.paused||this.muted||!settings.music||!this.wantMusic;if(stop&&!el.paused)el.pause();else if(!stop&&el.paused)el.play().catch(()=>{})},150)},
  startMusic(lobby){this.wantMusic=true;this.kind=lobby?"lobby":"game";if(!this.ctx||this.timer||!settings.music)return;
    if(lobby){this.nowPlaying=null;if(!this.seq)this.build();const u=60/this.lobbyBpm/4;this.nextT=this.ctx.currentTime+.08;this.pos=0;
      this.timer=setInterval(()=>{if(!this.wantMusic)return;const now=this.ctx.currentTime;
        if(this.muted||!settings.music){this.nextT=now+.08;return}
        while(this.nextT<now+.12){this.lobbyStep(this.pos,this.nextT,u);this.pos++;this.nextT+=u}},25);return}
    let st=settings.style;if(st==="隨機"){const k=Object.keys(TRACKS);st=k[Math.floor(Math.random()*k.length)]}
    if(TRACKS[st]){this.startTrack(st);return}
    this.nowPlaying=null;if(!this.seq)this.build();
    const bpm=settings.style==="EDM"?148:136,u=60/bpm/4;this.nextT=this.ctx.currentTime+.08;this.pos=this.pos||0;
    this.timer=setInterval(()=>{if(!this.wantMusic)return;const now=this.ctx.currentTime;
      if(this.paused||this.muted||!settings.music){this.nextT=now+.08;return}
      while(this.nextT<now+.12){(settings.style==="EDM"?this.edmStep:this.chipStep).call(this,this.pos,this.nextT,u);this.pos++;this.nextT+=u}},25)},
  stopMusic(){this.wantMusic=false;this.wantLobby=false;this.kind=null;clearInterval(this.timer);this.timer=null;this.pos=0;if(this.el){this.el.pause();this.el=null}},
  refresh(){const lobby=this.kind==="lobby";if(this.timer&&this.wantMusic){const p=this.pos;this.stopMusic();if(lobby)this.lobbyMusic();else{this.startMusic();this.pos=p}}else if(settings.music&&this.wantMusic&&!this.timer)lobby?this.lobbyMusic():this.startMusic()},
  /* 換到大廳音樂（已經在放就不重來）；還不能出聲時先記著，第一次點畫面再開始 */
  lobbyMusic(){this.paused=false;if(this.kind==="lobby"&&this.timer)return;this.stopMusic();this.wantLobby=true;if(!this.ctx)return;this.startMusic(true)}};
// 第一次點畫面或按鍵就啟動聲音（大廳音樂才會開始）
addEventListener("pointerdown",()=>audio.init());
// App 切到背景時整個聲音暫停，回來再繼續
document.addEventListener("visibilitychange",()=>{if(!audio.ctx)return;if(document.hidden)audio.ctx.suspend().catch(()=>{});else audio.ctx.resume().catch(()=>{})});

