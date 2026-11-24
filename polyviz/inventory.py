"""Export legislature-passed bills for the public map.

LegiScan status 4 means the legislature recorded the bill as passed. This export
keeps that fact and does not treat it as a verified enactment.
"""
import argparse
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / 'web' / 'dist' / 'data' / 'bills.json'
TOPICS = ROOT / 'web' / 'dist' / 'data' / 'topics.json'
ISSUES = ROOT / 'web' / 'dist' / 'data' / 'issues.json'
DEFAULT_DB = ROOT / 'data' / 'raw' / 'legiscan' / 'bills.sqlite'
DEFAULT_OUT = ROOT / 'web' / 'dist' / 'data' / 'inventory.json'


def identity_key(state, number):
    return (state or '').upper(), ''.join(ch for ch in (number or '').upper() if ch.isalnum())


def shorten(text, limit=180):
    text = ' '.join((text or '').split())
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(' ', 1)[0]
    return (cut or text[:limit]).rstrip('.,;:') + '…'


def curated_keys(path=CURATED):
    document = json.loads(Path(path).read_text())
    return {identity_key(bill['state'], bill['bill_number']) for bill in document['bills']}


def allowed_topics(path=TOPICS):
    document = json.loads(Path(path).read_text())
    return {topic['id'] for topic in document['topics']}


def issue_taxonomy(path=ISSUES):
    return json.loads(Path(path).read_text())


def _alias_pattern(alias):
    return r'(?<!\w)' + re.escape(alias).replace(r'\ ', r'[\s-]+') + r'(?!\w)'


def issue_label_matches(title, summary, taxonomy):
    """Return each issue id with the aliases that selected it.

    `related` phrases are for search only and are not assigned. Alias boundaries
    match the candidate detector: spaces may be hyphens, and the phrase must
    start and end on a word boundary. Matching uses the full title and summary,
    before the public summary is shortened.
    """
    text = f"{title or ''}\n{summary or ''}"
    found = []
    for label in taxonomy.get('issue_tags', []):
        matched = [alias for alias in label.get('aliases', [])
                   if re.search(_alias_pattern(alias), text, re.I)]
        if matched:
            found.append((label['id'], matched[:6]))
    return found


def issue_labels(title, summary, taxonomy):
    """Issue ids selected by alias phrases. Related phrases are not labels."""
    return [label_id for label_id, _matched in issue_label_matches(title, summary, taxonomy)]


def passed_records(connection, year='2025', skip=(), topics=None, issues=None):
    """Return slim map records for non-Congress bills LegiScan marked passed."""
    skip = set(skip)
    allowed = None if topics is None else set(topics)
    rows = connection.execute(
        '''SELECT id, state, session_id, bill_number, title, summary, status_date, record_json
           FROM bills
           WHERE source_status = '4' AND state != 'US' AND status_date LIKE ?
           ORDER BY id''',
        (f'{year}-%',),
    )
    records = []
    for bill_id, state, session_id, number, title, summary, status_date, raw in rows:
        if identity_key(state, number) in skip:
            continue
        stored = json.loads(raw)
        url = (stored.get('source') or {}).get('url')
        labels = [topic for topic in stored.get('policy_topics') or [] if isinstance(topic, str)]
        if allowed is not None:
            labels = [topic for topic in labels if topic in allowed]
        matches = issue_label_matches(title, summary, issues) if issues else []
        tags = [label_id for label_id, _matched in matches]
        evidence = (stored.get('classification') or {}).get('evidence')
        topic_hits = []
        for topic in labels:
            hits = evidence.get(topic) if isinstance(evidence, dict) else None
            if isinstance(hits, list):
                topic_hits.append([hit for hit in hits if isinstance(hit, str)][:6])
            else:
                topic_hits.append(None)
        record = {
            'id': bill_id,
            'state': state,
            'session_id': str(session_id),
            'bill_number': number,
            'title': ' '.join((title or '').split()),
            'summary': shorten(summary),
            'status': 'passed',
            'dates': {'status': status_date},
            'policy_topics': labels,
            'topic_hits': topic_hits,
            'issue_tags': tags,
            'issue_hits': [matched for _label_id, matched in matches],
            'affected_sectors': [],
            'classification': {
                'method': 'keyword_rules',
                'review_status': 'unreviewed' if labels else 'needs_review',
                'outcome': 'matched' if labels else 'unclassified',
            },
            'sources': ([{'label': 'Legislature record', 'url': url}]
                        if isinstance(url, str) and url.startswith('https://') else []),
            'summary_provenance': (
                'LegiScan description. The legislature recorded this bill as passed; '
                'the governor signature is not verified here.'
            ),
        }
        records.append(record)
    return records


def document(records, year='2025'):
    provenance = records[0]['summary_provenance'] if records else ''
    return {
        'schema_version': 2,
        'layout': 'passed-bills-v2',
        'title': f'{year} legislature-passed bills',
        'coverage': (
            'Bills LegiScan marked Passed with a status date in this year, excluding Congress '
            'and bills already in the source-checked enacted snapshot. Signature and chaptering '
            'are not verified. Each bill is [id, state, session_id, bill_number, title, summary, '
            'status_date, policy_topics, source_url, issue_tags, topic_hits, issue_hits]. '
            'Topic and issue hits are the phrases that selected each label.'
        ),
        'year': int(year),
        'states': sorted({record['state'] for record in records}),
        'summary_provenance': provenance,
        'bills': [[
            record['id'], record['state'], record['session_id'], record['bill_number'],
            record['title'], record['summary'], record['dates']['status'], record['policy_topics'],
            record['sources'][0]['url'] if record['sources'] else '',
            record['issue_tags'], record['topic_hits'], record['issue_hits'],
        ] for record in records],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=DEFAULT_DB)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--year', default='2025')
    args = parser.parse_args()
    connection = sqlite3.connect(args.database)
    try:
        records = passed_records(
            connection, args.year, skip=curated_keys(), topics=allowed_topics(),
            issues=issue_taxonomy())
    finally:
        connection.close()
    payload = document(records, args.year)
    args.output.write_text(json.dumps(payload, separators=(',', ':'), ensure_ascii=False) + '\n')
    print(json.dumps({
        'bills': len(records),
        'states': len(payload['states']),
        'with_issues': sum(bool(record['issue_tags']) for record in records),
        'output': str(args.output),
    }))


if __name__ == '__main__':
    main()
