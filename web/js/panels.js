/* taco 方塊對戰：面板：選單、設定、按鍵設定、暫停、結算。
   所有檔案依 index.html 的順序載入，共用同一個全域範圍。 */
"use strict";
/* ================= 面板（選單、設定、按鍵、暫停、結算） ================= */
function hidePanel(){panel.hidden=true;panel.innerHTML="";document.body.classList.remove("menu-open")}
/* 自己跳出來的面板（結算、對手按的暫停）：剛出現的一下子不接受點擊，免得還在連按觸控鍵時誤按到「離開房間」 */
let panelGuard=0;
function showPanel(html,guard){panel.innerHTML=html;panelGuard=guard?performance.now()+800:0;panel.hidden=false;document.body.classList.add("menu-open");const b=panel.querySelector("button");if(b)b.focus({preventScroll:true})}
const kbtn=(k,t,sub,act,val)=>`<li><button type="button" class="${val!=null?"setting":""}" data-act="${act}"><span class="k">${k}</span><span class="t">${t}${sub?`<small>${sub}</small>`:""}</span>${val!=null?`<span class="val">${val}</span>`:""}</button></li>`;
const keyLine=i=>{const m=keys[i];return`${keyName(m.left)} ${keyName(m.right)} 移動　${keyName(m.down)} 軟降　${keyName(m.cw)} 順轉　${keyName(m.ccw)} 逆轉　${keyName(m.drop)} 硬降　${keyName(m.hold)} 暫存`};
function showMenu(){state="menu";match=null;paused=false;audio.stopMusic();
  const extra={5:records.sprint!=null?`　最佳 ${fmt(records.sprint)}`:"",6:records.marathon!=null?`　最佳 ${records.marathon} 行`:"",2:records.score!=null?`　最高 ${records.score.toLocaleString()} 分`:""};
  showPanel(`<div class="card">${typeof PWA!=="undefined"&&PWA.hasUpdate()?`<div class="row-btns"><button type="button" class="update" data-act="update">🆕 有新版本，點一下更新</button></div>`:""}<h2>選擇模式</h2><ul class="menu">${MODES.map(m=>kbtn(m.key,m.title,m.desc+(extra[m.key]||""),"mode"+m.key)).join("")}
    ${kbtn(7,"線上對戰","建立房間或輸入房號，和朋友用各自的手機對打","online")}
    ${kbtn(0,"設定","音效、落點預覽、移動速度、自訂按鍵","settings")}</ul>
    ${typeof PWA!=="undefined"&&PWA.canInstall()?`<div class="row-btns"><button type="button" data-act="install">📲 安裝到桌面</button></div>`:""}
    <p class="hint">數字鍵選擇（上排或數字鍵盤都可以）<br>玩家 1：${keyLine(0)}<br>玩家 2：${keyLine(1)}<br>對電腦或單人時兩組按鍵都能用　Esc / P 暫停　M 靜音</p></div>`)}
function showDiff(c){state="diff";cfg=c;showPanel(`<div class="card"><h2>${MODES.find(m=>m.cfg===c).title}：選對手</h2><ul class="menu">${Object.keys(DIFFICULTY).map((d,i)=>kbtn(i+1,`對電腦（${d}）`,`電腦每 ${DIFFICULTY[d]} 秒動一次`,"diff"+(i+1))).join("")}${kbtn(4,"雙人同機","同一台鍵盤，玩家 1 對玩家 2","diff4")}</ul><div class="row-btns"><button type="button" data-act="menu">← 返回主選單</button></div><p class="hint">Esc / Backspace 也可以返回</p></div>`)}
function showSettings(){state="settings";showPanel(`<div class="card"><h2>設定</h2><ul class="menu">${ITEMS.map(([k,t],i)=>kbtn(i+1,t,k==="style"?(TRACKS[settings.style]?`by ${TRACKS[settings.style].by}（Pixabay）`:settings.style==="隨機"?"每局從四首音樂檔裡挑一首":"程式即時合成"):"","set"+k,label(k))).join("")}${kbtn(ITEMS.length+1,"按鍵設定","自己按鍵盤決定每個動作用哪個鍵","keys")}</ul><div class="row-btns"><button type="button" data-act="menu">← 返回主選單</button></div><p class="hint">按數字或點一下切換，自動存在這個瀏覽器　Esc / Backspace 也可以返回<br>音樂檔來自 Pixabay：${Object.entries(TRACKS).map(([n,t])=>`${n}（${t.by}）`).join("、")}</p></div>`)}
function showKeys(msg=""){state="keys";const cell=(i,a)=>`<button type="button" data-key="${i}:${a}" class="${waitKey&&waitKey[0]===i&&waitKey[1]===a?"wait":""}">${waitKey&&waitKey[0]===i&&waitKey[1]===a?"請按鍵…":keyName(keys[i][a])}</button>`;
  showPanel(`<div class="card"><h2>按鍵設定</h2><p>點一下要改的按鍵，再按鍵盤上想用的鍵（按 Esc 取消）。同一個鍵已經被別的動作用了，兩個會互換。</p>
    <div class="scroll"><div class="keymap"><span></span><span class="hd">玩家 1</span><span class="hd">玩家 2</span>${ACTIONS.map(([a,t])=>`<span>${t}</span>${cell(0,a)}${cell(1,a)}`).join("")}</div></div>
    ${msg?`<p style="color:var(--amber)">${msg}</p>`:""}
    <div class="row-btns"><button type="button" data-act="keys-reset">恢復預設</button><button type="button" data-act="settings">← 返回設定</button><button type="button" data-act="menu">回主選單</button></div>
    <p class="hint">Esc、P、M、R、Backspace 是暫停、靜音、重來、回選單用的，不能設定。<br>注音輸入法按 Shift 會切中英文，不建議設成 Shift。</p></div>`)}
function showPause(){showPanel(`<div class="card"><div class="big">PAUSE</div><ul class="menu">${kbtn("Esc","返回遊戲","也可以按 P","resume")}${kbtn("R","重新開始","","restart")}${kbtn("⌫","回主選單","Backspace","menu")}</ul></div>`)}
function fmt(t){const m=Math.floor(t/60),s=(t%60).toFixed(2).padStart(5,"0");return`${m}:${s}`}

/* 結算：每位玩家一欄，勝負標籤＋各項數據，最好的數值標亮 */
/* 結算：每位玩家一欄，勝負標籤＋各項數據；判定勝負用的項目排最前面並編號，決定勝負的那一列標亮 */
const STAT={score:["分數",p=>p.score,1],lines:["消行",p=>p.lines,1],sent:["送出攻擊",p=>p.sent,1],recv:["收到攻擊",p=>p.received,0],ko:["KO",p=>p.ko,1],
  deaths:["被擊倒",p=>p.deaths,0],height:["結束時行高",p=>p.height(),0],combo:["最高連擊",p=>Math.max(0,p.maxCombo),1],tetris:["四行消除",p=>p.tetrises,1],
  tspin:["T 轉",p=>p.tspins,1],ppm:["每分鐘方塊",p=>match.elapsed?Math.round(p.pieces/match.elapsed*60):0,1]};
const RULES={battle:["ko","sent","height"],attack:["sent","ko","height"],score:["score","lines"]};   // 依序比，前面一樣才比下一項
const SCORE_ITEMS=[["line1","單行","100 × 等級"],["line2","雙行","300 × 等級"],["line3","三行","500 × 等級"],["line4","四行消除","800 × 等級"],
  ["tspin0","T 轉（沒消行）","400 × 等級"],["tspin1","T 轉單行","800 × 等級"],["tspin2","T 轉雙行","1200 × 等級"],["tspin3","T 轉三行","1600 × 等級"],
  ["b2b","連續四行／T 轉加成","該次的 0.5 倍"],["combo","連擊加分","50 × 連擊數 × 等級"],["perfect","全清","3000 × 等級"],["soft","軟降","每格 1"],["hard","硬降","每格 2"]];
function scoreRows(P){const used=SCORE_ITEMS.filter(([k])=>P.some(p=>p.book[k]));
  const unit=k=>["soft","hard"].includes(k)?"格":"次";
  const rows=used.map(([k,n,rule])=>`<tr><td>${n}<br><small style="color:var(--dim)">${rule}</small></td>${P.map(p=>{const b=p.book[k];return`<td>${b?`${b.n.toLocaleString()} ${unit(k)}<br><b>${b.pts.toLocaleString()}</b>`:"-"}</td>`}).join("")}</tr>`).join("");
  const sum=`<tr class="key"><td>合計</td>${P.map(p=>`<td><b>${p.score.toLocaleString()}</b></td>`).join("")}</tr>`;
  return (rows||`<tr><td colspan="${P.length+1}">這局還沒有得分</td></tr>`)+sum}
function showResult(){const m=match,P=m.players,two=P.length===2;let head;
  if(cfg.kind==="sprint")head=m.success?`完成！${fmt(m.finish[0])}`:"挑戰失敗";
  else if(cfg.kind==="marathon")head=m.success?"15 關全破！":`消了 ${P[0].lines} 行`;
  else if(m.winner===-1)head="平手";
  else if(ais[1]||m.net)head=m.winner===0?"你贏了！":"你輸了";
  else head=`${names[m.winner]} 獲勝！`;
  const tag=i=>!two?"":m.winner===-1?'<span class="tag draw">平手</span>':m.winner===i?'<span class="tag win">勝利</span>':'<span class="tag lose">落敗</span>';
  const rule=two?(RULES[cfg.kind]||[]):[];
  // 找出決定勝負的那一項
  let keyStat=null,why="";
  for(const k of rule){const [,f]=STAT[k];if(f(P[0])!==f(P[1])){keyStat=k;break}}
  if(two&&keyStat&&(m.winner===0||m.winner===1)){const [n,f,hi]=STAT[keyStat],w=m.winner,l=1-w,ord=rule.indexOf(keyStat);
    const prev=rule.slice(0,ord).map(k=>`${STAT[k][0]}一樣`).join("、");
    why=`${prev?prev+"，所以比"+n+"。":""}決勝關鍵：${n} ${names[w]} ${f(P[w]).toLocaleString()} ${hi?">":"<"} ${names[l]} ${f(P[l]).toLocaleString()}${hi?"":"（越低越好）"}`}
  else if(two&&cfg.kind==="survival"&&m.winner!==-1)why=`決勝關鍵：${names[1-m.winner]} 先被頂到頂`;
  else if(two&&m.winner===-1)why="每一項判定都一樣，算平手";
  const ruleText={battle:"KO 對戰的判定：① KO 多的贏 → ② 送出攻擊多的贏 → ③ 結束時行高低的贏（分數不算）",
    attack:`攻擊對戰的判定：先送出 ${ATTACK_GOAL} 行的人贏；時間到就 ① 送出攻擊 → ② KO → ③ 行高`,
    score:"分數對戰的判定：① 分數高的贏 → ② 消行多的贏",survival:"生死戰的判定：先被頂到頂的人輸（分數不算）"}[cfg.kind]||"";
  let order=[...rule,"score","lines","sent","recv","ko","deaths","combo","tetris","tspin","ppm"].filter((k,i,a)=>a.indexOf(k)===i);
  if(!two)order=order.filter(k=>!["sent","recv","ko","deaths","height"].includes(k));
  if(!["battle","attack"].includes(cfg.kind))order=order.filter(k=>!["ko","deaths"].includes(k));
  const body=order.map(k=>{const [n,f,hi]=STAT[k],v=P.map(f),best=two&&v[0]!==v[1]?(hi?Math.max(...v):Math.min(...v)):null,no=rule.indexOf(k);
    return`<tr class="${k===keyStat?"key":""}"><td>${no>=0?`<span class="no">判定${"①②③"[no]}</span>`:""}${n}</td>${v.map(x=>`<td style="${x===best?"color:var(--amber)":""}">${x.toLocaleString()}</td>`).join("")}</tr>`}).join("");
  const extra=[];if(note)extra.push(note);if(two&&cfg.kind==="survival")extra.push(`本次戰績 ${wins[0]} : ${wins[1]}`);
  extra.push(`用時 ${fmt(m.elapsed)}`);
  showPanel(`<div class="card"><div class="big">${head}</div>${why?`<p class="why">${why}</p>`:""}${ruleText?`<p style="text-align:center">${ruleText}</p>`:""}
    <div class="scroll"><table class="result"><thead><tr><th></th>${P.map((_,i)=>`<th>${names[i]}<br>${tag(i)}</th>`).join("")}</tr></thead><tbody>${body}</tbody></table></div>
    <h2 style="font-size:16px">分數明細</h2>
    <div class="scroll"><table class="result"><thead><tr><th>項目（每次的分數）</th>${P.map((_,i)=>`<th>${names[i]}</th>`).join("")}</tr></thead><tbody>${scoreRows(P)}</tbody></table></div>
    <details class="how"><summary>分數怎麼算？</summary>消 1／2／3／4 行：100／300／500／800 分 × 等級；T 轉（沒消行 400，消 1／2／3 行 800／1200／1600）× 等級；
      連擊每次再加 50 × 連擊數 × 等級；連續四行或連續 T 轉 × 1.5；全清再加 3000 × 等級；軟降每格 1 分、硬降每格 2 分。
      只有「分數對戰」用分數判勝負，其他模式分數只是參考。</details>
    ${extra.map(l=>`<p style="text-align:center">${l}</p>`).join("")}
    <ul class="menu">${m.net?(NET.host?kbtn("R","再來一局（同模式）","對手會一起開始","restart")+kbtn("M","換模式","回房間選模式","net-room"):`<li><p class="hint">等房主開下一局…</p></li>`)+kbtn("⌫","離開房間","","net-leave"):kbtn("R","再來一局","空白鍵 / Enter 也可以","restart")+kbtn("⌫","回主選單","Esc / Backspace","menu")}</ul></div>`,true)}

panel.addEventListener("click",e=>{const b=e.target.closest("button");if(!b||performance.now()<panelGuard)return;audio.init();
  if(b.dataset.key){const [i,a]=b.dataset.key.split(":");waitKey=[+i,a];showKeys();return}
  if(b.dataset.act)handle(b.dataset.act)});
function handle(a){
  if(a.startsWith("mode")){const m=MODES.find(x=>x.key===+a.slice(4));if(m.cfg.vs)showDiff(m.cfg);else start(m.cfg,"普通")}
  else if(a==="install")PWA.install();else if(a==="update")location.reload();else if(a==="online")showOnline();else if(a==="net-create")netCreate();else if(a==="net-join")netJoin();
  else if(a.startsWith("net-mode"))netHostStart(+a.slice(8));else if(a==="net-room")showRoom();else if(a==="net-leave"){netLeave();showMenu()}
  else if(a==="settings"){waitKey=null;showSettings()}else if(a==="keys")showKeys();
  else if(a==="keys-reset"){keys=DEFAULT_KEYS.map(k=>Object.assign({},k));save("taco-blocks-keys",keys);waitKey=null;showKeys("已恢復預設按鍵")}
  else if(a.startsWith("diff")){const n=+a.slice(4);start(cfg,n===4?null:Object.keys(DIFFICULTY)[n-1])}
  else if(a.startsWith("set")){const k=a.slice(3);toggleSetting(k);if(k==="style"||k==="music"){audio.stopMusic();if(settings.music){audio.startMusic();clearTimeout(audio.preview);audio.preview=setTimeout(()=>{if(state!=="play")audio.stopMusic()},6000)}}showSettings()}
  else if(a==="resume")setPause(false);else if(a==="restart"){if(match&&match.net){if(NET.host)netHostStart(NET.modeKey)}else start(cfg,diff)}else if(a==="menu"){paused=false;showMenu()}}
function setPause(v){if(state!=="play"||match.over)return;if(match.net)return netSetPause(v);paused=v;audio.paused=v;if(v){for(const k in held)delete held[k];match.players.forEach(p=>p.soft=false);showPause()}else hidePanel()}
function bindKey(code){const [i,a]=waitKey;waitKey=null;
  if(code==="Escape"){showKeys();return}
  if(RESERVED.includes(code)){showKeys(`「${keyName(code)}」是系統用的鍵，請換一個`);return}
  const old=keys[i][a];let swapped="";
  keys.forEach((m,j)=>{for(const [b,t] of ACTIONS)if(m[b]===code&&!(j===i&&b===a)){m[b]=old;swapped=`（和玩家 ${j+1} 的「${t}」互換）`}});
  keys[i][a]=code;save("taco-blocks-keys",keys);showKeys(`玩家 ${i+1}「${ACTIONS.find(x=>x[0]===a)[1]}」改成 ${keyName(code)} ${swapped}`)}

