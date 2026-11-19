export const states = {CA: {name: 'California', fips: '06'}, TX: {name: 'Texas', fips: '48'}};
export function matches(bill, filters, includeState = true) {
  return bill.status === 'enacted' && !!bill.dates.enacted && bill.dates.enacted <= filters.date
    && (!includeState || filters.state === 'all' || bill.state === filters.state)
    && (filters.topic === 'all' || bill.policy_topics.includes(filters.topic))
    && (filters.issue === 'all' || bill.issue_tags.includes(filters.issue))
    && (!filters.reviewed || bill.classification.review_status === 'reviewed')
    && (!filters.search || `${bill.bill_number} ${bill.title} ${bill.summary}`.toLowerCase().includes(filters.search.toLowerCase().trim()));
}
export function filteredBills(bills, filters) {
  return bills.filter(b => matches(b, filters)).sort((a,b) => b.dates.enacted.localeCompare(a.dates.enacted) || a.id.localeCompare(b.id));
}
export function stateCounts(bills, filters) {
  return Object.fromEntries(Object.keys(states).map(state => [state,bills.filter(b => b.state === state && matches(b, filters, false)).length]));
}
export function monthEnd(index) { return new Date(Date.UTC(2025, Number(index)+1, 0)).toISOString().slice(0,10); }
export function safeUrl(value) { try {const url=new URL(value);return url.protocol === 'https:' ? url.href : null;} catch{return null;} }
