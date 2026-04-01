# -*- coding: utf-8 -*-
import os
import json

CRAWLER_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(CRAWLER_DIR, '..', 'data')
ROOT = os.path.join(CRAWLER_DIR, '..', '..')
DOCS_DIR = os.path.join(ROOT, 'docs')
GRAPH_JSON = os.path.abspath(os.path.join(DATA_DIR, 'graph_v3.json'))
OUT_HTML = os.path.abspath(os.path.join(DOCS_DIR, 'index.html'))

HTML_TPL = '''\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>化工安全论文知识网络图</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0d1117;color:#e6edf3;font-family:'Segoe UI',sans-serif;overflow:hidden}
#app{width:100vw;height:100vh;display:flex}
#sidebar{width:320px;min-width:320px;background:#161b22;border-right:1px solid #30363d;display:flex;flex-direction:column;transition:width .3s;z-index:100}
#sidebar.collapsed{width:0;min-width:0}
#sb-header{padding:15px;border-bottom:1px solid #30363d;display:flex;justify-content:space-between;align-items:center}
#sb-title{font-size:14px;color:#79c0ff;font-weight:bold}
#sb-toggle{background:none;border:1px solid #30363d;color:#8b949e;border-radius:4px;padding:2px 8px;cursor:pointer}
#sb-list{flex:1;overflow-y:auto;padding:5px}
.sb-item{padding:12px;border-bottom:1px solid #21262d;font-size:12px}
.sb-item-title{color:#e6edf3;margin-bottom:5px;line-height:1.4}
#graph-wrap{flex:1;position:relative;background:radial-gradient(circle at center, #161b22 0%, #0d1117 100%)}
svg{width:100%;height:100%}
#legend{position:absolute;top:20px;right:20px;background:rgba(22,27,34,.8);border:1px solid #30363d;padding:15px;border-radius:10px;pointer-events:none}
.lr{display:flex;align-items:center;gap:8px;margin:5px 0;font-size:12px}
.ld{width:10px;height:10px;border-radius:50%}
#tt{position:fixed;pointer-events:none;background:rgba(13,17,23,.95);border:1px solid #388bfd;padding:12px;border-radius:8px;font-size:12px;max-width:300px;display:none;z-index:1000;box-shadow:0 10px 30px rgba(0,0,0,.5)}
.hull{stroke-width:1.4}
.cat-label{font-size:13px;font-weight:700;paint-order:stroke;stroke:#0d1117;stroke-width:3px;stroke-linejoin:round}
</style>
</head>
<body>
<div id="app">
  <div id="sidebar">
    <div id="sb-header"><span id="sb-title">文献库</span><button id="sb-toggle" onclick="toggleSB()">收起</button></div>
    <div id="sb-list"></div>
  </div>
  <div id="graph-wrap">
    <svg id="svg"><g id="root"><g id="gh"></g><g id="ge"></g><g id="gn"></g></g></svg>
    <div id="legend">
      <h3 style="font-size:14px;margin-bottom:10px;color:#79c0ff">研究分类视图（固定布局·异形包裹）</h3>
      <div class="lr"><div class="ld" style="background:#79c0ff"></div>分类异形气泡（包裹论文）</div>
      <div class="lr"><div class="ld" style="background:#8b949e;opacity:.55"></div>论文节点</div>
      <div style="margin-top:10px;color:#8b949e;font-size:11px;line-height:1.6">
        ● 空间关系固定，不可拖拽<br>● 灰线=标题语义近邻，蓝线=跨分类相似<br>● 点击分类查看分类内论文
      </div>
    </div>
    <div id="tt"></div>
  </div>
</div>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const G = {GRAPH_DATA};
let svg, root, sbOpen = true, kScale = 1;

function toggleSB(){
  sbOpen=!sbOpen;
  document.getElementById('sidebar').classList.toggle('collapsed',!sbOpen);
  document.getElementById('sb-toggle').textContent=sbOpen?'收起':'展开';
}

function showInfo(d){
  const list = document.getElementById('sb-list');
  if(d.type === 'category'){
    document.getElementById('sb-title').textContent = d.label;
    const papers = (d.papers || []).sort((a,b)=>((b.year||'0')<(a.year||'0')?-1:1));
    list.innerHTML = papers.map((p,i)=>`<div class="sb-item"><div class="sb-item-title">${i+1}. ${p.title}</div><div style="color:#8b949e">${p.year||'未知'}</div></div>`).join('');
  }else{
    document.getElementById('sb-title').textContent = '论文详情';
    list.innerHTML = `<div class="sb-item"><div class="sb-item-title" style="font-size:14px;color:#79c0ff">${d.full_title}</div><p style="margin-top:10px">年份: ${d.year||'未知'}</p><p>作者: ${d.author||'未知'}</p><p>单位: ${d.unit||'未知'}</p></div>`;
  }
  if(!sbOpen) toggleSB();
}

function seededAngle(id){
  const v = (id * 9301 + 49297) % 233280;
  return (v / 233280) * Math.PI * 2;
}

function expandHull(points, pad){
  const c = d3.polygonCentroid(points);
  return points.map(p=>{
    const dx = p[0]-c[0], dy = p[1]-c[1];
    const len = Math.sqrt(dx*dx+dy*dy) || 1;
    return [p[0] + dx/len*pad, p[1] + dy/len*pad];
  });
}

function render(){
  const W = document.getElementById('graph-wrap').clientWidth;
  const H = window.innerHeight;

  const categories = G.nodes.filter(n=>n.type==='category');
  const papers = G.nodes.filter(n=>n.type==='paper');
  const catByKey = new Map(categories.map(c=>[c.cat_id,c]));

  const S = 35; // 更大的网格间距，保证文字放得下
  const D = 9;  // 缩小距离以贴合视觉

  const macroHex = [
    {q: 0, r: 0},
    {q: D, r: 0}, {q: D, r: -D}, {q: 0, r: -D}, {q: -D, r: 0}, {q: -D, r: D}, {q: 0, r: D},
    {q: 2*D, r: 0}, {q: 2*D, r: -D}, {q: -2*D, r: D}
  ];

  categories.forEach((c, i)=>{
    const h = macroHex[i % macroHex.length];
    c.axial_q = h.q; c.axial_r = h.r;
    c.x = S * Math.sqrt(3) * (c.axial_q + c.axial_r/2);
    c.y = S * 3/2 * c.axial_r;
  });

  const hexDirs = [
    {dq: 1, dr: 0}, {dq: 1, dr: -1}, {dq: 0, dr: -1},
    {dq: -1, dr: 0}, {dq: -1, dr: 1}, {dq: 0, dr: 1}
  ];

  function getHexSpiral(radius) {
    if (radius === 0) return [{dq:0, dr:0}];
    let results = [];
    let curQ = -radius;
    let curR = radius;
    for (let i = 0; i < 6; i++) {
        for (let j = 0; j < radius; j++) {
            results.push({dq: curQ, dr: curR});
            curQ += hexDirs[i].dq;
            curR += hexDirs[i].dr;
        }
    }
    return results;
  }

  // 1. 每篇论文关联多个分类，计算其重力坐标 (Ideal Position)
  papers.forEach(p => {
    let cats = [];
    if(p.categories && p.categories.length) {
      cats = p.categories.map(cid => catByKey.get(cid)).filter(Boolean);
    }
    if(!cats.length) cats = [catByKey.get(p.primary_category) || categories[0]];
    
    let sumX = 0, sumY = 0;
    cats.forEach(c => { sumX += c.x; sumY += c.y; });
    p.idealX = sumX / cats.length + (Math.random()-0.5)*S*0.5;
    p.idealY = sumY / cats.length + (Math.random()-0.5)*S*0.5;
    p.r = 5;
  });

  // 2. 占位保护：类别中心及第一圈不得填入论文
  const occupiedGrid = new Set();
  categories.forEach(c => {
    occupiedGrid.add(`${c.axial_q},${c.axial_r}`);
    hexDirs.forEach(d => occupiedGrid.add(`${c.axial_q+d.dq},${c.axial_r+d.dr}`));
  });

  // 根据屏幕坐标近似反推格点
  function screenToHex(x, y) {
    let q_f = (Math.sqrt(3)/3 * x - 1/3 * y) / S;
    let r_f = (2/3 * y) / S;
    let q = Math.round(q_f), r = Math.round(r_f), s = Math.round(-q_f - r_f);
    let q_d = Math.abs(q - q_f), r_d = Math.abs(r - r_f), s_d = Math.abs(s - (-q_f - r_f));
    if (q_d > r_d && q_d > s_d) q = -r - s;
    else if (r_d > s_d) r = -q - s;
    return {q, r};
  }

  function axialToPt(q, r) {
    return { x: S * Math.sqrt(3) * (q + r/2), y: S * 3/2 * r };
  }

  // 论文按照理想位置寻找附近空旷格点
  papers.sort(() => Math.random() - 0.5); // 随机顺避免扎堆一侧
  papers.forEach(p => {
    const centerHex = screenToHex(p.idealX, p.idealY);
    let radius = 0;
    let bestHex = null;
    while(true) {
      const ringList = getHexSpiral(radius);
      let minD = Infinity;
      for(let pt of ringList) {
        const hq = centerHex.q + pt.dq, hr = centerHex.r + pt.dr;
        const key = `${hq},${hr}`;
        if(!occupiedGrid.has(key)) {
          const sp = axialToPt(hq, hr);
          const dist = Math.pow(sp.x - p.idealX, 2) + Math.pow(sp.y - p.idealY, 2);
          if(dist < minD) { minD = dist; bestHex = {q: hq, r: hr}; }
        }
      }
      if(bestHex) break;
      radius++;
    }
    occupiedGrid.add(`${bestHex.q},${bestHex.r}`);
    p.axial_q = bestHex.q; p.axial_r = bestHex.r;
    const realPt = axialToPt(p.axial_q, p.axial_r);
    p.x = realPt.x; p.y = realPt.y;
  });

  // Center mathematically
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  [...categories, ...papers].forEach(n => {
    if(n.x < minX) minX = n.x; if(n.x > maxX) maxX = n.x;
    if(n.y < minY) minY = n.y; if(n.y > maxY) maxY = n.y;
  });
  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;
  
  [...categories, ...papers].forEach(n => {
    n.x = n.x - cx + W/2; 
    n.y = n.y - cy + H/2;
  });

  const ge = d3.select('#ge'); ge.selectAll('*').remove();
  const gh = d3.select('#gh'); gh.selectAll('*').remove();
  const gn = d3.select('#gn'); gn.selectAll('*').remove();

  const nodeById = new Map();
  [...categories, ...papers].forEach(n => nodeById.set(n.id, n));

  const relEdges = G.edges.filter(e => e.type === 'paper_sim_intra' || e.type === 'paper_sim_cross');
  ge.selectAll('line.sim').data(relEdges).join('line')
    .attr('class', 'sim')
    .attr('x1', d => nodeById.get(d.source)?.x ?? 0)
    .attr('y1', d => nodeById.get(d.source)?.y ?? 0)
    .attr('x2', d => nodeById.get(d.target)?.x ?? 0)
    .attr('y2', d => nodeById.get(d.target)?.y ?? 0)
    .attr('stroke', d => d.type === 'paper_sim_cross' ? '#58a6ff' : '#8b949e')
    .attr('stroke-width', d => d.type === 'paper_sim_cross' ? 0.9 : 0.45)
    .attr('stroke-opacity', d => d.type === 'paper_sim_cross' ? 0.55 : 0.22);

  const catEdges = G.edges.filter(e => e.type === 'cat_cat');
  ge.selectAll('line.cat').data(catEdges).join('line')
    .attr('class', 'cat')
    .attr('x1', d => nodeById.get(d.source)?.x ?? 0)
    .attr('y1', d => nodeById.get(d.source)?.y ?? 0)
    .attr('x2', d => nodeById.get(d.target)?.x ?? 0)
    .attr('y2', d => nodeById.get(d.target)?.y ?? 0)
    .attr('stroke', '#79c0ff')
    .attr('stroke-width', d => Math.min(3, 0.6 + (d.weight || 1) * 0.06))
    .attr('stroke-opacity', 0.28);

  const hullData = categories.map(c=>{
    const pts = papers.filter(p=>(p.categories && p.categories.includes(c.cat_id)) || p.primary_category === c.cat_id).map(p=>[p.x,p.y]);
    return {cat:c, pts};
  });

  hullData.forEach(h=>{
    if(h.pts.length === 0) return;
    let path = '';
    // Give all points a tiny sub-pixel random jitter to prevent D3 from failing on perfectly collinear hex coordinates
    const safePts = h.pts.map(pt => [pt[0] + (Math.random()-0.5)*0.1, pt[1] + (Math.random()-0.5)*0.1]);
    
    if(safePts.length < 3){
      const rr = 36;
      path = `M ${h.cat.x-rr},${h.cat.y} a ${rr},${rr} 0 1,0 ${rr*2},0 a ${rr},${rr} 0 1,0 -${rr*2},0`;
    }else{
      try {
        const hull = d3.polygonHull(safePts) || safePts;
        const ext = expandHull(hull, 22);
        const line = d3.line().curve(d3.curveCatmullRomClosed.alpha(0.7));
        path = line(ext);
      } catch (err) {
        // Fallback for extreme degenerate cases
        const rr = 40;
        path = `M ${h.cat.x-rr},${h.cat.y} a ${rr},${rr} 0 1,0 ${rr*2},0 a ${rr},${rr} 0 1,0 -${rr*2},0`;
      }
    }
    gh.append('path')
      .attr('class','hull')
      .attr('d', path)
      .attr('fill', h.cat.color)
      .attr('fill-opacity', .06)
      .attr('stroke', h.cat.color)
      .attr('stroke-opacity', .35)
      .style('cursor','pointer')
      .on('click', ()=>showInfo(h.cat));
  });

  const paperNode = gn.selectAll('g.paper').data(papers).join('g').attr('class','paper').attr('transform', d=>`translate(${d.x},${d.y})`).attr('cursor','pointer');

  paperNode.append('circle')
    .attr('r', d=>d.r)
    .attr('fill', d=>d.color)
    .attr('fill-opacity', .42)
    .attr('stroke', d=>d.color)
    .attr('stroke-width', .9);

  const labels = paperNode.append('text')
    .text(d=>d.label)
    .attr('text-anchor', 'middle')
    .attr('dy', d=>d.r+8)
    .attr('font-size', 2.8)
    .attr('fill', '#c9d1d9')
    .attr('pointer-events','none');

  const catLabel = gn.selectAll('text.cat-label').data(categories).join('text')
    .attr('class','cat-label')
    .attr('x', d=>d.x)
    .attr('y', d=>d.y)
    .attr('text-anchor','middle')
    .attr('fill', d=>d.color)
    .text(d=>d.label)
    .style('cursor','pointer')
    .on('click', (_,d)=>showInfo(d));

  const tt = document.getElementById('tt');
  paperNode
    .on('mouseover', (e,d)=>{
      tt.style.display='block';
      tt.innerHTML=`<div style="font-weight:bold;color:#79c0ff">${d.full_title || d.label}</div><div style="color:#8b949e;margin-top:4px">论文条目</div>`;
    })
    .on('mousemove', e=>{tt.style.left=(e.clientX+15)+'px';tt.style.top=(e.clientY-10)+'px';})
    .on('mouseout', ()=>tt.style.display='none')
    .on('click', (_,d)=>showInfo(d));

  catLabel
    .on('mouseover', (e,d)=>{
      tt.style.display='block';
      tt.innerHTML=`<div style="font-weight:bold;color:#79c0ff">${d.label}</div><div style="color:#8b949e;margin-top:4px">研究分类 · ${d.count} 篇</div>`;
    })
    .on('mousemove', e=>{tt.style.left=(e.clientX+15)+'px';tt.style.top=(e.clientY-10)+'px';})
    .on('mouseout', ()=>tt.style.display='none');

  function updateLabelVisibility(k){ labels.style('opacity', 1); }
  updateLabelVisibility(kScale);
}

svg = d3.select('#svg');
root = d3.select('#root');
svg.call(d3.zoom().scaleExtent([0.05, 10]).on('zoom', e=>{kScale = e.transform.k; root.attr('transform', e.transform); }));

render();
</script>
</body></html>
'''


def main():
    with open(GRAPH_JSON, 'r', encoding='utf-8') as f:
        gdata = f.read()

    html = HTML_TPL.replace('{GRAPH_DATA}', gdata)

    with open(OUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'Done: {OUT_HTML}')


if __name__ == '__main__':
    main()
