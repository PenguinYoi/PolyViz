export const states = {CA: {name: 'California', fips: '06'}, TX: {name: 'Texas', fips: '48'}};
export const fipsToCode = {
  '01':'AL','02':'AK','04':'AZ','05':'AR','06':'CA','08':'CO','09':'CT','10':'DE','11':'DC','12':'FL',
  '13':'GA','15':'HI','16':'ID','17':'IL','18':'IN','19':'IA','20':'KS','21':'KY','22':'LA','23':'ME',
  '24':'MD','25':'MA','26':'MI','27':'MN','28':'MS','29':'MO','30':'MT','31':'NE','32':'NV','33':'NH',
  '34':'NJ','35':'NM','36':'NY','37':'NC','38':'ND','39':'OH','40':'OK','41':'OR','42':'PA','44':'RI',
  '45':'SC','46':'SD','47':'TN','48':'TX','49':'UT','50':'VT','51':'VA','53':'WA','54':'WV','55':'WI','56':'WY'
};
export function billDate(bill) {
  const dates = bill.dates || {};
  return bill.status === 'passed' ? (dates.status || '') : (dates.enacted || '');
}
export function expandInventory(inventory) {
  return inventory.bills.map(([id, state, sessionId, billNumber, title, summary, statusDate, topics, url, issues]) => ({
    id, state, session_id: sessionId, bill_number: billNumber, title, summary,
    status: 'passed',
    dates: {status: statusDate},
    policy_topics: topics || [],
    issue_tags: issues || [],
    affected_sectors: [],
    classification: {
      method: 'keyword_rules',
      review_status: topics && topics.length ? 'unreviewed' : 'needs_review',
      outcome: topics && topics.length ? 'matched' : 'unclassified',
    },
    sources: url ? [{label: 'Legislature record', url}] : [],
    summary_provenance: inventory.summary_provenance,
  }));
}
export function matches(bill, filters, includeState = true) {
  return (bill.status === 'enacted' || bill.status === 'passed') && !!billDate(bill) && billDate(bill) <= filters.date
    && (!includeState || filters.state === 'all' || bill.state === filters.state)
    && (filters.topic === 'all' || bill.policy_topics.includes(filters.topic))
    && (filters.issue === 'all' || bill.issue_tags.includes(filters.issue))
    && (!filters.reviewed || bill.classification.review_status === 'reviewed')
    && (!filters.search || `${bill.bill_number} ${bill.title} ${bill.summary}`.toLowerCase().includes(filters.search.toLowerCase().trim()));
}
export function filteredBills(bills, filters) {
  return bills.filter(b => matches(b, filters)).sort((a,b) => billDate(b).localeCompare(billDate(a)) || a.id.localeCompare(b.id));
}
export function stateCounts(bills, filters, stateCodes = Object.keys(states)) {
  const counts = Object.fromEntries(stateCodes.map(state => [state, 0]));
  for (const bill of bills) {
    if (bill.state in counts && matches(bill, filters, false)) counts[bill.state] += 1;
  }
  return counts;
}
export function monthEnd(index) { return new Date(Date.UTC(2025, Number(index)+1, 0)).toISOString().slice(0,10); }
export function safeUrl(value) { try {const url=new URL(value);return url.protocol === 'https:' ? url.href : null;} catch{return null;} }
