import {states, filteredBills, stateCounts, matches, monthEnd, safeUrl} from './model.js';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const shortDate = value => new Date(value+'T12:00:00Z').toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric',timeZone:'UTC'});
const colors = ['#6b9490','#8eaa84','#7190ab','#c5a576','#8a9b6e','#c1a76a','#9a88af','#9e8c85','#be8c7f','#a5a1bb','#9bafbb','#8c9caa','#739ca1','#a6a384','#9fae7c','#ab8fa2'];
let data, taxonomy, issues, geography, playing = null;
let filters = {state:'all',topic:'all',issue:'all',date:'2025-12-31',search:'',reviewed:false};
let month = 11;
function stop(){if(playing)clearInterval(playing);playing=null;$('play').innerHTML='<span aria-hidden="true">▶</span> Play';$('play').setAttribute('aria-label','Play timeline');}
function selectState(state){filters.state=filters.state===state?'all':state;render();}
function setUrl(){const params = new URLSearchParams();for(const key of ['state','topic','issue'])if(filters[key]!=='all')params.set(key,filters[key]);if(month!==11)params.set('month',month);if(filters.search)params.set('q',filters.search);if(filters.reviewed)params.set('reviewed','1');history.replaceState(null,'',`${location.pathname}${params.size?'?'+params:''}`);}
function topicName(id){return taxonomy.topics.find(t=>t.id===id)?.name ?? id;}
function issueName(id){return issues.issue_tags.find(t=>t.id===id)?.name ?? id;}
function topicTags(bill){return bill.policy_topics.map(t=>`<span class="tag">${esc(topicName(t))}</span>`).join('') + bill.issue_tags.map(t=>`<span class="tag issue">${esc(issueName(t))}</span>`).join('');}
function render(){
 const bills=filteredBills(data.bills,filters), counts=stateCounts(data.bills,filters), max=Math.max(1,...Object.values(counts));
 const date=new Date(filters.date+'T12:00:00Z').toLocaleDateString('en-US',{month:'long',year:'numeric',timeZone:'UTC'});
 $('total-count').textContent=bills.length;$('bill-count').textContent=bills.length;$('through-label').textContent=`through ${date}`;$('timeline-date').textContent=date;
 $('map-title').textContent=filters.topic==='all'?'All policy topics':topicName(filters.topic);
 $('bill-geography').textContent=filters.state==='all'?'BOTH STATES':states[filters.state].name.toUpperCase();
 $('state-filter').value=filters.state;$('issue-filter').value=filters.issue;$('reviewed').checked=filters.reviewed;$('timeline').value=month;
 document.querySelectorAll('.topic-button').forEach(el=>{const active=el.dataset.topic===filters.topic;el.classList.toggle('active',active);el.setAttribute('aria-pressed',active);});
 for(const [code,info] of Object.entries(states)){
  const path=$('state-'+info.fips), count=counts[code];
  path.style.fill=count?`rgb(${Math.round(137-count/max*115)},${Math.round(187-count/max*82)},${Math.round(175-count/max*68)})`:'#e4efec';
  path.classList.toggle('selected',filters.state===code);path.classList.toggle('dimmed',filters.state!=='all'&&filters.state!==code);
  path.setAttribute('aria-pressed',filters.state===code);path.setAttribute('aria-label',`${info.name}, ${count} matching enactments in sample. Select state.`);
  $('state-text-'+code).textContent=count;
 }
 $('legend-range').textContent=max===1?'1 match':`1–${max} matches`;
 $('state-comparison').innerHTML=Object.entries(states).map(([code,info])=>`<button class="state-card ${filters.state===code?'active':''}" data-state="${code}" aria-pressed="${filters.state===code}"><span class="state-mini" aria-hidden="true"></span><span>${info.name}<small>Sample enactments</small></span><strong>${counts[code]}</strong></button>`).join('');
 $('bill-list').innerHTML=bills.length?bills.map(bill=>`<article class="bill-item"><div class="bill-meta"><span class="bill-id"><span class="state-abbr">${bill.state}</span>${esc(bill.bill_number.replace(/([A-Z]+)(\d+)/,'$1 $2'))}</span><time datetime="${bill.dates.enacted}">${shortDate(bill.dates.enacted)}</time></div><button class="bill-title" data-bill="${esc(bill.id)}">${esc(bill.title)}</button><p class="bill-summary">${esc(bill.summary)}</p><div class="tags">${topicTags(bill)}</div><span class="proposed">Proposed labels · needs review</span></article>`).join(''):`<div class="empty"><strong>No matching bills</strong>${filters.reviewed?'This sample has no independently reviewed labels. Turn off “Reviewed labels only” to explore proposed labels.':'Try another topic, clear your search, or move the timeline forward.'}</div>`;
 const months=Array.from({length:12},(_,i)=>data.bills.filter(b=>matches(b,{...filters,date:'2025-12-31'})&&Number(b.dates.enacted.slice(5,7))-1===i).length), peak=Math.max(1,...months);
 $('timeline-chart').innerHTML=months.map((count,i)=>`<div class="chart-bar ${i>month?'future':''}" style="height:${Math.max(2,count/peak*38)}px"></div>`).join('');
 $('timeline').setAttribute('aria-valuetext',date);
 $('announcement').textContent=`${bills.length} matching sample enactments through ${date}.`;
 setUrl();
}
function showBill(id){
 const bill=data.bills.find(b=>b.id===id);if(!bill)return;
 const sources=bill.sources.map(s=>{const href=safeUrl(s.url);return href?`<a class="detail-source" href="${esc(href)}" target="_blank" rel="noopener noreferrer">${esc(s.label)}</a>`:'';}).join('');
 $('detail-body').innerHTML=`<p class="detail-label">${states[bill.state].name} · ${esc(bill.bill_number)} · ${esc(bill.session_id)}</p><h2>${esc(bill.title)}</h2><div class="tags">${topicTags(bill)}</div><span class="proposed">Assistant-proposed labels · not independently reviewed</span><div class="detail-dates"><div><span class="detail-label">Enacted</span><strong>${shortDate(bill.dates.enacted)}</strong></div><div><span class="detail-label">Effective</span><strong>${bill.dates.effective?shortDate(bill.dates.effective):'Not established in sample'}</strong></div></div><h3>Selected provisions</h3><p>${esc(bill.summary)}</p><p class="detail-label">${esc(bill.summary_provenance)}</p><h3>Scope and exceptions</h3><ul>${(bill.summary_limitations??[]).map(note=>`<li>${esc(note)}</li>`).join('')}</ul>${bill.effective_date_note?`<p><strong>Effective-date note:</strong> ${esc(bill.effective_date_note)}</p>`:''}<h3>Source traceability</h3><p>Historical enactment and selected provisions were checked against official sources by an AI assistant. This is separate from independent topic review.</p>${(bill.source_claims??[]).map(claim=>`<p class="detail-label">Checked ${esc(claim.checked_on)} · ${esc(claim.source_locator)}</p>`).join('')}<h3>Why these labels?</h3><div class="evidence">“${esc(bill.classification.evidence[0].excerpt)}”</div><p>This phrase comes from the PolyViz summary. It supports exploring these proposed labels, but is not independent validation. Affected sectors do not automatically become policy topics.</p>${bill.affected_sectors.length?`<p><strong>Affected sector:</strong> ${bill.affected_sectors.map(id=>esc(issues.affected_sectors.find(s=>s.id===id)?.name??id)).join(', ')}</p>`:''}<h3>Check the official sources</h3>${sources}<p class="detail-label">Historical enactment checked November 18, 2026. Later amendments, court decisions and current enforceability are outside this snapshot.</p>`;
 stop();$('detail-dialog').showModal();
}
async function init(){
 [data,taxonomy,issues,geography]=await Promise.all(['bills','topics','issues','states'].map(async name=>{const response=await fetch(`data/${name}.json`);if(!response.ok)throw new Error(`Could not load ${name}`);return response.json();}));
 const params=new URLSearchParams(location.search);
 if(params.get('state') in states)filters.state=params.get('state');
 if(taxonomy.topics.some(t=>t.id===params.get('topic')))filters.topic=params.get('topic');
 if(issues.issue_tags.some(t=>t.id===params.get('issue')))filters.issue=params.get('issue');
 if(params.has('month')&&/^\d+$/.test(params.get('month'))&&Number(params.get('month'))<=11)month=Number(params.get('month'));
 filters.date=monthEnd(month);filters.search=params.get('q')??'';filters.reviewed=params.get('reviewed')==='1';$('search').value=filters.search;
 $('sample-count').textContent=data.bills.length;
 $('topic-filters').innerHTML=[{id:'all',name:'All policy topics'},...taxonomy.topics].map((topic,i)=>`<button class="topic-button" data-topic="${topic.id}" style="--topic-color:${colors[i%colors.length]}" aria-pressed="false"><span class="topic-dot" aria-hidden="true"></span>${esc(topic.name)}</button>`).join('');
 $('issue-filter').innerHTML='<option value="all">All issues</option>'+issues.issue_tags.map(issue=>`<option value="${issue.id}">${esc(issue.name)}</option>`).join('');
 const svgNS='http://www.w3.org/2000/svg';
 for(const geo of geography){
  const code=Object.keys(states).find(s=>states[s].fips===geo.id),path=document.createElementNS(svgNS,'path');path.setAttribute('d',geo.path);path.id='state-'+geo.id;path.classList.add('state-path');
  const title=document.createElementNS(svgNS,'title');title.textContent=geo.name+(code?' · sample coverage':' · no sample coverage');path.append(title);
  if(code){path.classList.add('covered');path.setAttribute('role','button');path.setAttribute('tabindex','0');path.addEventListener('click',()=>selectState(code));path.addEventListener('keydown',event=>{if(['Enter',' '].includes(event.key)){event.preventDefault();selectState(code);}});}
  $('state-paths').append(path);
 }
 for(const [code,x,y] of [['CA',122,306],['TX',463,430]]){
  const label=document.createElementNS(svgNS,'text');label.setAttribute('x',x);label.setAttribute('y',y);label.setAttribute('text-anchor','middle');label.classList.add('map-label');label.setAttribute('aria-hidden','true');
  label.innerHTML=`<tspan x="${x}">${code}</tspan><tspan class="map-label-count" x="${x}" dy="23" id="state-text-${code}"></tspan>`;$('state-labels').append(label);
 }
 $('topic-filters').addEventListener('click',event=>{const button=event.target.closest('[data-topic]');if(button){filters.topic=button.dataset.topic;render();}});
 $('state-comparison').addEventListener('click',event=>{const button=event.target.closest('[data-state]');if(button)selectState(button.dataset.state);});
 $('state-filter').addEventListener('change',event=>{filters.state=event.target.value;render();});
 $('issue-filter').addEventListener('change',event=>{filters.issue=event.target.value;render();});
 $('reviewed').addEventListener('change',event=>{filters.reviewed=event.target.checked;render();});
 $('search').addEventListener('input',event=>{filters.search=event.target.value;render();});
 $('timeline').addEventListener('input',event=>{stop();month=Number(event.target.value);filters.date=monthEnd(month);render();});
 $('play').addEventListener('click',()=>{if(playing){stop();return;}if(month===11)month=-1;playing=setInterval(()=>{month++;filters.date=monthEnd(month);render();if(month===11)stop();},900);$('play').innerHTML='<span aria-hidden="true">Ⅱ</span> Pause';$('play').setAttribute('aria-label','Pause timeline');});
 $('reset').addEventListener('click',()=>{stop();filters={state:'all',topic:'all',issue:'all',date:'2025-12-31',search:'',reviewed:false};month=11;$('search').value='';render();});
 $('bill-list').addEventListener('click',event=>{const button=event.target.closest('[data-bill]');if(button)showBill(button.dataset.bill);});
 for(const id of ['about-button','methodology-button'])$(id).addEventListener('click',()=>{stop();$('about-dialog').showModal();});
 $('close-detail').addEventListener('click',()=>$('detail-dialog').close());$('close-about').addEventListener('click',()=>$('about-dialog').close());
 $('download-data').addEventListener('click',()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const anchor=document.createElement('a');anchor.href=url;anchor.download='polyviz-2025-sample.json';anchor.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
 document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
 render();
}
init().catch(error=>{$('bill-list').textContent='The sample could not load. Please refresh or serve this folder over HTTP.';$('total-count').textContent='—';$('bill-count').textContent='—';$('announcement').textContent=error.message;console.error(error);});
