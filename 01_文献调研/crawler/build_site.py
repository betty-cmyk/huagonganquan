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
        ● 空间关系固定，不可拖拽<br>● 滚动缩放查看细节<br>● 点击分类查看分类内论文
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

  const S = 24; // 网格单元间距
  const D = 16; // 大类之间的固定格点距离，完美留出6-7个单位的空气墙

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

  // papers are assigned to exact empty spots around category
  categories.forEach(c => {
    const catPapers = papers.filter(p => p.primary_category === c.cat_id);
    let ring = 2; // 第 0 和第 1 层空出，留给文字排布空间，绝不遮挡
    let points = [];
    while(points.length < catPapers.length) {
      points = points.concat(getHexSpiral(ring));
      ring++;
    }
    catPapers.forEach((p, i) => {
      p.r = 4.5;
      p.axial_q = c.axial_q + points[i].dq;
      p.axial_r = c.axial_r + points[i].dr;
      p.x = S * Math.sqrt(3) * (p.axial_q + p.axial_r/2);
      p.y = S * 3/2 * p.axial_r;
    });
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

  const edges = G.edges.filter(e=>e.type==='cat_cat');
  ge.selectAll('line').data(edges).join('line')
    .attr('x1', d=>d.source.x).attr('y1', d=>d.source.y)
    .attr('x2', d=>d.target.x).attr('y2', d=>d.target.y)
    .attr('stroke', '#58a6ff').attr('stroke-width', d=>Math.min(8, Math.max(1, d.weight*0.4))).attr('stroke-opacity', .35);

  const hullData = categories.map(c=>{
    const pts = papers.filter(p=>p.primary_category===c.cat_id).map(p=>[p.x,p.y]);
    return {cat:c, pts};
  });

  hullData.forEach(h=>{
    if(h.pts.length === 0) return;
    let path = '';
    if(h.pts.length < 3){
      const rr = 36;
      path = `M ${h.cat.x-rr},${h.cat.y} a ${rr},${rr} 0 1,0 ${rr*2},0 a ${rr},${rr} 0 1,0 -${rr*2},0`;
    }else{
      const hull = d3.polygonHull(h.pts) || h.pts;
      const ext = expandHull(hull, 22);
      const line = d3.line().curve(d3.curveCatmullRomClosed.alpha(0.7));
      path = line(ext);
    }
    gh.append('path')
      .attr('class','hull')
      .attr('d', path)
      .attr('fill', h.cat.color)
      .attr('fill-opacity', .13)
      .attr('stroke', h.cat.color)
      .attr('stroke-opacity', .55)
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
    .attr('dy', d=>d.r+10)
    .attr('font-size', 3.5)
    .attr('fill', '#8b949e')
    .attr('pointer-events','none')
    .style('opacity', 0);

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

  function updateLabelVisibility(k){ labels.style('opacity', k > 2 ? 1 : 0); }
  updateLabelVisibility(kScale);
}

svg = d3.select('#svg');
root = d3.select('#root');
svg.call(d3.zoom().scaleExtent([0.05, 10]).on('zoom', e=>{kScale = e.transform.k; root.attr('transform', e.transform); root.selectAll('g.paper text').style('opacity', kScale > 2 ? 1 : 0);}));

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
