import {fipsToCode, expandInventory, filteredBills, stateCounts, matches, monthEnd, safeUrl, billDate, searchPlan} from './model.js';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const shortDate = value => new Date(value+'T12:00:00Z').toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric',timeZone:'UTC'});
const colors = ['#3d5a80','#8d6b4a','#6d7c93','#b08968','#2f4858','#c4a574','#5c6b7a','#7a5c58','#4c6a8a','#a3846b','#3e5166','#9a7b63','#6e5a4e','#4e6e82','#8a7358','#556070'];
const pageSize = 40;
let data, taxonomy, issues, geography, playing = null, states = {}, listLimit = pageSize;
let filters = {state:'all',topic:'all',issue:'all',date:'2025-12-31',search:'',issueQuery:'',reviewed:false};
let month = 11, raised = false, latestCounts = {};
function mapFill(count, max) {
  if (!count) return '#e7e3d8';
  const t = count / max;
  return `rgb(${Math.round(213 - t * 183)},${Math.round(222 - t * 164)},${Math.round(234 - t * 139)})`;
}
function stop(){if(playing)clearInterval(playing);playing=null;$('play').innerHTML='<span aria-hidden="true">▶</span> Play';$('play').setAttribute('aria-label','Play timeline');}
function selectState(state){listLimit=pageSize;filters.state=filters.state===state?'all':state;render();}
function setUrl(){const params = new URLSearchParams();for(const key of ['state','topic','issue'])if(filters[key]!=='all')params.set(key,filters[key]);if(month!==11)params.set('month',month);if(filters.search)params.set('q',filters.search);if(filters.issueQuery.trim())params.set('iq',filters.issueQuery);if(filters.reviewed)params.set('reviewed','1');if(raised)params.set('view','raised');history.replaceState(null,'',`${location.pathname}${params.size?'?'+params:''}`);}
function issueSearchNote(hits){
 const query = filters.issueQuery.trim();
 if(!query)return 'Finds a related issue, then bills that use those words. Not a legal finding.';
 if(!hits.length)return 'No listed issue for that wording. Showing bills that use those words.';
 const names = hits.slice(0,3).map(hit=>hit.name);
 const extra = hits.length>3?` and ${hits.length-3} more`:'';
 return `Related issues: ${names.join(', ')}${extra}. Labeled bills come first, then wording matches.`;
}
function topicName(id){return taxonomy.topics.find(t=>t.id===id)?.name ?? id;}
function issueName(id){return issues.issue_tags.find(t=>t.id===id)?.name ?? id;}
function topicTags(bill){return (bill.policy_topics??[]).map(t=>`<span class="tag">${esc(topicName(t))}</span>`).join('') + (bill.issue_tags??[]).map(t=>`<span class="tag issue">${esc(issueName(t))}</span>`).join('');}
function billLabel(number){return number.replace(/([A-Za-z]+)0*(\d+)/,'$1 $2');}
function render(){
 const plan=filters.issueQuery.trim()?searchPlan(filters.issueQuery,issues.issue_tags):null;
 const issueHits=plan?.hits??[];
 const view={...filters,issueMatches:plan?issueHits.map(hit=>hit.id):null,issuePhrases:plan?plan.phrases:null};
 const bills=filteredBills(data.bills,view), counts=stateCounts(data.bills,view,Object.keys(states)), max=Math.max(1,...Object.values(counts));
 latestCounts=counts;
 const date=new Date(filters.date+'T12:00:00Z').toLocaleDateString('en-US',{month:'long',year:'numeric',timeZone:'UTC'});
 const shown=bills.slice(0,listLimit);
 $('total-count').textContent=bills.length;$('bill-count').textContent=bills.length;$('through-label').textContent=`through ${date}`;$('timeline-date').textContent=date;
 $('map-title').textContent=filters.topic==='all'?'All policy topics':topicName(filters.topic);
 $('bill-geography').textContent=filters.state==='all'?'ALL STATES':states[filters.state].name.toUpperCase();
 $('state-filter').value=filters.state;$('issue-filter').value=filters.issue;$('issue-search-note').textContent=issueSearchNote(issueHits);$('reviewed').checked=filters.reviewed;$('timeline').value=month;
 $('issue-suggestions').innerHTML=issueHits.slice(0,6).map(hit=>`<button type="button" class="issue-chip ${filters.issue===hit.id?'active':''}" data-issue="${hit.id}" aria-pressed="${filters.issue===hit.id}">${esc(hit.name)}</button>`).join('');
 $('view-flat').setAttribute('aria-pressed',String(!raised));$('view-raised').setAttribute('aria-pressed',String(raised));$('map-wrap').classList.toggle('raised',raised);
 $('map-scene').setAttribute('transform',raised?'translate(8 28) scale(0.95) skewX(-14)':'');
 document.querySelectorAll('.topic-button').forEach(el=>{const active=el.dataset.topic===filters.topic;el.classList.toggle('active',active);el.setAttribute('aria-pressed',active);});
 for(const [code,info] of Object.entries(states)){
  const path=$('state-'+info.fips), shadow=$('shadow-'+info.fips), count=counts[code];
  const lift=raised&&count?4+(count/max)*30:0;
  path.style.fill=mapFill(count,max);
  const base=lift?`translate(0 ${(-lift).toFixed(1)})`:'';
  path.dataset.base=base;
  if(base)path.setAttribute('transform',base);else path.removeAttribute('transform');
  if(shadow){
    if(lift)shadow.setAttribute('transform',`translate(4 ${(lift*0.42).toFixed(1)})`);
    else shadow.removeAttribute('transform');
    shadow.style.opacity=lift?'0.45':'0';
  }
  path.classList.toggle('selected',filters.state===code);path.classList.toggle('dimmed',filters.state!=='all'&&filters.state!==code);
  path.setAttribute('aria-pressed',filters.state===code);path.setAttribute('aria-label',`${info.name}, ${count} matching bills. Select state.`);
 }
 $('legend-range').textContent=max===1?'1 match':`1–${max} matches`;
 $('state-comparison').innerHTML=Object.entries(states).sort((a,b)=>a[1].name.localeCompare(b[1].name)).map(([code,info])=>`<button class="state-card ${filters.state===code?'active':''}" data-state="${code}" aria-pressed="${filters.state===code}"><span>${info.name}<small>Bills</small></span><strong>${counts[code]}</strong></button>`).join('');
 const empty=filters.reviewed?'Nothing in this snapshot has an independently reviewed topic label. Turn off “Reviewed labels only” to explore proposed labels.':'Try another topic, clear your search, or move the timeline forward.';
 $('bill-list').innerHTML=shown.length?shown.map(bill=>`<article class="bill-item"><div class="bill-meta"><span class="bill-id"><span class="state-abbr">${bill.state}</span>${esc(billLabel(bill.bill_number))}</span><time datetime="${billDate(bill)}">${shortDate(billDate(bill))}</time></div><button class="bill-title" data-bill="${esc(bill.id)}">${esc(bill.title)}</button><p class="bill-summary">${esc(bill.summary)}</p><div class="tags">${topicTags(bill)}</div><span class="proposed">${bill.status==='enacted'?'Source-checked enactment · labels still need review':'Passed by the legislature · signature not verified'}</span></article>`).join(''):`<div class="empty"><strong>No matching bills</strong>${empty}</div>`;
 $('show-more').hidden=bills.length<=shown.length;
 $('show-more').textContent=`Show more bills (${Math.max(0,bills.length-shown.length)} remaining)`;
 const months=Array.from({length:12},(_,i)=>data.bills.filter(b=>matches(b,{...view,date:'2025-12-31'})&&Number(billDate(b).slice(5,7))-1===i).length), peak=Math.max(1,...months);
 $('timeline-chart').innerHTML=months.map((count,i)=>`<div class="chart-bar ${i>month?'future':''}" style="height:${Math.max(2,count/peak*38)}px"></div>`).join('');
 $('timeline').setAttribute('aria-valuetext',date);
 $('announcement').textContent=`${bills.length} matching bills through ${date}.`;
 setUrl();
}
function showBill(id){
 const bill=data.bills.find(b=>b.id===id);if(!bill)return;
 const sources=(bill.sources??[]).map(s=>{const href=safeUrl(s.url);return href?`<a class="detail-source" href="${esc(href)}" target="_blank" rel="noopener noreferrer">${esc(s.label)}</a>`:'';}).join('');
 const when=billDate(bill);
 const enacted=bill.status==='enacted';
 const evidence=bill.classification?.evidence?.[0]?.excerpt;
 const limitations=(bill.summary_limitations??[]).map(note=>`<li>${esc(note)}</li>`).join('');
 $('detail-body').innerHTML=`<p class="detail-label">${states[bill.state].name} · ${esc(bill.bill_number)} · ${esc(bill.session_id)}</p><h2>${esc(bill.title)}</h2><div class="tags">${topicTags(bill)}</div><span class="proposed">${enacted?'Source-checked enactment · topic labels are not independently reviewed':'Passed by the legislature · signature not verified · topic labels are keyword proposals'}</span><div class="detail-dates"><div><span class="detail-label">${enacted?'Enacted':'Legislature status date'}</span><strong>${when?shortDate(when):'Not recorded'}</strong></div>${enacted?`<div><span class="detail-label">Effective</span><strong>${bill.dates.effective?shortDate(bill.dates.effective):'Not established in sample'}</strong></div>`:''}</div>${enacted?'':`<p>LegiScan recorded this bill as passed. This snapshot does not verify a governor's signature or a chapter number.</p>`}<h3>Selected provisions</h3><p>${esc(bill.summary)}</p><p class="detail-label">${esc(bill.summary_provenance??'')}</p>${limitations?`<h3>Scope and exceptions</h3><ul>${limitations}</ul>`:''}${bill.effective_date_note?`<p><strong>Effective-date note:</strong> ${esc(bill.effective_date_note)}</p>`:''}${enacted?`<h3>Source traceability</h3><p>Historical enactment and selected provisions were checked against official sources by an AI assistant. This is separate from independent topic review.</p>${(bill.source_claims??[]).map(claim=>`<p class="detail-label">Checked ${esc(claim.checked_on)} · ${esc(claim.source_locator)}</p>`).join('')}`:''}${evidence?`<h3>Why these labels?</h3><div class="evidence">“${esc(evidence)}”</div><p>This phrase comes from the PolyViz summary. It supports exploring these proposed labels, but is not independent validation.</p>`:''}${(bill.affected_sectors??[]).length?`<p><strong>Affected sector:</strong> ${bill.affected_sectors.map(sector=>esc(issues.affected_sectors.find(item=>item.id===sector)?.name??sector)).join(', ')}</p>`:''}<h3>Check the official source</h3>${sources||'<p>No source link was stored for this bill.</p>'}`;
 stop();$('detail-dialog').showModal();
}
async function init(){
 const [curated,inventory,topicFile,issueFile,geoFile]=await Promise.all(['bills','inventory','topics','issues','states'].map(async name=>{const response=await fetch(`data/${name}.json`);if(!response.ok)throw new Error(`Could not load ${name}`);return response.json();}));
 data={...curated,bills:[...curated.bills,...expandInventory(inventory)]};
 taxonomy=topicFile;issues=issueFile;geography=geoFile;
 const params=new URLSearchParams(location.search);
 states={};
 for(const geo of geography){
  const code=fipsToCode[geo.id];
  if(code)states[code]={name:geo.name,fips:geo.id};
 }
 if(params.get('state') in states)filters.state=params.get('state');
 if(taxonomy.topics.some(t=>t.id===params.get('topic')))filters.topic=params.get('topic');
 if(issues.issue_tags.some(t=>t.id===params.get('issue')))filters.issue=params.get('issue');
 if(params.has('month')&&/^\d+$/.test(params.get('month'))&&Number(params.get('month'))<=11)month=Number(params.get('month'));
 raised=params.get('view')==='raised';
 filters.date=monthEnd(month);filters.search=params.get('q')??'';filters.issueQuery=params.get('iq')??'';filters.reviewed=params.get('reviewed')==='1';$('search').value=filters.search;$('issue-search').value=filters.issueQuery;
 $('sample-count').textContent=data.bills.length.toLocaleString('en-US');
 $('enacted-count').textContent=curated.bills.length;
 $('state-filter').innerHTML='<option value="all">All states</option>'+Object.entries(states).sort((a,b)=>a[1].name.localeCompare(b[1].name)).map(([code,info])=>`<option value="${code}">${esc(info.name)}</option>`).join('');
 $('topic-filters').innerHTML=[{id:'all',name:'All policy topics'},...taxonomy.topics].map((topic,i)=>`<button class="topic-button" data-topic="${topic.id}" style="--topic-color:${colors[i%colors.length]}" aria-pressed="false"><span class="topic-dot" aria-hidden="true"></span>${esc(topic.name)}</button>`).join('');
 $('issue-filter').innerHTML='<option value="all">All issues</option>'+issues.issue_tags.map(issue=>`<option value="${issue.id}">${esc(issue.name)}</option>`).join('');
 const svgNS='http://www.w3.org/2000/svg';
 function showHover(code){const info=states[code];if(!info)return;const count=latestCounts[code]??0;$('map-hover').hidden=false;$('map-hover').textContent=`${info.name} · ${count.toLocaleString('en-US')} matching ${count===1?'bill':'bills'}`;}
 for(const geo of geography){
  const code=fipsToCode[geo.id],path=document.createElementNS(svgNS,'path');path.setAttribute('d',geo.path);path.id='state-'+geo.id;path.classList.add('state-path');
  const shadow=document.createElementNS(svgNS,'path');shadow.setAttribute('d',geo.path);shadow.id='shadow-'+geo.id;shadow.classList.add('state-shadow');$('state-shadows').append(shadow);
  const title=document.createElementNS(svgNS,'title');title.textContent=geo.name;path.append(title);
  if(code&&states[code]){path.classList.add('covered');path.setAttribute('role','button');path.setAttribute('tabindex','0');path.addEventListener('click',()=>selectState(code));path.addEventListener('keydown',event=>{if(['Enter',' '].includes(event.key)){event.preventDefault();selectState(code);}});path.addEventListener('pointerenter',()=>{showHover(code);const base=path.dataset.base;if(base)path.setAttribute('transform',`${base} translate(0 -7)`);});path.addEventListener('pointerleave',()=>{$('map-hover').hidden=true;const base=path.dataset.base;if(base)path.setAttribute('transform',base);else path.removeAttribute('transform');});}
  $('state-paths').append(path);
 }
 $('topic-filters').addEventListener('click',event=>{const button=event.target.closest('[data-topic]');if(button){listLimit=pageSize;filters.topic=button.dataset.topic;render();}});
 $('state-comparison').addEventListener('click',event=>{const button=event.target.closest('[data-state]');if(button)selectState(button.dataset.state);});
 $('state-filter').addEventListener('change',event=>{listLimit=pageSize;filters.state=event.target.value;render();});
 $('issue-filter').addEventListener('change',event=>{listLimit=pageSize;filters.issue=event.target.value;render();});
 $('issue-search').addEventListener('input',event=>{listLimit=pageSize;filters.issueQuery=event.target.value;render();});
 $('issue-suggestions').addEventListener('click',event=>{const button=event.target.closest('[data-issue]');if(!button)return;listLimit=pageSize;filters.issue=filters.issue===button.dataset.issue?'all':button.dataset.issue;render();});
 $('view-flat').addEventListener('click',()=>{raised=false;render();});
 $('view-raised').addEventListener('click',()=>{raised=true;render();});
 $('reviewed').addEventListener('change',event=>{listLimit=pageSize;filters.reviewed=event.target.checked;render();});
 $('search').addEventListener('input',event=>{listLimit=pageSize;filters.search=event.target.value;render();});
 $('timeline').addEventListener('input',event=>{stop();listLimit=pageSize;month=Number(event.target.value);filters.date=monthEnd(month);render();});
 $('play').addEventListener('click',()=>{if(playing){stop();return;}if(month===11)month=-1;playing=setInterval(()=>{month++;filters.date=monthEnd(month);render();if(month===11)stop();},900);$('play').innerHTML='<span aria-hidden="true">Ⅱ</span> Pause';$('play').setAttribute('aria-label','Pause timeline');});
 $('reset').addEventListener('click',()=>{stop();listLimit=pageSize;filters={state:'all',topic:'all',issue:'all',date:'2025-12-31',search:'',issueQuery:'',reviewed:false};month=11;raised=false;$('search').value='';$('issue-search').value='';$('map-hover').hidden=true;render();});
 $('show-more').addEventListener('click',()=>{listLimit+=pageSize;render();});
 $('bill-list').addEventListener('click',event=>{const button=event.target.closest('[data-bill]');if(button)showBill(button.dataset.bill);});
 for(const id of ['about-button','methodology-button'])$(id).addEventListener('click',()=>{stop();$('about-dialog').showModal();});
 $('close-detail').addEventListener('click',()=>$('detail-dialog').close());$('close-about').addEventListener('click',()=>$('about-dialog').close());
 $('download-data').addEventListener('click',()=>{const url=URL.createObjectURL(new Blob([JSON.stringify({schema_version:2,bills:data.bills},null,2)],{type:'application/json'}));const anchor=document.createElement('a');anchor.href=url;anchor.download='polyviz-2025-bills.json';anchor.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
 document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
 render();
}
init().catch(error=>{$('bill-list').textContent='The bills could not load. Please refresh or serve this folder over HTTP.';$('total-count').textContent='—';$('bill-count').textContent='—';$('announcement').textContent=error.message;console.error(error);});
