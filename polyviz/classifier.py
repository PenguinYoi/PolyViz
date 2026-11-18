"""Offline, explainable baseline classifier; labels always require evaluation."""
import argparse
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

TAXONOMY = Path(__file__).resolve().parents[1] / 'data' / 'topics-v2.json'
STATES = set('AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC US'.split())
STATUSES = {'pending', 'enacted', 'vetoed', 'failed', 'withdrawn', 'unknown'}


def normalized_text(value):
    return ' '.join(re.findall(r'\w+', value.casefold()))


def classify(title, summary, taxonomy):
    text = ' ' + normalized_text(title + ' ' + summary) + ' '
    evidence = {}
    for topic in taxonomy['topics']:
        matches = [term for term in topic['terms']
                   if ' ' + normalized_text(term) + ' ' in text]
        if matches:
            evidence[topic['id']] = matches
    return {
        'topics': list(evidence),
        'classification': {
            'method': 'keyword_rules', 'method_version': '1',
            'taxonomy_version': taxonomy['version'],
            'review_status': 'unreviewed' if evidence else 'needs_review',
            'outcome': 'matched' if evidence else 'unclassified',
            'evidence': evidence,
        },
    }


def convert(payload, taxonomy):
    if not isinstance(payload, dict):
        raise ValueError('Each bill must be a JSON object.')
    wrapped = 'bill' in payload
    if wrapped and payload.get('status') not in (None, 'OK'):
        raise ValueError('LegiScan response is not successful.')
    bill = payload['bill'] if wrapped else payload
    if not isinstance(bill, dict):
        raise ValueError('bill must be an object.')
    legiscan = wrapped or ('bill_id' in bill and isinstance(bill.get('session'), dict))
    state = str(bill.get('state', '')).upper().strip()
    if state not in STATES:
        raise ValueError('state must be a supported two-letter jurisdiction code.')
    session = bill.get('session_id')
    if legiscan:
        session = bill.get('session', {}).get('session_id') or session
    elif session is None:
        session = bill.get('session')
    if session is None or not re.fullmatch(r'[A-Za-z0-9_-]+', str(session)):
        raise ValueError('Provide a stable session_id (including special-session identity).')
    number = re.sub(r'\s+', '', str(bill.get('bill_number', '')).upper())
    if not re.fullmatch(r'[A-Z]+[0-9]+[A-Z0-9]*', number):
        raise ValueError('bill_number must contain a letter prefix and bill number.')
    title = bill.get('title', '')
    summary = bill.get('description', '') if legiscan else bill.get('summary', '')
    summary = summary or ''
    if not isinstance(title, str) or not isinstance(summary, str) or not title.strip():
        raise ValueError('A nonempty title and optional string summary are required.')
    source_status = bill.get('status', 'unknown')
    if legiscan:
        # LegiScan 4 is "Passed"; preserve it without assuming enactment.
        status = {0:'pending', 1:'pending', 2:'pending', 3:'pending',
                  5:'vetoed', 6:'failed'}.get(source_status, 'unknown')
    else:
        status = source_status
        if status not in STATUSES:
            raise ValueError('Unsupported status; use ' + ', '.join(sorted(STATUSES)))
    enacted = None if legiscan else bill.get('enacted_date')
    if enacted is not None:
        date.fromisoformat(enacted)
        if status != 'enacted':
            raise ValueError('enacted_date requires enacted status.')
    origin = bill.get('origin_chamber', 'unknown')
    if origin not in {'lower', 'upper', 'unicameral', 'unknown'}:
        raise ValueError('Invalid origin_chamber.')
    warnings = []
    if legiscan and source_status == 4:
        warnings.append('LegiScan Passed status needs enactment verification; retained as unknown.')
    if status == 'enacted' and enacted is None:
        warnings.append('Enactment date missing; exclude from year-based totals until verified.')
    result = {
        'id': f'{state}-{session}-{number}', 'state': state,
        'session_id': str(session), 'bill_number': number,
        'origin_chamber': origin, 'title': title.strip(), 'summary': summary.strip(),
        'status': status, 'source_status': source_status, 'enacted_date': enacted,
        'source': {'provider': 'legiscan' if legiscan else 'user_supplied',
                   'bill_id': str(bill['bill_id']) if bill.get('bill_id') is not None else None,
                   'url': bill.get('state_link') or bill.get('url') or bill.get('source_url')},
        **classify(title, summary, taxonomy), 'warnings': warnings,
        'dates': {'introduced': None if legiscan else bill.get('introduced_date'),
                  'enacted': enacted,
                  'effective': None if legiscan else bill.get('effective_date')},
    }
    if not result['topics']:
        result['warnings'].append('No topic rules matched; this does not establish that the bill is outside the taxonomy.')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='Single bill, array of bills, or LegiScan getBill JSON')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--taxonomy', type=Path, default=TAXONOMY)
    parser.add_argument('--method', choices=['keywords', 'semantic', 'nli', 'hybrid'], default='keywords')
    parser.add_argument('--threshold', type=float, help='Provisional cutoff: semantic defaults to 0.4; NLI defaults to 0.7')
    parser.add_argument('--download-model', action='store_true', help='Allow one-time free model download; never calls inference APIs')
    args = parser.parse_args()
    try:
        if args.input.resolve() == args.output.resolve():
            raise ValueError('Output must differ from input; preserve source records.')
        payload = json.loads(args.input.read_text())
        taxonomy = json.loads(args.taxonomy.read_text())
        records = payload if isinstance(payload, list) else [payload]
        if not records:
            raise ValueError('Input contains no bills.')
        bills = [convert(record, taxonomy) for record in records]
        if len({bill['id'] for bill in bills}) != len(bills):
            raise ValueError('Duplicate bill identities in input.')
        if args.method in {'semantic', 'nli', 'hybrid'}:
            if args.method == 'semantic':
                from .semantic import SemanticClassifier
                semantic = SemanticClassifier(taxonomy, args.threshold if args.threshold is not None else 0.4, args.download_model)
            elif args.method == 'hybrid':
                from .hybrid import HybridClassifier
                semantic = HybridClassifier(taxonomy, args.threshold if args.threshold is not None else 0.7, args.download_model)
            else:
                from .nli import NLIClassifier
                semantic = NLIClassifier(taxonomy, args.threshold if args.threshold is not None else 0.7, args.download_model)
            for bill in bills:
                bill['warnings'] = [w for w in bill['warnings'] if not w.startswith('No topic rules matched')]
                bill.update(semantic.classify(bill['title'], bill['summary']))
        from .schema import to_v2
        bills = [to_v2(bill, detect=True) for bill in bills]
        document = {'schema_version': 2, 'generated_at': datetime.now(timezone.utc).isoformat(), 'bills': bills}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(document, indent=2, ensure_ascii=False) + '\n')
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(1, f'Error: {exc}\n')
    print(f'Wrote {len(bills)} bill(s) to {args.output}')


if __name__ == '__main__':
    main()
