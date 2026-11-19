import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {expandInventory,filteredBills,stateCounts,monthEnd,safeUrl} from '../dist/model.js';
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
test('source links only accept https',()=>{
 assert.equal(safeUrl('javascript:alert(1)'),null);assert.equal(safeUrl('data:text/html,test'),null);assert.equal(safeUrl('https://example.org/'),'https://example.org/');
});
