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
#sidebar-right{width:320px;min-width:320px;background:#161b22;border-left:1px solid #30363d;display:flex;flex-direction:column;transition:width .3s;z-index:100;transform:translateX(100%);position:absolute;right:0;top:0;bottom:0}
#sidebar-right.active{transform:translateX(0)}
#sbr-header{padding:15px;border-bottom:1px solid #30363d;display:flex;justify-content:space-between;align-items:center}
#sbr-title{font-size:14px;color:#79c0ff;font-weight:bold}
#sbr-toggle{background:none;border:1px solid #30363d;color:#8b949e;border-radius:4px;padding:2px 8px;cursor:pointer}
#sbr-list{flex:1;overflow-y:auto;padding:15px;font-size:12px;color:#e6edf3;line-height:1.6}
.hull{stroke-width:1.4}
.cat-label{font-size:13px;font-weight:700;paint-order:stroke;stroke:#0d1117;stroke-width:3px;stroke-linejoin:round}
#analysis-btn{position:absolute;top:20px;right:20px;background:#388bfd;color:#fff;border:none;padding:10px 16px;border-radius:6px;cursor:pointer;font-size:13px;font-weight:bold;pointer-events:auto;box-shadow:0 0 10px rgba(56,139,253,0.4);z-index:150;}
#charts-tray{position:fixed;bottom:-450px;left:0;right:0;height:450px;background:#161b22;border-top:1px solid #30363d;transition:bottom .3s, right .3s;z-index:200;padding:20px;display:flex;gap:15px;overflow-x:auto}
#charts-tray.active{bottom:0}
#charts-tray.with-sbr{right:320px}
.chart-box{min-width:300px;flex:1;background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:15px;display:flex;flex-direction:column}
.chart-title{font-size:13px;color:#79c0ff;margin-bottom:10px;text-align:center;font-weight:bold}
#close-tray{position:absolute;top:10px;right:10px;background:none;border:none;color:#8b949e;cursor:pointer;font-size:20px}
.stat-tag{display:inline-block;padding:2px 8px;border-radius:12px;font-size:10px;margin:2px;background:#21262d;border:1px solid #30363d}
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
    <button id="analysis-btn" onclick="toggleAnalysis()">查看统计分析图表</button>
    <div id="sidebar-right" class="active">
      <div id="sbr-header"><span id="sbr-title">论文档案</span><button id="sbr-toggle" onclick="toggleSBR()">关闭</button></div>
      <div id="sbr-list">请在网络图中点击具体论文气泡查看详细信息。</div>
    </div>
    <div id="charts-tray">
      <button id="close-tray" onclick="toggleAnalysis()">×</button>
      <div class="chart-box" id="chart-years"><div class="chart-title">历年论文产出趋势</div><div class="chart-canvas" style="flex:1"></div></div>
      <div class="chart-box" id="chart-cats"><div class="chart-title">研究方向分布</div><div class="chart-canvas" style="flex:1"></div></div>
      <div class="chart-box" id="chart-units"><div class="chart-title">核心研究机构Top10</div><div class="chart-canvas" style="flex:1"></div></div>
      <div class="chart-box" id="chart-kws"><div class="chart-title">关键词分布热度</div><div class="chart-canvas" style="flex:1;display:flex;flex-wrap:wrap;align-content:flex-start;justify-content:flex-start;overflow-y:auto;overflow-x:hidden;padding:6px"></div></div>
    </div>
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

let sbrOpen = true;
function toggleSBR(){
  sbrOpen=!sbrOpen;
  document.getElementById('sidebar-right').classList.toggle('active', sbrOpen);
  document.getElementById('charts-tray').classList.toggle('with-sbr', sbrOpen);
}

function showInfo(d){
  if(d.type === 'category'){
    const list = document.getElementById('sb-list');
    document.getElementById('sb-title').textContent = d.label;
    const papers = (d.papers || []).sort((a,b)=>((b.year||'0')<(a.year||'0')?-1:1));
    list.innerHTML = `<div style="padding:10px;font-size:11px;color:#8b949e;background:#0d1117;margin-bottom:5px">共收集论文 ${papers.length} 篇</div>` + 
      papers.map((p,i)=>`<div class="sb-item" onclick='focusPaper(${JSON.stringify(p.title)})'><div class="sb-item-title">${i+1}. ${p.title}</div><div style="display:flex;justify-content:space-between;color:#8b949e"><span>${p.year||'未知'}</span></div></div>`).join('');
    if(!sbOpen) toggleSB();
  }else{
    const rlist = document.getElementById('sbr-list');
    document.getElementById('sbr-title').textContent = '论文档案';
    rlist.innerHTML = `<div style="font-size:16px;color:#79c0ff;font-weight:bold;margin-bottom:15px;border-bottom:1px solid #30363d;padding-bottom:10px">${d.full_title}</div>
      <div style="display:flex;justify-content:space-between;color:#8b949e;margin-bottom:10px"><span>年份：${d.year||'未知'}</span></div>
      <div style="color:#e6edf3;margin-bottom:15px"><strong>作者：</strong>${d.author||'未记录'}</div>
      <div style="color:#e6edf3;margin-bottom:20px"><strong>单位：</strong>${d.unit||'未记录'}</div>
      <div style="color:#79c0ff;margin-bottom:8px;font-weight:bold">核心摘要</div>
      <div style="background:#0d1117;padding:12px;border-radius:6px;border:1px solid #30363d;margin-bottom:20px">${d.abstract||'暂无摘要信息。'}</div>
      <div style="color:#79c0ff;margin-bottom:8px;font-weight:bold">关键词标签</div>
      <div style="margin-bottom:20px">${(d.keywords || '').split(/[，,]/).map(k=>`<span class="stat-tag">${k}</span>`).join('')}</div>
      <div style="color:#79c0ff;margin-bottom:8px;font-weight:bold">结构大纲</div>
      <div style="background:#0d1117;padding:12px;border-radius:6px;border:1px solid #30363d">${d.outline||'无目录提取记录。'}</div>
    `;
    if(!sbrOpen) toggleSBR();
  }
}

function focusPaper(title){
  const p = G.nodes.find(n=>n.full_title === title);
  if(p) showInfo(p);
}

let chartsInited = false;
function toggleAnalysis(){
  const tray = document.getElementById('charts-tray');
  tray.classList.toggle('active');
  if(tray.classList.contains('active') && !chartsInited) {
    initCharts();
    chartsInited = true;
  }
}

function initCharts(){
  // 1. 按类别历年趋势多折线
  const papers = G.nodes.filter(n => n.type==='paper');
  const catMap = new Map(G.nodes.filter(n => n.type==='category').map(c => [c.cat_id, c]));
  const yearSet = new Set();
  const seriesMap = new Map();

  papers.forEach(p => {
    const y = Number(p.year);
    if (!Number.isFinite(y) || y < 1900 || y > 2100) return;
    const cid = p.primary_category || 'UNKNOWN';
    const cname = catMap.get(cid)?.label || cid;
    if (!seriesMap.has(cid)) seriesMap.set(cid, { id: cid, label: cname, color: catMap.get(cid)?.color || '#8b949e', years: {} });
    const s = seriesMap.get(cid);
    s.years[y] = (s.years[y] || 0) + 1;
    yearSet.add(y);
  });

  const allYears = Array.from(yearSet).sort((a,b) => a-b);
  const yearDataByCat = Array.from(seriesMap.values()).map(s => ({
    ...s,
    data: allYears.map(y => ({ year: y, value: s.years[y] || 0 }))
  })).sort((a,b) => b.data.reduce((t,d)=>t+d.value,0) - a.data.reduce((t,d)=>t+d.value,0));

  const yBox = d3.select('#chart-years .chart-canvas');
  const yw = yBox.node().clientWidth, yh = yBox.node().clientHeight - 16;
  const ysvg = yBox.append('svg').attr('width', yw).attr('height', yh);

  const maxY = d3.max(yearDataByCat.flatMap(s => s.data.map(d => d.value))) || 1;
  const x = d3.scalePoint().domain(allYears).range([40, yw - 12]);
  const y = d3.scaleLinear().domain([0, maxY]).nice().range([yh - 28, 10]);

  ysvg.append('g')
    .attr('transform', `translate(0,${yh - 28})`)
    .call(d3.axisBottom(x).tickValues(allYears.filter((d,i)=>!(i%2))))
    .selectAll('text').style('font-size','9px').attr('transform','rotate(40)').style('text-anchor','start');

  ysvg.append('g')
    .attr('transform', 'translate(40,0)')
    .call(d3.axisLeft(y).ticks(4))
    .selectAll('text').style('font-size','9px');

  const line = d3.line().x(d => x(d.year)).y(d => y(d.value)).curve(d3.curveMonotoneX);
  yearDataByCat.forEach(s => {
    ysvg.append('path')
      .datum(s.data)
      .attr('fill','none')
      .attr('stroke', s.color)
      .attr('stroke-width', 1.8)
      .attr('stroke-opacity', 0.9)
      .attr('d', line);
  });

  const legend = ysvg.append('g').attr('transform', `translate(${Math.max(46, yw - 190)},14)`);
  yearDataByCat.slice(0, 8).forEach((s, i) => {
    const row = legend.append('g').attr('transform', `translate(0,${i * 14})`);
    row.append('line').attr('x1',0).attr('x2',12).attr('y1',0).attr('y2',0).attr('stroke', s.color).attr('stroke-width',2);
    row.append('text').attr('x',16).attr('y',3).attr('fill','#c9d1d9').style('font-size','9px').text(s.label.replace('类',''));
  });

  // 2. 饼图
  const cats = G.nodes.filter(n=>n.type==='category').map(c=>({label:c.label, count:c.count, color:c.color})).sort((a,b)=>b.count-a.count);
  const cBox = d3.select('#chart-cats .chart-canvas');
  const cw = cBox.node().clientWidth, ch = cBox.node().clientHeight;
  const csvg = cBox.append('svg').attr('width',cw).attr('height',ch).append('g').attr('transform',`translate(${cw/2},${ch/2})`);
  const pie = d3.pie().value(d=>d.count).sort(null);
  const arc = d3.arc().innerRadius(ch/5).outerRadius(ch/3.2);
  const outerArc = d3.arc().innerRadius(ch/2.3).outerRadius(ch/2.3);
  
  const pData = pie(cats);
  csvg.selectAll('path.slice').data(pData).join('path').attr('class','slice').attr('d',arc).attr('fill',d=>d.data.color).attr('stroke','#161b22').attr('stroke-width',1);

  // Anti-overlap layout for labels
  pData.forEach(d => {
    let midA = d.startAngle + (d.endAngle - d.startAngle)/2;
    d.pos = outerArc.centroid(d);
    d.side = midA < Math.PI ? 1 : -1;
    d.pos[0] = ch/2.3 * d.side;
  });
  
  for(let iter=0; iter<30; iter++){
    for(let i=0; i<pData.length; i++){
      for(let j=i+1; j<pData.length; j++){
        let a = pData[i], b = pData[j];
        if(a.side === b.side){
          let dy = b.pos[1] - a.pos[1];
          if(Math.abs(dy) < 14){
            let push = (14 - Math.abs(dy)) * 0.5 * Math.sign(dy || 1);
            a.pos[1] -= push; b.pos[1] += push;
          }
        }
      }
    }
  }

  csvg.selectAll('polyline').data(pData).join('polyline')
    .attr('points', d => {
        let p1 = arc.centroid(d);
        let p2 = outerArc.centroid(d);
        return [p1, p2, d.pos];
    }).style('fill','none').style('stroke','#484f58').style('stroke-width',1);

  csvg.selectAll('.pie-label').data(pData).join('text').attr('class','pie-label')
    .attr('transform', d => `translate(${d.pos[0] + d.side * 4}, ${d.pos[1]})`)
    .text(d => `${d.data.label.replace(/^.*_/,'')} (${d.data.count})`)
    .attr('text-anchor', d => d.side===1 ? 'start' : 'end')
    .attr('fill', '#c9d1d9').style('font-size', '10px').attr('dy', '.3em');
  
  // 3. 词云 (简单标签云实现)
  const kwMap = {};
  G.nodes.filter(n=>n.type==='paper').forEach(p=>{ (p.keywords||'').split(/[，,]/).forEach(k=>{ if(k.trim().length>1) kwMap[k.trim()]=(kwMap[k.trim()]||0)+1; }); });
  const topKws = Object.entries(kwMap).sort((a,b)=>b[1]-a[1]).slice(0,120);
  const kBox = d3.select('#chart-kws .chart-canvas');
  kBox.html(''); 
  topKws.forEach(([word, count])=>{
    kBox.append('span').attr('class','stat-tag').style('font-size',`${Math.min(16, 8 + count*1.4)}px`).style('color',d3.interpolateCool(Math.random())).text(word);
  });

  // 4. 核心机构柱状图
  const units = {};
  G.nodes.filter(n=>n.type==='paper').forEach(p=>{ if(p.unit && p.unit!=='未记录') units[p.unit] = (units[p.unit]||0)+1; });
  const unitData = Object.entries(units).sort((a,b)=>b[1]-a[1]).slice(0,10);
  const uBox = d3.select('#chart-units .chart-canvas');
  uBox.html('');
  const uw = uBox.node().clientWidth, uh = uBox.node().clientHeight;
  const usclX = d3.scaleLinear().domain([0, d3.max(unitData, d=>d[1])]).range([0, uw-100]);
  const usclY = d3.scaleBand().domain(unitData.map(d=>d[0])).range([10, uh-30]).padding(0.3);
  const usvg = uBox.append('svg').attr('width',uw).attr('height',uh);
  
  usvg.selectAll('rect').data(unitData).join('rect')
    .attr('x', 80).attr('y', d=>usclY(d[0])).attr('width', d=>usclX(d[1])).attr('height', usclY.bandwidth())
    .attr('fill', '#388bfd').attr('rx', 3);
  usvg.selectAll('.u-label').data(unitData).join('text').attr('class','u-label')
    .attr('x', 75).attr('y', d=>usclY(d[0]) + usclY.bandwidth()/2).attr('dy', '.35em').text(d=>d[0])
    .attr('text-anchor','end').attr('fill','#c9d1d9').style('font-size','10px');
  usvg.selectAll('.v-label').data(unitData).join('text').attr('class','v-label')
    .attr('x', d=>85 + usclX(d[1])).attr('y', d=>usclY(d[0]) + usclY.bandwidth()/2).attr('dy', '.35em').text(d=>d[1])
    .attr('fill','#79c0ff').style('font-size','10px').style('font-weight','bold');
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
  const D = 10;

  // 按语义手工锚定：把工艺安全类放到风险评价/灾害防控附近
  const macroHexByCat = {
    'A_风险评价': {q: 0, r: 0},
    'J_工艺安全': {q: 4, r: -2},
    'B_灾害防控': {q: 10, r: -5},
    'E_事故应急': {q: 10, r: 0},
    'H_运输储存': {q: 5, r: 4},
    'C_安全管理体系': {q: -5, r: 4},
    'D_安全技术监测': {q: -10, r: 0},
    'I_园区企业': {q: -10, r: 5},
    'G_职业卫生': {q: -5, r: 8},
    'F_基础理论': {q: 0, r: 8},
  };

  categories.forEach((c, i)=>{
    const h = macroHexByCat[c.cat_id] || {q: (i-5)*2, r: (i%2===0?0:2)};
    c.axial_q = h.q; c.axial_r = h.r;
    c.anchorX = S * Math.sqrt(3) * (c.axial_q + c.axial_r/2);
    c.anchorY = S * 3/2 * c.axial_r;
    c.x = c.anchorX;
    c.y = c.anchorY;
  });

  // 分类中心做轻量排斥：防止大类气泡重叠成一团
  const CAT_MIN_DIST = S * 7.5;
  for (let iter = 0; iter < 80; iter++) {
    for (let i = 0; i < categories.length; i++) {
      for (let j = i + 1; j < categories.length; j++) {
        const a = categories[i], b = categories[j];
        let dx = b.x - a.x, dy = b.y - a.y;
        let dist = Math.sqrt(dx*dx + dy*dy) || 0.001;
        if (dist < CAT_MIN_DIST) {
          const push = (CAT_MIN_DIST - dist) * 0.06;
          dx /= dist; dy /= dist;
          a.x -= dx * push; a.y -= dy * push;
          b.x += dx * push; b.y += dy * push;
        }
      }
    }
    // 回弹到语义锚点，防止结构散架
    categories.forEach(c => {
      c.x = c.x * 0.92 + c.anchorX * 0.08;
      c.y = c.y * 0.92 + c.anchorY * 0.08;
    });
  }

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
    const primaryCat = catByKey.get(p.primary_category);
    if (!cats.length && primaryCat) cats = [primaryCat];

    // 主分类增强：优先贴近主分类中心，避免工艺安全等小类被完全拉走
    let sumX = 0, sumY = 0, wSum = 0;
    cats.forEach(c => {
      const w = (primaryCat && c.cat_id === primaryCat.cat_id) ? 0.68 : 0.32 / Math.max(1, cats.length - 1);
      sumX += c.x * w;
      sumY += c.y * w;
      wSum += w;
    });
    if (wSum <= 0 && primaryCat) {
      sumX = primaryCat.x;
      sumY = primaryCat.y;
      wSum = 1;
    }

    p.idealX = sumX / wSum + (Math.random()-0.5)*S*0.35;
    p.idealY = sumY / wSum + (Math.random()-0.5)*S*0.35;
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

  // 论文先按网格占位，再做轻量力学松弛，避免过于规整
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

  // 轻力学：拉向理想位 + 论文间轻排斥（让布局更自然）
  const RELAX_ITERS = 180;
  const REPULSE_DIST = S * 3.2;
  for (let it = 0; it < RELAX_ITERS; it++) {
    // 拉向理想位
    papers.forEach(p => {
      p.x += (p.idealX - p.x) * 0.1;
      p.y += (p.idealY - p.y) * 0.1;
    });

    // 论文间排斥
    for (let i = 0; i < papers.length; i++) {
      for (let j = i + 1; j < papers.length; j++) {
        const a = papers[i], b = papers[j];
        let dx = b.x - a.x, dy = b.y - a.y;
        let d = Math.sqrt(dx*dx + dy*dy) || 0.001;
        if (d < REPULSE_DIST) {
          const push = (REPULSE_DIST - d) * 0.04;
          dx /= d; dy /= d;
          a.x -= dx * push; a.y -= dy * push;
          b.x += dx * push; b.y += dy * push;
        }
      }
    }

    // 约束：不要偏离主分类过远
    papers.forEach(p => {
      const pc = catByKey.get(p.primary_category);
      if (!pc) return;
      const dx = p.x - pc.x, dy = p.y - pc.y;
      const d = Math.sqrt(dx*dx + dy*dy) || 0.001;
      const maxR = S * 8.2;
      if (d > maxR) {
        const k = (d - maxR) * 0.08;
        p.x -= (dx / d) * k;
        p.y -= (dy / d) * k;
      }
    });
  }

  // 小类标题轻微贴近本类论文簇，避免“标题远离气泡”
  categories.forEach(c => {
    const own = papers.filter(p => p.primary_category === c.cat_id);
    if (own.length > 0 && own.length <= 10) {
      const mx = own.reduce((s, p) => s + p.x, 0) / own.length;
      const my = own.reduce((s, p) => s + p.y, 0) / own.length;
      c.x = c.x * 0.88 + mx * 0.12;
      c.y = c.y * 0.88 + my * 0.12;
    }
  });

  // 分类标题排斥：避免标题覆盖论文气泡
  const LABEL_REPEL_ITERS = 140;
  for (let it = 0; it < LABEL_REPEL_ITERS; it++) {
    // 标题与论文排斥
    categories.forEach(c => {
      const labelR = Math.max(42, c.label.length * 8.2);
      papers.forEach(p => {
        let dx = c.x - p.x;
        let dy = c.y - p.y;
        let d = Math.sqrt(dx * dx + dy * dy) || 0.001;
        const minD = labelR + p.r + 16;
        if (d < minD) {
          const push = (minD - d) * 0.16;
          dx /= d;
          dy /= d;
          c.x += dx * push;
          c.y += dy * push;
        }
      });
    });

    // 标题与标题也互斥，防止互压
    for (let i = 0; i < categories.length; i++) {
      for (let j = i + 1; j < categories.length; j++) {
        const a = categories[i], b = categories[j];
        let dx = b.x - a.x;
        let dy = b.y - a.y;
        let d = Math.sqrt(dx * dx + dy * dy) || 0.001;
        const minD = Math.max(86, (a.label.length + b.label.length) * 4.6);
        if (d < minD) {
          const push = (minD - d) * 0.08;
          dx /= d;
          dy /= d;
          a.x -= dx * push; a.y -= dy * push;
          b.x += dx * push; b.y += dy * push;
        }
      }
    }

    // 标题不能跑太远，保持语义锚点
    categories.forEach(c => {
      let adx = c.x - c.anchorX;
      let ady = c.y - c.anchorY;
      let ad = Math.sqrt(adx * adx + ady * ady) || 0.001;
      const maxAnchorDrift = S * 3.6;
      if (ad > maxAnchorDrift) {
        const back = (ad - maxAnchorDrift) * 0.22;
        c.x -= (adx / ad) * back;
        c.y -= (ady / ad) * back;
      }
    });
  }

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
    .attr('stroke-opacity', d => d.type === 'paper_sim_cross' ? 0.5 : 0.18);

  // 全局晕染层（降亮40% + 平滑Blob边缘）
  const defs = svg.select('defs').empty() ? svg.append('defs') : svg.select('defs');
  defs.selectAll('*').remove();

  defs.append('filter')
    .attr('id', 'paper-glow-blur')
    .attr('x', '-120%')
    .attr('y', '-120%')
    .attr('width', '340%')
    .attr('height', '340%')
    .append('feGaussianBlur')
    .attr('stdDeviation', 6.2);

  defs.append('filter')
    .attr('id', 'edge-glow-blur')
    .attr('x', '-60%')
    .attr('y', '-60%')
    .attr('width', '220%')
    .attr('height', '220%')
    .append('feGaussianBlur')
    .attr('stdDeviation', 1.2);

  defs.append('filter')
    .attr('id', 'title-glow-blur')
    .attr('x', '-80%')
    .attr('y', '-80%')
    .attr('width', '260%')
    .attr('height', '260%')
    .append('feGaussianBlur')
    .attr('stdDeviation', 1.8);

  // 1) 类别Blob平滑边缘（替代规整圆）
  const blobLayer = gh.append('g')
    .attr('class', 'blob-layer')
    .attr('pointer-events', 'none');

  const geoPath = d3.geoPath();
  const papersByCat = d3.group(papers, d => d.primary_category);
  for (const [cid, plist] of papersByCat) {
    if (!plist || plist.length < 3) continue;
    const color = catByKey.get(cid)?.color || '#58a6ff';
    const density = d3.contourDensity()
      .x(d => d.x)
      .y(d => d.y)
      .size([W, H])
      .bandwidth(Math.max(28, S * 0.95))
      .thresholds(16);
    const contours = density(plist);
    const outer = contours.slice(0, Math.min(6, contours.length));
    outer.forEach((ct, i) => {
      blobLayer.append('path')
        .attr('d', geoPath(ct))
        .attr('fill', color)
        .attr('fill-opacity', 0.038 - i * 0.005)
        .attr('filter', 'url(#paper-glow-blur)');
    });
  }

  // 2) 连线晕染（仅跨类连线，减轻卡顿）
  const edgeGlow = gh.append('g')
    .attr('class', 'edge-glow-layer')
    .attr('pointer-events', 'none');

  const crossEdges = relEdges.filter(d => d.type === 'paper_sim_cross');
  edgeGlow.selectAll('line.sim-glow').data(crossEdges).join('line')
    .attr('class', 'sim-glow')
    .attr('x1', d => nodeById.get(d.source)?.x ?? 0)
    .attr('y1', d => nodeById.get(d.source)?.y ?? 0)
    .attr('x2', d => nodeById.get(d.target)?.x ?? 0)
    .attr('y2', d => nodeById.get(d.target)?.y ?? 0)
    .attr('stroke', '#58a6ff')
    .attr('stroke-width', 1.4)
    .attr('stroke-opacity', 0.084)
    .attr('filter', 'url(#edge-glow-blur)');

  // 3) 论文节点微光（降亮40%）
  const paperGlow = gh.append('g')
    .attr('class', 'paper-glow-layer')
    .attr('pointer-events', 'none');

  paperGlow.selectAll('circle.paper-glow').data(papers).join('circle')
    .attr('class', 'paper-glow')
    .attr('cx', d => d.x)
    .attr('cy', d => d.y)
    .attr('r', d => Math.max(30, d.r * 8))
    .attr('fill', d => d.color)
    .attr('fill-opacity', 0.066)
    .attr('filter', 'url(#paper-glow-blur)');

  // 4) 类标题微光（降亮40%）
  const titleGlow = gh.append('g')
    .attr('class', 'title-glow-layer')
    .attr('pointer-events', 'none');

  titleGlow.selectAll('text.cat-glow').data(categories).join('text')
    .attr('class', 'cat-glow')
    .attr('x', d => d.x)
    .attr('y', d => d.y)
    .attr('text-anchor', 'middle')
    .attr('fill', d => d.color)
    .attr('fill-opacity', 0.132)
    .style('font-size', '13px')
    .style('font-weight', 700)
    .text(d => d.label)
    .attr('filter', 'url(#title-glow-blur)');

  const paperNode = gn.selectAll('g.paper').data(papers).join('g').attr('class','paper').attr('transform', d=>`translate(${d.x},${d.y})`).attr('cursor','pointer');

  paperNode.append('circle')
    .attr('r', d=>d.r)
    .attr('fill', d=>d.color)
    .attr('fill-opacity', .88)
    .attr('stroke', '#0d1117')
    .attr('stroke-width', .6);

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

  paperNode.on('click', (_,d)=>showInfo(d));

  function updateLabelVisibility(k){ labels.style('opacity', 1); }
  updateLabelVisibility(kScale);
}

svg = d3.select('#svg');
root = d3.select('#root');
svg.call(d3.zoom().scaleExtent([0.05, 10]).on('zoom', e=>{kScale = e.transform.k; root.attr('transform', e.transform); }));

render();

setTimeout(()=>{
  const cats = G.nodes.filter(n=>n.type==='category');
  const initCat = cats.find(c => (c.label || '').includes('事故分析与应急'))
    || cats.find(c => (c.cat_id || '') === 'E_事故应急')
    || cats.find(c => (c.cat_id || '').includes('事故') || (c.label || '').includes('事故'))
    || cats.find(c => (c.cat_id || '').includes('应急') || (c.label || '').includes('应急'));

  if(initCat) {
    showInfo(initCat);
    const firstTitle = initCat.papers && initCat.papers.length ? initCat.papers[0].title : null;
    if(firstTitle){
      const firstPaper = G.nodes.find(n => n.type==='paper' && n.full_title === firstTitle);
      if(firstPaper) showInfo(firstPaper);
    }
  }
}, 500);
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
