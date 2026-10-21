/* taco 方塊對戰：電腦對手（和 Python 版 ai.py 一樣的評分）。
   所有檔案依 index.html 的順序載入，共用同一個全域範圍。 */
"use strict";
/* ================= 電腦對手（和 ai.py 一樣的評分） ================= */
const DIFFICULTY={"簡單":.40,"普通":.18,"困難":.07};
function evaluate(grid,cells){const b=grid.map(r=>r.slice());for(const [x,y] of cells)if(y>=0)b[y][x]="X";
  const full=b.map((r,i)=>r.every(Boolean)?i:-1).filter(i=>i>=0);let board=b.filter((_,i)=>!full.includes(i));
  board=Array.from({length:full.length},()=>Array(COLS).fill(null)).concat(board);
  const hs=[];let holes=0;for(let x=0;x<COLS;x++){let top=ROWS;for(let y=0;y<ROWS;y++)if(board[y][x]){top=y;break}hs.push(ROWS-top);for(let y=top;y<ROWS;y++)if(!board[y][x])holes++}
  let bump=0;for(let i=0;i<COLS-1;i++)bump+=Math.abs(hs[i]-hs[i+1]);
  return -.51*hs.reduce((a,b)=>a+b,0)+.76*full.length**2-.72*holes-.18*bump-.3*Math.max(...hs)}
function bestPlacement(p){let best=[0,p.x],bs=-Infinity;for(let r=0;r<4;r++)for(let x=-2;x<COLS;x++){if(!p.valid(p.kind,r,x,-2))continue;let y=-2;while(p.valid(p.kind,r,x,y+1))y++;
  const c=cellsOf(p.kind,r,x,y);if(c.some(([,cy])=>cy<0))continue;const s=evaluate(p.grid,c);if(s>bs){bs=s;best=[r,x]}}return best}
class AI{constructor(iv){this.iv=iv;this.t=0;this.target=null;this.no=-1}
  update(dt,p,m,i){if(!p.active)return;this.t+=dt;if(this.t<this.iv)return;this.t=0;
    if(!this.target||this.no!==p.pieceNo){this.target=bestPlacement(p);this.no=p.pieceNo}
    const [r,x]=this.target;let ok=false;if(p.rot!==r)ok=p.rotate(1);else if(p.x!==x)ok=p.move(x>p.x?1:-1);if(!ok)m.hardDrop(i)}}

