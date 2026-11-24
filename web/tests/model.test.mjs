import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {expandInventory,filteredBills,stateCounts,monthEnd,safeUrl,matchIssues,searchPlan,labelMix,topStates,matchReason,labelEvidence,textHasPhrase} from '../dist/model.js';
const {bills}=JSON.parse(readFileSync(new URL('../dist/data/bills.json',import.meta.url)));
const filters={state:'all',topic:'all',issue:'all',date:'2025-12-31',search:'',reviewed:false};
test('sample contains distinct sourced enacted identities and valid taxonomy labels',()=>{
 const taxonomy=JSON.parse(readFileSync(new URL('../dist/data/topics.json',import.meta.url)));
 const issues=JSON.parse(readFileSync(new URL('../dist/data/issues.json',import.meta.url)));
 assert.equal(new Set(bills.map(b=>b.id)).size,bills.length);
 assert.equal(bills.length,17);
 for(const b of bills){assert.equal(b.status,'enacted');assert.match(b.dates.enacted,/^2025-\d{2}-\d{2}$/);assert.deepEqual(b.topics,b.policy_topics);assert.equal(b.classification.review_status,'needs_review');assert.ok(b.sources.every(s=>safeUrl(s.url)));assert.ok(b.policy_topics.every(id=>taxonomy.topics.some(t=>t.id===id)));assert.ok(b.issue_tags.every(id=>issues.issue_tags.some(t=>t.id===id)));}
});
test('topics count each multi-label bill once and combine with issue filters',()=>{
 assert.equal(filteredBills(bills,{...filters,topic:'housing'}).length,5);
 assert.equal(filteredBills(bills,{...filters,issue:'data_centers'}).length,2);
 assert.equal(filteredBills(bills,{...filters,topic:'housing',issue:'data_centers'}).length,0);
 assert.equal(filteredBills(bills,filters).length,17);
});
test('timeline is cumulative and uses enactment rather than effective date',()=>{
 assert.equal(filteredBills(bills,{...filters,date:monthEnd(4)}).length,0);
 assert.equal(filteredBills(bills,{...filters,date:monthEnd(5)}).length,10);
 assert.equal(filteredBills(bills,{...filters,date:monthEnd(8)}).length,14);
 assert.equal(filteredBills(bills,{...filters,date:monthEnd(9)}).length,17);
});
test('state selection narrows the list but preserves cross-state comparison counts',()=>{
 assert.equal(filteredBills(bills,{...filters,state:'CA'}).length,9);
 assert.deepEqual(stateCounts(bills,{...filters,state:'CA'}),{CA:9,TX:8});
});
test('review-only does not promote assistant labels to verified',()=>{
 assert.equal(filteredBills(bills,{...filters,reviewed:true}).length,0);
});
test('unknown and undated statuses stay out of enacted counts',()=>{
 const copy=structuredClone(bills[0]);copy.status='unknown';assert.equal(filteredBills([copy],filters).length,0);
 copy.status='enacted';copy.dates.enacted=null;assert.equal(filteredBills([copy],filters).length,0);
});
test('bill search is case-insensitive and respects other filters',()=>{
 assert.equal(filteredBills(bills,{...filters,search:'sb6'}).length,1);
 assert.equal(filteredBills(bills,{...filters,search:'SB6',state:'CA'}).length,0);
});
test('passed bills use the status date and undated rows stay hidden',()=>{
 const passed={id:'NY-1-A1',state:'NY',session_id:'1',bill_number:'A1',title:'Transit',summary:'Buses',status:'passed',dates:{status:'2025-02-02'},policy_topics:['transportation'],issue_tags:[],classification:{review_status:'unreviewed'}};
 assert.equal(filteredBills([passed],filters).length,1);
 assert.equal(filteredBills([passed],{...filters,date:monthEnd(0)}).length,0);
 assert.equal(filteredBills([{...passed,dates:{status:null}}],filters).length,0);
 assert.equal(stateCounts([passed],filters).NY,undefined);
});
test('compact inventory rows expand into passed bills',()=>{
 const [bill]=expandInventory({summary_provenance:'LegiScan description.',bills:[['NY-1-A1','NY','1','A1','Transit','Buses','2025-02-02',['transportation'],'https://nyassembly.gov/bill',['data_centers']]]});
 assert.equal(bill.status,'passed');
 assert.equal(bill.dates.status,'2025-02-02');
 assert.equal(bill.sources[0].url,'https://nyassembly.gov/bill');
 assert.deepEqual(bill.issue_tags,['data_centers']);
 assert.equal(filteredBills([bill],{...filters,issue:'data_centers'}).length,1);
});
test('issue search matches related wording and still respects the issue bar',()=>{
 const issueTags=JSON.parse(readFileSync(new URL('../dist/data/issues.json',import.meta.url))).issue_tags;
 const ids=query=>matchIssues(query,issueTags).map(hit=>hit.id);
 assert.ok(ids('power bill').includes('electricity_rates'));
 assert.ok(ids('server farms').includes('data_centers'));
 assert.ok(ids('fentanyl').includes('opioids'));
 assert.ok(ids('daycare').includes('child_care'));
 assert.ok(ids('property tax').includes('property_tax'));
 assert.equal(ids('property tax').includes('tax_incentives'),false);
 assert.deepEqual(ids('zzzz'),[]);
 assert.equal(ids('rates').includes('electricity_rates'),false);
 const bill={id:'TX-1-HB1',state:'TX',session_id:'1',bill_number:'HB1',title:'Grid planning',summary:'Large users',status:'passed',dates:{status:'2025-06-01'},policy_topics:[],issue_tags:['electricity_rates'],classification:{review_status:'unreviewed'}};
 assert.equal(filteredBills([bill],{...filters,issueMatches:['electricity_rates']}).length,1);
 assert.equal(filteredBills([bill],{...filters,issue:'opioids',issueMatches:['electricity_rates']}).length,0);
 assert.equal(filteredBills([bill],{...filters,issue:'electricity_rates',issueMatches:['electricity_rates']}).length,1);
 assert.equal(filteredBills([bill],{...filters,issueMatches:[]}).length,0);
 const plan=searchPlan('power bill',issueTags);
 const worded={id:'TX-1-HB2',state:'TX',session_id:'1',bill_number:'HB2',title:'Utility bill relief',summary:'Lowers a power bill for households',status:'passed',dates:{status:'2025-08-01'},policy_topics:[],issue_tags:[],classification:{review_status:'unreviewed'}};
 const other={id:'TX-1-HB3',state:'TX',session_id:'1',bill_number:'HB3',title:'Schools',summary:'Teachers and classrooms',status:'passed',dates:{status:'2025-08-02'},policy_topics:[],issue_tags:[],classification:{review_status:'unreviewed'}};
 const older={...bill,dates:{status:'2025-01-01'}};
 const view={...filters,issueMatches:plan.hits.map(hit=>hit.id),issuePhrases:plan.phrases};
 const found=filteredBills([worded,other,older],view);
 assert.deepEqual(found.map(item=>item.id),[older.id,worded.id]);
 const plain=searchPlan('classroom size',issueTags);
 assert.equal(plain.hits.length,0);
 const sized={id:'CA-1-AB9',state:'CA',session_id:'1',bill_number:'AB9',title:'Maximum classroom size',summary:'Limits class size',status:'passed',dates:{status:'2025-03-01'},policy_topics:[],issue_tags:[],classification:{review_status:'unreviewed'}};
 assert.equal(filteredBills([sized,other],{...filters,issueMatches:[],issuePhrases:plain.phrases}).length,1);
});
test('label mix counts a bill in each of its labels and leaves unlabeled bills out of the bars',()=>{
 const rows=[{policy_topics:['housing','energy'],issue_tags:['medicaid']},{policy_topics:['housing'],issue_tags:[]},{policy_topics:[],issue_tags:['medicaid']}];
 const topics=labelMix(rows,'policy_topics');
 assert.deepEqual(topics.ranked,[['housing',2],['energy',1]]);
 assert.equal(topics.unlabeled,1);
 assert.deepEqual(labelMix(rows,'issue_tags').ranked,[['medicaid',2]]);
 assert.deepEqual(topStates({TX:4,CA:9,NY:0,AL:4},2),[['CA',9],['AL',4]]);
 assert.equal(matchReason({issue_tags:['medicaid']},{issueMatches:['medicaid'],issuePhrases:['medicaid']}),'label');
 assert.equal(matchReason({issue_tags:[]},{issueMatches:['medicaid'],issuePhrases:['medicaid']}),'wording');
 assert.equal(matchReason({issue_tags:['medicaid']},{}),'');
});
test('label evidence names the phrase and distinguishes a wording match',()=>{
 const topics=[{id:'housing',name:'Housing',terms:['tenant','school district']}];
 const issueTags=[{id:'electricity_rates',name:'Electricity rates',aliases:['electric rates']}];
 const labeled={title:'Tenant protection',summary:'Limits eviction for a tenant.',policy_topics:['housing'],issue_tags:['electricity_rates']};
 const housing=labelEvidence(labeled,topics,issueTags).find(reason=>reason.id==='housing');
 assert.equal(housing.kind,'phrase');
 assert.deepEqual(housing.phrases,['tenant']);
 assert.equal(textHasPhrase('Funds school districts.','school district'),true);
 assert.equal(textHasPhrase('A database.','data'),false);
 const rates=labelEvidence({...labeled,summary:'Changes electric-rates for customers.'},topics,issueTags).find(reason=>reason.id==='electricity_rates');
 assert.deepEqual(rates.phrases,['electric rates']);
 const worded={title:'Utility relief',summary:'Lowers a power bill.',policy_topics:[],issue_tags:[]};
 const wording=labelEvidence(worded,topics,issueTags,{issueMatches:['electricity_rates'],issuePhrases:['power bill','electric rates']});
 assert.equal(wording.length,1);
 assert.equal(wording[0].kind,'wording');
 assert.deepEqual(wording[0].phrases,['power bill']);
 const taggedSearch=labelEvidence(labeled,topics,issueTags,{issueMatches:['electricity_rates'],issuePhrases:['power bill']});
 assert.equal(taggedSearch.some(reason=>reason.kind==='wording'),false);
});
test('stored label hits survive a shortened summary',()=>{
 const [bill]=expandInventory({summary_provenance:'x',bills:[['NY-1-A1','NY','1','A1','Care','Short.','2025-02-02',['healthcare'],'',['mental_health'],[['mental health']],[['behavioral health']]]]});
 const reasons=labelEvidence(bill,[{id:'healthcare',name:'Healthcare',terms:['hospital']}],[{id:'mental_health',name:'Mental health',aliases:['mental health']}]);
 assert.deepEqual(reasons.map(reason=>reason.phrases),[['mental health'],['behavioral health']]);
});
test('a saved excerpt explains a label when the short text has no listed phrase',()=>{
 const bill={title:'Grid costs',summary:'Large users.',policy_topics:[],issue_tags:['electricity_rates'],classification:{evidence:[{excerpt:'large electricity users'}]}};
 const [reason]=labelEvidence(bill,[],[{id:'electricity_rates',name:'Electricity rates',aliases:['electric rates']}]);
 assert.deepEqual(reason.phrases,['large electricity users']);
});
test('source links only accept https',()=>{
 assert.equal(safeUrl('javascript:alert(1)'),null);assert.equal(safeUrl('data:text/html,test'),null);assert.equal(safeUrl('https://example.org/'),'https://example.org/');
});
