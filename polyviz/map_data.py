"""Validate provenance and consistency before publishing map data (offline)."""
import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]


def official_url(value):
    parsed=urlparse(value or '')
    host=(parsed.hostname or '').lower()
    return parsed.scheme=='https' and (host.endswith('.ca.gov') or host.endswith('.texas.gov')) and not parsed.username and not parsed.password


def validate(document):
    """Check admission metadata, never declare legal or semantic accuracy."""
    errors=[];seen=set()
    topics=json.loads((ROOT/'data/topics-v2.json').read_text())
    issues=json.loads((ROOT/'data/issue-taxonomy.json').read_text())
    labels={'policy_topics':{t['id'] for t in topics['topics']},**{key:{t['id'] for t in issues[key]} for key in ('issue_tags','affected_sectors','policy_actions')}}
    def valid_date(value):
        try:return date.fromisoformat(value)
        except (ValueError,TypeError):return None
    if document.get('schema_version')!=2:errors.append('Expected schema_version 2')
    for bill in document.get('bills',[]):
        identity=bill.get('id','missing-id')
        def fail(message):errors.append(f'{identity}: {message}')
        if identity in seen:fail('duplicate identity')
        seen.add(identity)
        if identity!=f"{bill.get('state')}-{bill.get('session_id')}-{bill.get('bill_number')}":fail('identity differs from state/session/bill')
        if bill.get('state') not in document.get('states',[]):fail('state outside declared coverage')
        enacted=bill.get('dates',{}).get('enacted')
        if bill.get('status')!='enacted' or not valid_date(enacted):fail('requires enacted status and ISO enactment date')
        elif valid_date(enacted).year!=document.get('year'):fail('enactment outside declared year')
        if bill.get('enacted_date')!=enacted:fail('legacy and v2 enactment dates disagree')
        if bill.get('topics')!=bill.get('policy_topics'):fail('topic aliases disagree')
        for key,allowed in labels.items():
            values=bill.get(key)
            if not isinstance(values,list) or any(not isinstance(x,str) or x not in allowed for x in values):fail(f'invalid {key}')
            elif len(set(values))!=len(values):fail(f'duplicate {key}')
        urls={s.get('url') for s in bill.get('sources',[])}
        if not urls or any(not official_url(url) for url in urls):fail('requires official state source URLs')
        verification=bill.get('status_verification',{})
        if verification.get('source_url') not in urls or verification.get('event_date')!=enacted or verification.get('event')!='signed_by_governor':fail('signature evidence missing or inconsistent')
        if not valid_date(verification.get('checked_on')):fail('missing status check date')
        claims=bill.get('source_claims',[])
        if not claims or not any(c.get('text')==bill.get('summary') for c in claims):fail('summary must have a matching sourced claim')
        for claim in claims:
            if claim.get('source_url') not in urls or not claim.get('source_locator') or not valid_date(claim.get('checked_on')):fail('claim requires source, locator and check date')
            if claim.get('check_method')!='assistant_compared_with_official_source':fail('unexpected claim-check provenance')
        if bill.get('classification',{}).get('review_status')=='reviewed' and not bill.get('independent_label_review'):fail('reviewed labels require an independent review record')
        if bill.get('summary_scope')!='selected_provisions_not_comprehensive' or not bill.get('summary_limitations'):fail('summary needs scope and limitations')
        effective=bill.get('dates',{}).get('effective')
        if effective and (not valid_date(effective) or not bill.get('effective_date_note')):fail('effective date needs valid date and explanation')
        if bill.get('effective_date_events') and effective:fail('staged provisions must not imply a single effective date')
        for event in bill.get('effective_date_events',[]):
            if not valid_date(event.get('date')) or not event.get('scope') or event.get('source_url') not in urls:fail('invalid provision-level effective-date evidence')
    if not seen:errors.append('No bills')
    if errors:raise ValueError('\n'.join(errors))
    return {'bills':len(seen),'states':dict(Counter(b['state'] for b in document['bills'])),'independently_reviewed_labels':sum(b['classification']['review_status']=='reviewed' for b in document['bills']), 'result':'provenance_and_consistency_checks_passed','limitation':'These checks do not independently verify summary meaning, completeness, legal effect, or topic accuracy.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('input',type=Path)
    args=parser.parse_args()
    try:print(json.dumps(validate(json.loads(args.input.read_text())),indent=2))
    except (OSError,ValueError,TypeError,KeyError) as exc:parser.exit(1,f'Map-data validation failed: {exc}\n')


if __name__=='__main__':main()
