javascript:(function(){
  var results = [];

  // 获取当前关键词
  var keyword = '';
  var swMatch = location.href.match(/[?&]sw=([^&]+)/);
  if(swMatch){ try{ keyword=decodeURIComponent(swMatch[1]); }catch(e){ keyword=swMatch[1]; } }
  var inp = document.querySelector('input[name=sw],input[name=keyword],input[type=search]');
  if(inp && inp.value) keyword = inp.value;

  // 获取当前页码
  var pageMatch = location.href.match(/page[Nn]o=([0-9]+)/);
  var page = pageMatch ? pageMatch[1] : '1';

  // === 提取所有 <a> 标题（过滤导航链接）===
  var links = document.querySelectorAll('a');
  links.forEach(function(a){
    var txt = (a.innerText || a.textContent || '').trim();
    // 标题特征：8~80字，纯中文/中英混合，排除按钮/导航
    if(txt.length >= 8 && txt.length <= 80
      && /[\u4e00-\u9fa5]{4,}/.test(txt)
      && !/^(登录|注册|首页|搜索|下载|帮助|关于|更多|上一页|下一页|返回|查看|全文|收藏|引用|分享|导出|期刊|学位|会议|专利)$/.test(txt)
    ){
      results.push({
        title: txt,
        href: a.href || ''
      });
    }
  });

  // 去重
  var seen = {}; var uniq = [];
  results.forEach(function(r){
    if(!seen[r.title]){ seen[r.title]=1; uniq.push(r); }
  });

  if(uniq.length === 0){
    alert('未提取到标题！请确认已登录并在搜索结果页。'); return;
  }

  // 生成 JSON 并下载
  var ts = new Date().toISOString().slice(0,10);
  var fname = 'titles_' + (keyword||'未知') + '_p' + page + '_' + ts + '.json';
  var out = JSON.stringify({
    keyword: keyword,
    page: page,
    url: location.href,
    date: ts,
    count: uniq.length,
    titles: uniq
  }, null, 2);

  var blob = new Blob([out],{type:'application/json;charset=utf-8'});
  var url  = URL.createObjectURL(blob);
  var a    = document.createElement('a');
  a.href=url; a.download=fname;
  document.body.appendChild(a); a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  alert('已提取 '+uniq.length+' 条标题\n文件：'+fname+'\n\n请将文件放入 01_文献调研/data/ 目录');
})();