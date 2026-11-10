'use strict';
const $ = (q) => document.querySelector(q);
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = (n) => Number(n).toLocaleString('zh-CN');
const sourceNames = {compound:'化合物数据集',bbb:'血脑屏障数据集',drugbank:'DrugBank 资料'};
const navItems = [['overview','◈','数据总览'],['explore','⌕','多源检索'],['similar','⌬','相似结构探索'],['screen','⚗','可解释筛选'],['compare','▥','候选分子对比'],['quality','◇','质量与溯源'],['history','◷','筛选记录']];
let candidates;
try {candidates = JSON.parse(localStorage.getItem('chem-candidates') || '[]'); if(!Array.isArray(candidates)) candidates=[];} catch {candidates=[];}
let screenResult = null;
let searchParams = {source:'compound',q:'',label:'',page:1,size:8};
let similarityInput = {smiles:'N1C2=C(C3=CC=CC=C3C1)C=CC=C2c9ncc[nH]9',threshold:.4};
let screenParams = {source:'compound',mw_max:500,logp_max:5,hbd_max:5,hba_max:10,psa_max:140};
let sequence=0;
const api = async (path, params, options) => {
  const response = await fetch('/api/'+path+(params?'?'+new URLSearchParams(params):''), options);
  const body = await response.json();
  if(!response.ok) throw new Error(body.error || '请求失败');
  return body;
};
function toast(message){$('#toast').textContent=message;$('#toast').style.display='block';setTimeout(()=>$('#toast').style.display='none',2800);}
function heading(title, subtitle, action=''){return `<div class="page-head"><div><div class="eyebrow">CHEM ATLAS / RESEARCH WORKSPACE</div><h1>${esc(title)}</h1><div class="subtle">${esc(subtitle)}</div></div><div class="actions">${action}</div></div>`;}
function badge(source){return `<span class="badge ${source==='compound'?'green':source==='bbb'?'':'gray'}">${sourceNames[source]||esc(source)}</span>`;}
function button(text, action, cls='secondary', extra=''){return `<button class="${cls}" data-action="${action}" ${extra}>${text}</button>`;}
function linkDetail(id){return `#detail/${encodeURIComponent(id)}`;}
function empty(message){return `<div class="empty">${message}</div>`;}
function image(id){return `/api/structure?id=${encodeURIComponent(id)}`;}
function value(v){return v == null ? '—' : esc(v);}
function sourceOptions(selected,all=true){return `${all?'<option value="">全部来源</option>':''}${Object.entries(sourceNames).map(([k,v])=>`<option value="${k}" ${selected===k?'selected':''}>${v}</option>`).join('')}`;}
function metric(label,n,note){return `<div class="metric"><div class="label">${label}</div><strong>${fmt(n)}</strong><small>${note}</small></div>`;}
function table(items, explanations=false){
  if(!items.length)return empty('没有符合条件的记录，请调整关键词或筛选条件。');
  return `<div class="table-wrap"><table><thead><tr><th>记录 / 分子表示</th><th>数据来源</th><th>MW</th><th>LogP</th><th>TPSA</th><th>来源标签</th><th>操作</th></tr></thead><tbody>${items.map(r=>`<tr><td><a href="${linkDetail(r.id)}"><strong>${esc(r.name)}</strong></a><div class="smiles" title="${esc(r.smiles||'该来源不含结构')}">${esc(r.smiles||'该来源不含结构')}</div>${explanations?`<div class="reason">${r.reasons.map(esc).join(' · ')}</div>`:''}</td><td>${badge(r.source)}</td><td>${value(r.mw)}</td><td>${value(r.logp)}</td><td>${value(r.psa)}</td><td><span class="badge gray">${esc(r.label||'未提供')}</span></td><td>${button(candidates.includes(r.id)?'已加入':'加入对比','add','link',`data-id="${esc(r.id)}" ${!r.smiles?'disabled':''}`)}</td></tr>`).join('')}</tbody></table></div>`;
}
async function overview(){
  const q = await api('overview');
  return heading('从数据出发，探索分子空间','整合本地化学数据 · 连接结构、性质与筛选证据',`<a class="button" href="#explore">开始检索 →</a>`)+
    `<div class="metrics">${metric('全部来源记录',q.sources.reduce((n,s)=>n+s.rows,0),'3 个本地数据文件')}${metric('可解析结构记录',q.structures,'RDKit 结构标准化')}${metric('唯一分子结构',q.unique_structures,'基于规范化 SMILES')}${metric('血脑屏障来源标签',10648,'实验 / 文献标签，非模型预测')}</div>`+
    `<div class="grid2"><section class="panel"><div class="panel-title"><h2>数据资产分布</h2><span class="badge green">本地索引已就绪</span></div>${q.sources.map((s,i)=>`<div class="bar-row"><div class="bar-label"><span>${sourceNames[s.source]}</span><strong>${fmt(s.rows)} 条</strong></div><div class="bar-track"><div class="bar ${i===1?'blue':i===2?'light':''}" style="width:${s.rows/14313*100}%"></div></div><small class="subtle">${esc(s.path)}</small></div>`).join('')}<div class="split-line"></div><div class="subtle">数据来源分别保留；仅对完全相同的规范化结构展示关联。</div></section>
    <section class="panel"><h2>可复核的研究流程</h2><div class="flow"><span>检索数据</span><b>→</b><span>探索结构</span><b>→</b><span>筛选归档</span></div><div class="feature"><strong>01 · 结构相似度有依据</strong><small>Morgan 指纹与 Tanimoto 系数，展示算法及阈值。</small></div><div class="feature"><strong>02 · 每个筛选结果可解释</strong><small>逐条展示性质值与条件，支持候选分子横向对比。</small></div><div class="feature"><strong>03 · 筛选记录带数据指纹</strong><small>保存命中 ID、条件、来源 SHA256 与计算库版本。</small></div><a class="button secondary" href="#screen">进入可解释筛选</a></section></div><div class="notice">性质由 RDKit ${esc(q.rdkit)} 重新计算，原始字段保存在详情中。DrugBank 资料没有 SMILES，不参与结构计算。</div>`;
}
async function explore(){
  const r=await api('search',searchParams);
  return heading('多源检索','按来源、关键词和来源标签定位研究数据',`<a class="button secondary" href="/api/export?${new URLSearchParams(searchParams)}">导出全部匹配 CSV</a>`)+
    `<form id="search-form" class="panel form-row"><label>数据来源<select name="source">${sourceOptions(searchParams.source)}</select></label><label class="wide">关键词 / ID / SMILES / 原文<input name="q" placeholder="例如 tmy0、DB00001 或 thrombin" value="${esc(searchParams.q)}"></label><label>来源标签<select name="label">${[['','全部标签'],['active','active'],['inactive','inactive'],['0','BBB 0'],['1','BBB 1']].map(([k,v])=>`<option value="${k}" ${searchParams.label===k?'selected':''}>${v}</option>`).join('')}</select></label><button type="submit">查询</button></form>`+
    `<section class="panel table-panel"><div class="panel-title"><h2>查询结果 <span class="subtle">${fmt(r.total)} 条记录</span></h2><span class="subtle">MW: g/mol · TPSA: Å²</span></div>${table(r.items)}<div class="pager"><span>第 ${r.page} / ${Math.max(1,Math.ceil(r.total/r.size))} 页 · 每页 ${r.size} 条</span><div class="actions">${button('上一页','prev','secondary',r.page===1?'disabled':'')}${button('下一页','next','secondary',r.page*r.size>=r.total?'disabled':'')}</div></div></section>`;
}
async function detail(id){
  const r = await api('detail',{id});
  const fields = Object.entries(r.payload);
  return heading(r.name+' · 记录详情','原始字段、计算性质与来源定位',`<a class="button secondary" href="#explore">返回检索</a>${r.smiles?button('加入候选对比','add','',`data-id="${esc(r.id)}"`):''}`)+
  `<div class="detail-grid"><section class="panel"><div class="panel-title"><h2>分子结构</h2>${badge(r.source)}</div>${r.canonical?`<img class="structure" src="${image(id)}" alt="${esc(r.name)} 二维分子结构"><div class="mono">${esc(r.canonical)}</div>`:empty('此记录不含可计算结构')}<div class="split-line"></div><div class="kv"><span>来源文件</span><span>${esc({compound:'compound_info.csv',bbb:'Dataset/BBB_10648.csv',drugbank:'DrugBankAll.xlsx'}[r.source])}</span></div><div class="kv"><span>原文件行号</span><span>第 ${r.source_row} 行（含表头）</span></div><div class="kv"><span>来源标签</span><span>${esc(r.label||'未提供')}</span></div>${r.smiles?button('以此结构查相似分子','use-similar','secondary',`data-smiles="${esc(r.smiles)}"`):''}</section>
  <section class="panel"><h2>${r.canonical?'计算性质与来源证据':'药物资料原文'}</h2>${r.canonical?`<div class="props">${['mw','logp','hbd','hba','psa'].map(p=>`<div class="prop"><span>${p.toUpperCase()}</span><strong>${value(r[p])}</strong></div>`).join('')}</div><p class="subtle">MW: g/mol；TPSA: Å²；HBD/HBA: 氢键供体/受体数。所有值由本版本 RDKit 统一计算。</p>`:'<div class="notice">该来源未提供分子结构，不显示推断性质。点击字段名称展开原始内容。</div>'}<div class="payload">${fields.map(([k,v],i)=>`<details ${i<2?'open':''}><summary>${esc(k)}</summary><p>${esc(v||'原始数据未提供')}</p></details>`).join('')}</div></section></div>
  <section class="panel"><h2>相同规范化结构的来源记录 <span class="subtle">${r.related_total} 条</span></h2>${r.related.length?`<div class="actions">${r.related.map(x=>`<a class="button secondary" href="${linkDetail(x.id)}">${esc(x.name)} · ${esc(x.label||'无标签')}</a>`).join('')}</div><p class="subtle">最多展示 20 条；结构完全相同的来源记录不代表实验条件相同。</p>`:'<p class="subtle">未发现其他相同规范化结构记录，或此记录没有结构。</p>'}</section>`;
}
async function similar(){
 return heading('相似结构探索','基于结构指纹寻找相似分子，保留各来源记录')+
 `<section class="panel"><form id="similar-form"><label>查询分子 SMILES<textarea name="smiles" required>${esc(similarityInput.smiles)}</textarea></label><div class="form-row" style="margin-top:14px"><label style="max-width:200px">最低 Tanimoto 相似度<input name="threshold" type="number" min="0" max="1" step="0.05" value="${similarityInput.threshold}" required></label><button type="submit">计算相似分子</button><span class="subtle">Morgan · radius 2 · 2048 bits</span></div></form></section><div class="notice">相似度表示指纹重合程度，不等同于生物活性、血脑屏障通透性或药效。结果最多展示前 60 条。</div><div id="similar-results">${empty('输入 SMILES 或从记录详情带入结构，开始探索。')}</div>`;
}
async function screen(){
 return heading('可解释筛选','用透明的性质条件缩小候选范围，每条命中均附有判断依据',button('恢复默认条件','reset-screen'))+
 `<section class="panel"><form id="screen-form"><div class="form-row"><label>候选来源<select name="source"><option value="compound" ${screenParams.source==='compound'?'selected':''}>化合物数据集</option><option value="bbb" ${screenParams.source==='bbb'?'selected':''}>血脑屏障数据集</option><option value="all" ${screenParams.source==='all'?'selected':''}>全部结构记录</option></select></label>${[['mw_max','MW 上限 (g/mol)'],['logp_max','LogP 上限'],['hbd_max','HBD 上限'],['hba_max','HBA 上限'],['psa_max','TPSA 上限 (Å²)']].map(([key,label])=>`<label>${label}<input name="${key}" type="number" step="any" min="${key==='logp_max'?-20:0}" max="${key==='logp_max'?20:10000}" value="${screenParams[key]}" required></label>`).join('')}<button type="submit">执行筛选</button></div></form></section><div class="notice">所有条件同时满足，边界值计入结果。默认条件是研究筛选参考，不构成成药性、有效性或安全性结论。</div><div id="screen-results">${screenResult?screenOutput():empty('设置上限并执行筛选，将显示命中数及逐项解释。')}</div>`;
}
function screenOutput(){
 const r=screenResult;
 return `<section class="panel table-panel"><div class="panel-title"><h2>命中 ${fmt(r.total)} 条 <span class="badge green">5 项性质条件同时满足</span></h2><a class="button secondary" href="/api/export?kind=screen&${new URLSearchParams(r.params)}">导出全部命中 CSV</a></div>${table(r.items.slice(0,6),true)}<div class="pager"><span>预览前 ${Math.min(r.total,6)} 条 · 按 MW 升序 · 导出包含全部 ${fmt(r.total)} 条</span></div></section><form id="save-form" class="panel form-row"><label>筛选记录名称<input name="name" maxlength="100" placeholder="例如：低分子量候选初筛" required></label><button type="submit">保存筛选记录</button><span class="subtle">保存条件、全部命中 ID 和数据来源指纹</span></form>`;
}
async function compare(){
 const records=await Promise.all(candidates.map(id=>api('detail',{id})));
 return heading('候选分子对比','并列检查结构和理化性质，候选列表保存在当前浏览器',button('清空候选','clear-compare'))+
 (!records.length?`<section class="panel">${empty('还没有候选分子。到检索或筛选页面点击“加入对比”，最多可加入 3 条。')}<a class="button" href="#explore">去检索分子</a></section>`:
 `<section class="panel"><div class="compare-grid">${records.map(r=>`<div class="compare-card"><div class="panel-title"><strong>${esc(r.name)}</strong>${button('移除','remove','link',`data-id="${esc(r.id)}"`)}</div>${badge(r.source)}<img src="${image(r.id)}" alt="${esc(r.name)} 结构"><div class="mono">${esc(r.smiles)}</div></div>`).join('')}</div><div class="split-line"></div><table class="compare-table"><thead><tr><th>对比指标</th>${records.map(r=>`<th>${esc(r.name)}</th>`).join('')}</tr></thead><tbody>${[['mw','分子量 MW (g/mol)'],['logp','脂水分配 LogP'],['hbd','氢键供体 HBD'],['hba','氢键受体 HBA'],['psa','极性表面积 TPSA (Å²)'],['label','原始来源标签']].map(([k,label])=>`<tr><td>${label}</td>${records.map(r=>`<td><strong>${value(r[k])}</strong></td>`).join('')}</tr>`).join('')}</tbody></table></section><div class="notice">比较使用同一版本 RDKit 计算的性质。来源标签来自各原始文件，不能作为跨实验条件的效力排序。</div>`);
}
async function quality(){
 const q=await api('quality');
 return heading('质量与溯源','从记录计数到文件指纹，核对研究结果所依据的数据')+
 `<div class="metrics">${metric('来源文件',3,'SHA256 内容校验')}${metric('非法结构',q.sources.reduce((n,s)=>n+s.invalid,0),'仅统计有结构字段的来源')}${metric('缺失结构',q.sources.reduce((n,s)=>n+s.missing,0),'DrugBank 无结构为来源设计')}${metric('源内重复记录',q.sources.reduce((n,s)=>n+s.duplicates,0),'保留重复行，呈现来源差异')}</div>`+
 `<div class="grid2"><section class="panel"><h2>文件指纹与导入证据</h2>${q.sources.map(s=>`<div class="source-card"><h3>${sourceNames[s.source]} <span class="subtle">${fmt(s.rows)} 条</span></h3><div class="subtle">${esc(s.path)} · ${new Date(s.imported).toLocaleDateString('zh-CN')}</div><div class="hash">SHA256 ${s.sha256}</div><div class="status-row"><span>非法 ${s.invalid}</span><span>缺失 ${s.missing}</span><span>源内重复 ${s.duplicates}</span></div></div>`).join('')}</section><section class="panel"><h2>质量规则与解释边界</h2><div class="feature"><strong>结构标准化</strong><small>RDKit ${q.rdkit} · 规范化 SMILES · 保留来源原文</small></div><div class="feature"><strong>重复记录识别</strong><small>${esc(q.quality_note)}</small></div><div class="feature"><strong>来源字段与计算字段并存</strong><small>主表显示统一计算值；记录详情中可展开原始字段进行核对。</small></div><div class="feature"><strong>关联证据</strong><small>仅展示规范化 SMILES 完全一致的记录，不按药物描述猜测关联。</small></div><div class="feature"><strong>研究记录复现</strong><small>筛选归档保留参数、全部命中 ID、前 100 条结果快照、文件指纹及计算库版本。</small></div></section></div>`;
}
async function history(){
 const rows=await api('runs');
 return heading('筛选记录','查看已归档的筛选条件、结果标识和来源证据',`<a class="button" href="#screen">创建筛选记录</a>`)+
 `<section class="panel table-panel"><div class="panel-title"><h2>已保存 ${rows.length} 条记录</h2><span class="subtle">持久保存于本地 SQLite</span></div>${rows.length?`<table><thead><tr><th>记录名称</th><th>创建时间</th><th>命中数量</th><th>操作</th></tr></thead><tbody>${rows.map(r=>`<tr><td><a href="#run/${r.id}"><strong>${esc(r.name)}</strong></a><div class="subtle">筛选编号 #${r.id}</div></td><td>${new Date(r.created).toLocaleString('zh-CN')}</td><td>${fmt(r.count)}</td><td><a href="/api/export?kind=run&id=${r.id}" class="button secondary">导出 JSON</a></td></tr>`).join('')}</tbody></table>`:empty('暂无筛选记录。执行筛选后输入名称并保存。')}</section>`;
}
async function runDetail(id){
 const r=await api('run',{id});
 return heading(r.name,'筛选归档 #'+r.id+' · '+new Date(r.created).toLocaleString('zh-CN'),`<a class="button secondary" href="#history">返回记录</a><a class="button" href="/api/export?kind=run&id=${r.id}">下载证据 JSON</a>`)+
 `<div class="grid2"><section class="panel"><h2>筛选条件快照</h2>${Object.entries(r.params).map(([k,v])=>`<div class="kv"><span>${esc(k)}</span><strong>${esc(v)}</strong></div>`).join('')}<div class="run-summary">命中 <strong>${fmt(r.ids.length)}</strong> 条来源记录<br>计算库 RDKit ${esc(r.provenance.rdkit)}<br>数值条件全部为包含边界的上限判断。</div></section><section class="panel"><h2>数据版本证据</h2>${r.provenance.sources.map(s=>`<div class="source-card"><h3>${esc(s.path)}</h3><div class="hash">${esc(s.sha256)}</div></div>`).join('')}<div class="notice">JSON 包含全部命中 ID 和前 100 条结果快照。复现时需同时核对原文件校验值、计算库版本与筛选参数。</div></section></div><section class="panel"><h2>命中标识预览 <span class="subtle">前 24 条 / 全部 ${fmt(r.ids.length)} 条</span></h2><div class="actions">${r.ids.slice(0,24).map(id=>`<a class="badge green" href="${linkDetail(id)}">${esc(id)}</a>`).join('')}</div></section>`;
}
async function render(){
 const current=++sequence;
 const [page, id] = (location.hash.slice(1)||'overview').split('/');
 $('#nav').innerHTML=navItems.map(([key,icon,label])=>`<a href="#${key}" class="${key===page?'active':''}"><i>${icon}</i>${label}${key==='compare'&&candidates.length?` <small>(${candidates.length})</small>`:''}</a>`).join('');
 $('#crumb').textContent=(navItems.find(x=>x[0]===page)||['','','记录详情'])[2];
 $('#main').innerHTML='<div class="busy">正在读取本地研究数据…</div>';
 try {
  const handlers={overview,explore,similar,screen,compare,quality,history};
  const html=page==='detail'?await detail(decodeURIComponent(id)):page==='run'?await runDetail(id):await (handlers[page]||overview)();
  if(current!==sequence)return;
  $('#main').innerHTML=html;
  window.scrollTo(0,0);
 }catch(e){if(current===sequence)$('#main').innerHTML=`<div class="error">${esc(e.message)}</div>`;}
}
document.addEventListener('click',async e=>{
 const b=e.target.closest('[data-action]');if(!b)return;
 try {
  const action=b.dataset.action;
  if(action==='add'){
   if(candidates.includes(b.dataset.id)){toast('该分子已在候选列表中');return;}
   if(candidates.length>=3){toast('最多对比 3 个分子，请先到候选分子对比页移除条目');return;}
   candidates.push(b.dataset.id);localStorage.setItem('chem-candidates',JSON.stringify(candidates));b.textContent='已加入';toast('已加入候选分子对比');
  }else if(action==='remove'||action==='clear-compare'){
   candidates=action==='clear-compare'?[]:candidates.filter(id=>id!==b.dataset.id);localStorage.setItem('chem-candidates',JSON.stringify(candidates));await render();
  }else if(action==='prev'||action==='next'){
   searchParams.page += action==='next'?1:-1;await render();
  }else if(action==='use-similar'){
   similarityInput.smiles=b.dataset.smiles;location.hash='similar';
  }else if(action==='reset-screen'){
   screenParams={source:'compound',mw_max:500,logp_max:5,hbd_max:5,hba_max:10,psa_max:140};screenResult=null;await render();
  }
 }catch(err){toast(err.message);}
});
document.addEventListener('submit',async e=>{
 const form=e.target;if(!['search-form','similar-form','screen-form','save-form'].includes(form.id))return;e.preventDefault();
 const params=Object.fromEntries(new FormData(form));
 const submit=form.querySelector('button[type="submit"]');if(submit)submit.disabled=true;
 const requestSequence=sequence;
 try{
  if(form.id==='search-form'){searchParams={...searchParams,...params,page:1};await render();}
  if(form.id==='similar-form'){
   similarityInput=params;$('#similar-results').innerHTML='<div class="busy">正在计算结构指纹相似度…</div>';
   const r=await api('similar',params);if(requestSequence!==sequence)return;
   $('#similar-results').innerHTML=`<section class="panel"><div class="panel-title"><h2>匹配 ${fmt(r.total)} 条 <span class="subtle">当前展示前 ${Math.min(r.total,6)} 条</span></h2><span class="badge green">阈值 ≥ ${r.threshold}</span></div>${r.items.length?r.items.slice(0,6).map(x=>`<div class="result-row"><img src="${image(x.id)}" alt="${esc(x.name)} 结构"><div><a href="${linkDetail(x.id)}"><strong>${esc(x.name)}</strong></a> ${badge(x.source)}<div class="smiles">${esc(x.smiles)}</div><span class="subtle">MW ${x.mw} · LogP ${x.logp}</span> ${button('加入对比','add','link',`data-id="${esc(x.id)}"`)}</div><div class="score">${x.similarity.toFixed(3)}<small>TANIMOTO 相似度</small></div></div>`).join(''):empty('该阈值下没有匹配结构，请降低阈值。')}<details><summary class="subtle">展开其余结果（最多前 60 条）</summary>${table(r.items.slice(6))}</details></section>`;
  }
  if(form.id==='screen-form'){
   screenParams=params;const r=await api('screen',params);if(requestSequence!==sequence)return;screenResult=r;$('#screen-results').innerHTML=screenOutput();
  }
  if(form.id==='save-form'){
   const r=await api('runs',null,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:params.name,params:screenResult.params,ids:screenResult.ids})});
   if(requestSequence!==sequence)return;toast('筛选记录已保存');location.hash='run/'+r.id;
  }
 }catch(err){
  if(requestSequence!==sequence)return;
  const target=form.id==='similar-form'?$('#similar-results'):form.id==='screen-form'?$('#screen-results'):null;
  if(target)target.innerHTML=`<div class="error">${esc(err.message)}</div>`;else toast(err.message);
 }finally{if(submit)submit.disabled=false;}
});
window.addEventListener('hashchange',render);
render();
