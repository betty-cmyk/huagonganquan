# -*- coding: utf-8 -*-
"""
build_site.py  —  生成最终 docs/index.html
修复：1)去掉全部视图 2)默认研究分类视图 3)点击/悬停正常
"""
import os, json

CRAWLER_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(CRAWLER_DIR, '..', 'data')
ROOT        = os.path.join(CRAWLER_DIR, '..', '..')
DOCS_DIR    = os.path.join(ROOT, 'docs')
GRAPH_JSON  = os.path.abspath(os.path.join(DATA_DIR, 'graph_v2.json'))
OUT_HTML    = os.path.abspath(os.path.join(DOCS_DIR, 'index.html'))

HTML_TPL = '''\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>化工安全论文知识关联图</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0d1117;color:#e6edf3;font-family:'Noto Sans SC',sans-serif;overflow:hidden}}
#app{{width:100vw;height:100vh;display:flex}}
#sidebar{{width:320px;min-width:320px;height:100vh;background:#161b22;border-right:1px solid #30363d;display:flex;flex-direction:column;transition:width .3s;overflow:hidden}}
#sidebar.collapsed{{width:0;min-width:0}}
#sb-header{{padding:14px 16px;border-bottom:1px solid #30363d;display:flex;justify-content:space-between;align-items:center}}
#sb-title{{font-size:14px;color:#79c0ff;font-weight:bold;flex:1;margin-right:8px}}
#sb-toggle{{background:none;border:1px solid #30363d;color:#8b949e;border-radius:4px;padding:2px 8px;cursor:pointer;font-size:12px;white-space:nowrap}}
#sb-toggle:hover{{background:#21262d;color:#e6edf3}}
#sb-stats{{padding:8px 16px;border-bottom:1px solid #21262d;font-size:12px;color:#8b949e;display:none}}
#sb-stats span{{color:#f78166;font-weight:bold}}
#sb-list{{flex:1;overflow-y:auto;padding:4px 0}}
#sb-list::-webkit-scrollbar{{width:4px}}
#sb-list::-webkit-scrollbar-thumb{{background:#30363d;border-radius:2px}}
.sb-item{{padding:8px 16px;border-bottom:1px solid #21262d;transition:background .15s}}
.sb-item:hover{{background:#21262d}}
.sb-item-title{{font-size:12px;color:#e6edf3;line-height:1.5;margin-bottom:3px}}
.sb-item-meta{{font-size:11px;color:#8b949e}}
.sb-yr{{display:inline-block;background:#21262d;border-radius:3px;padding:0 5px;margin-right:4px;color:#56d364}}
.sb-ph{{padding:40px 20px;text-align:center;color:#8b949e;font-size:13px;line-height:2}}
#graph-wrap{{flex:1;position:relative;overflow:hidden}}
svg{{width:100%;height:100%}}
#legend{{position:absolute;top:16px;right:16px;background:rgba(22,27,34,.93);border:1px solid #30363d;border-radius:8px;padding:12px 16px;font-size:12px}}
#legend h3{{font-size:13px;color:#79c0ff;margin-bottom:8px}}
.lr{{display:flex;align-items:center;gap:7px;margin:4px 0}}
.ld{{width:12px;height:12px;border-radius:50%;flex-shrink:0}}
#controls{{position:absolute;bottom:16px;left:50%;transform:translateX(-50%);display:flex;gap:8px}}
button{{background:#21262d;border:1px solid #30363d;color:#e6edf3;border-radius:6px;padding:6px 14px;cursor:pointer;font-size:12px;transition:background .2s}}
button:hover{{background:#388bfd;border-color:#388bfd}}
button.active{{background:#388bfd;border-color:#388bfd}}
#tt{{position:fixed;pointer-events:none;background:rgba(13,17,23,.97);border:1px solid #388bfd;border-radius:7px;padding:10px 14px;font-size:12px;max-width:260px;display:none;line-height:1.8;z-index:9999;box-shadow:0 4px 20px rgba(0,0,0,.5)}}
#tt .ttn{{font-weight:bold;color:#79c0ff;margin-bottom:4px;font-size:13px}}
#tt .ttp{{color:#e6edf3}}
#tt .ttl{{margin-top:6px;border-top:1px solid #30363d;padding-top:6px;max-height:160px;overflow-y:auto}}
#tt .ttli{{color:#8b949e;font-size:11px;padding:2px 0;border-bottom:1px solid #21262d}}
#tt .ttli:last-child{{border:none}}
</style>
</head>
<body>
<div id="app">
  <div id="sidebar">
    <div id="sb-header">
      <span id="sb-title">点击节点查看论文列表</span>
      <button id="sb-toggle" onclick="toggleSB()">收起</button>
    </div>
    <div id="sb-stats"><div id="sb-st"></div></div>
    <div id="sb-list"><div class="sb-ph">&#128070; 点击图中节点<br>在此查看该方向下的<br>所有论文标题</div></div>
  </div>
  <div id="graph-wrap">
    <svg id="svg">
      <defs><marker id="arr" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L0,6 L6,3 z" fill="#3d444d"/></marker></defs>
      <g id="root"><g id="ge"></g><g id="gn"></g></g>
    </svg>
    <div id="legend">
      <h3>图例</h3>
      <div class="lr"><div class="ld" style="background:#f78166"></div>搜索关键词</div>
      <div class="lr"><div class="ld" style="background:#79c0ff"></div>研究分类</div>
      <div class="lr"><div class="ld" style="background:#56d364"></div>发表年份</div>
      <div style="margin-top:8px;color:#8b949e;line-height:1.9;font-size:11px">节点大小 = 论文数<br>线宽 = 关联强度<br>&#128073; 点击节点看论文<br>滚轮缩放 · 拖拽节点</div>
    </div>
    <div id="controls">
      <button id="b-kw"  onclick="setView('keyword')">搜索词视图</button>
      <button id="b-cat" onclick="setView('category')" class="active">研究分类视图</button>
      <button id="b-yr"  onclick="setView('year')">年份视图</button>
      <button onclick="resetV()">重置视图</button>
    </div>
    <div id="tt"></div>
  </div>
</div>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const G = {GRAPH_DATA};
const AN = G.nodes, AE = G.edges;
let svg, root, zoom, sim, sbOpen=true, curView='category';

function toggleSB(){{sbOpen=!sbOpen;document.getElementById('sidebar').classList.toggle('collapsed',!sbOpen);document.getElementById('sb-toggle').textContent=sbOpen?'收起':'展开';}}

function showPapers(d){{
  const papers=(d.papers||[]).slice().sort((a,b)=>((b.year||'0')<(a.year||'0')?-1:1));
  document.getElementById('sb-title').textContent=d.label+' ('+d.count+'篇)';
  const st=document.getElementById('sb-stats'); st.style.display='block';
  document.getElementById('sb-st').innerHTML='共 <span>'+papers.length+'</span> 篇论文';
  if(!papers.length){{document.getElementById('sb-list').innerHTML='<div class="sb-ph">该节点无直接论文数据</div>';return;}}
  document.getElementById('sb-list').innerHTML=papers.map((p,i)=>
    '<div class="sb-item"><div class="sb-item-title">'+(i+1)+'. '+p.title+'</div>'
    +'<div class="sb-item-meta"><span class="sb-yr">'+(p.year||'?')+'</span>'+(p.author||'')+' '+(p.unit?'· '+p.unit:'')+'</div></div>'
  ).join('');
  if(!sbOpen) toggleSB();
}}

function nR(n){{return n.type==='keyword'?Math.sqrt(n.count)*7+22:n.type==='category'?Math.sqrt(n.count)*5+13:Math.sqrt(n.count)*3+9;}}

function setView(t){{
  curView=t;
  [['b-kw','keyword'],['b-cat','category'],['b-yr','year']].forEach(([id,v])=>document.getElementById(id).classList.toggle('active',v===t));
  const nodes=AN.filter(n=>n.type===t);
  render(nodes,AE);
}}

function resetV(){{svg.transition().duration(600).call(zoom.transform,d3.zoomIdentity);}}

function render(nodes,edges){{
  const ids=new Set(nodes.map(n=>n.id));
  const ve=edges.filter(e=>{{const s=e.source?.id??e.source,t2=e.target?.id??e.target;return ids.has(s)&&ids.has(t2);}});
  const nm={{}};const sn=nodes.map(n=>{{const c={{...n}};nm[n.id]=c;return c;}});
  const se=ve.map(e=>{{return{{...e,source:nm[e.source?.id??e.source],target:nm[e.target?.id??e.target]}};}});
  if(sim) sim.stop();
  const W=document.getElementById('graph-wrap').clientWidth, H=window.innerHeight;
  sim=d3.forceSimulation(sn)
    .force('link',d3.forceLink(se).distance(d=>130-d.weight*1.2).strength(0.4))
    .force('charge',d3.forceManyBody().strength(-300))
    .force('center',d3.forceCenter(W/2,H/2))
    .force('collision',d3.forceCollide().radius(n=>nR(n)+10));
  const ge=d3.select('#ge');ge.selectAll('*').remove();
  const link=ge.selectAll('line').data(se).join('line')
    .attr('stroke','#3d444d').attr('stroke-width',d=>Math.sqrt(d.weight)+0.5)
    .attr('stroke-opacity',0.6).attr('marker-end','url(#arr)');
  const gn=d3.select('#gn');gn.selectAll('*').remove();
  const node=gn.selectAll('g').data(sn).join('g').attr('cursor','pointer')
    .call(d3.drag()
      .on('start',(e,d)=>{{if(!e.active)sim.alphaTarget(0.3).restart();d.fx=d.x;d.fy=d.y;}})
      .on('drag',(e,d)=>{{d.fx=e.x;d.fy=e.y;}})
      .on('end',(e,d)=>{{if(!e.active)sim.alphaTarget(0);d.fx=null;d.fy=null;}}));
  node.append('circle').attr('r',nR).attr('fill',n=>n.color||'#8b949e')
    .attr('fill-opacity',0.85).attr('stroke',n=>n.color||'#8b949e')
    .attr('stroke-width',2).attr('stroke-opacity',0.35);
  node.append('text').text(n=>n.label).attr('text-anchor','middle')
    .attr('dy',n=>nR(n)+13).attr('font-size',n=>n.type==='keyword'?13:n.type==='category'?12:11)
    .attr('fill',n=>n.color||'#8b949e').attr('font-weight',n=>n.type==='keyword'?'bold':'normal')
    .attr('pointer-events','none');
  const tt=document.getElementById('tt');
  node.on('mouseover',(e,d)=>{{  
    const ps=(d.papers||[]).slice(0,5);
    const typeL={{keyword:'搜索词',category:'研究分类',year:'发表年份'}};
    tt.innerHTML='<div class="ttn">'+d.label+'</div>'
      +'<div class="ttp">类型：'+typeL[d.type]+' &nbsp;|&nbsp; 论文数：'+d.count+' 篇</div>'
      +(ps.length?'<div class="ttl">'+ps.map(p=>'<div class="ttli">'+(p.year?'['+p.year+'] ':'')+p.title+'</div>').join('')
        +(d.papers.length>5?'<div class="ttli" style="color:#388bfd">...还有'+(d.papers.length-5)+'篇，点击查看全部</div>':'')+'</div>':'');
    tt.style.display='block';
  }}).on('mousemove',(e)=>{{tt.style.left=(e.clientX+16)+'px';tt.style.top=(e.clientY-10)+'px';}}).on('mouseout',()=>{{tt.style.display='none';}});
  node.on('click',(e,d)=>{{showPapers(d);e.stopPropagation();}});
  svg.on('click',()=>{{node.select('circle').attr('fill-opacity',0.85);link.attr('stroke-opacity',0.6);}});
  sim.on('tick',()=>{{link.attr('x1',d=>d.source.x).attr('y1',d=>d.source.y).attr('x2',d=>d.target.x).attr('y2',d=>d.target.y);node.attr('transform',d=>`translate(${d.x},${d.y})`);}}); 
}}

svg=d3.select('#svg');root=d3.select('#root');
zoom=d3.zoom().scaleExtent([0.1,6]).on('zoom',e=>root.attr('transform',e.transform));
svg.call(zoom);
setView('category');
</script>
</body></html>
'''

def main():
    with open(GRAPH_JSON, 'r', encoding='utf-8') as f:
        gdata = f.read()
    html = HTML_TPL.replace('{GRAPH_DATA}', gdata)

    # 修复 Python str.format 导致的 CSS/JS 双括号问题
    # 只处理 <style> 块和 <script> 的 JS 逻辑部分（跳过 JSON 数据）
    style_s = html.find('<style>') + len('<style>')
    style_e = html.find('</style>')
    html = html[:style_s] + html[style_s:style_e].replace('{{','{').replace('}}','}') + html[style_e:]

    # JS 逻辑部分（const AN 之后）
    an_idx  = html.rfind('const AN')
    js_end  = html.rfind('</script>')
    html = html[:an_idx] + html[an_idx:js_end].replace('{{','{').replace('}}','}') + html[js_end:]

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(OUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html)
    print('生成完成：' + OUT_HTML + '  (' + str(len(html)) + ' 字符)')

if __name__ == '__main__':
    main()

