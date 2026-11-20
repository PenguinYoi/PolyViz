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
const STOP = new Set(['a','an','the','of','and','or','for','to','in','on','by','with','about','from','that','this','into','over','under','per','its','their','new']);
const WEAK = new Set(['bill','bills','act','acts','law','laws','state','states','program','programs','public','cost','costs','use','uses','rate','rates']);
const SHORT_PHRASES = new Set(['ai','ev']);

function variants(token) {
  const forms = new Set([token]);
  if (token.length > 3 && token.endsWith('s') && !token.endsWith('ss')) forms.add(token.slice(0, -1));
  if (token.length > 4 && token.endsWith('es') && !token.endsWith('ses')) forms.add(token.slice(0, -2));
  return forms;
}
function words(text) {
  return String(text || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim().split(/\s+/).filter(token => token && !STOP.has(token));
}
function tokenMatch(left, right) {
  for (const form of variants(left)) if (variants(right).has(form)) return true;
  return false;
}
function containsPhrase(queryTokens, phraseTokens) {
  if (!phraseTokens.length || phraseTokens.length > queryTokens.length) return false;
  if (phraseTokens.length === 1 && WEAK.has(phraseTokens[0])) return false;
  if (phraseTokens.length === 1 && phraseTokens[0].length < 3 && !SHORT_PHRASES.has(phraseTokens[0])) return false;
  for (let start = 0; start <= queryTokens.length - phraseTokens.length; start += 1) {
    if (phraseTokens.every((token, index) => tokenMatch(token, queryTokens[start + index]))) return true;
  }
  return false;
}
export function matchIssues(query, issueTags) {
  const queryTokens = words(query);
  if (!queryTokens.length) return [];
  const items = issueTags.map(issue => {
    const phrases = [issue.name, ...(issue.aliases || []), ...(issue.related || [])].map(words).filter(tokens => tokens.length);
    return {issue, phrases, vocab: phrases.flat(), nameTokens: words(issue.name)};
  });
  const frequency = new Map();
  for (const item of items) {
    const seen = new Set(item.vocab.flatMap(token => [...variants(token)]));
    for (const token of seen) frequency.set(token, (frequency.get(token) || 0) + 1);
  }
  const hits = [];
  for (const item of items) {
    let score = 0;
    if (item.phrases.some(phrase => containsPhrase(queryTokens, phrase))) score = 1;
    else if (queryTokens.length === 1 && queryTokens[0].length < 3) score = 0;
    else if (queryTokens.every(token => item.vocab.some(known => tokenMatch(token, known)))) {
      const distinctive = queryTokens.some(token => !WEAK.has(token) && [...variants(token)].some(form => (frequency.get(form) || 9) <= 2));
      if (distinctive) score = 0.8;
    } else if (queryTokens.length === 1 && !WEAK.has(queryTokens[0]) && item.nameTokens.some(token => tokenMatch(token, queryTokens[0]))) {
      score = 0.75;
    }
    if (score) hits.push({id: item.issue.id, name: item.issue.name, score});
  }
  return hits.sort((a, b) => b.score - a.score || a.name.localeCompare(b.name) || a.id.localeCompare(b.id));
}
export function matches(bill, filters, includeState = true) {
  const tags = bill.issue_tags || [];
  return (bill.status === 'enacted' || bill.status === 'passed') && !!billDate(bill) && billDate(bill) <= filters.date
    && (!includeState || filters.state === 'all' || bill.state === filters.state)
    && (filters.topic === 'all' || bill.policy_topics.includes(filters.topic))
    && (filters.issue === 'all' || tags.includes(filters.issue))
    && (filters.issueMatches == null || tags.some(id => filters.issueMatches.includes(id)))
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
