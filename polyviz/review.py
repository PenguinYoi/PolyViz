"""Blind, local human annotation workflow. No model predictions are shown."""
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from .classifier import convert


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary = path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
    os.replace(temporary,path)


def initialize(payload, policy):
    originals = payload if isinstance(payload,list) else [payload]
    bills = [convert(bill,policy) for bill in originals]
    if not bills or len({b['id'] for b in bills}) != len(bills):
        raise ValueError('Expected nonempty bills with unique identities.')
    records = [{'id':b['id'],'state':b['state'],'title':b['title'],'summary':b['summary'],
                'source_url':b['source']['url'],'outcome':'pending','topics':None,
                'evidence':{},'affected_sectors':None,'sector_evidence':{},'notes':'','reviewer':None,'reviewed_at':None} for b in bills]
    inputs = [{k:r[k] for k in ('id','state','title','summary','source_url')} for r in records]
    return {'schema_version':1,'policy':policy,'policy_hash':digest(policy),
            'input_hash':digest(inputs),'records':records}


def validate_session(session):
    if digest(session['policy']) != session['policy_hash']:
        raise ValueError('Policy changed inside the session; initialize a new review version.')
    inputs = [{k:r[k] for k in ('id','state','title','summary','source_url')} for r in session['records']]
    if digest(inputs) != session['input_hash']:
        raise ValueError('Review input text changed; initialize a new review version.')


def annotate(session, record_id, outcome, topics, evidence, notes, reviewer, affected_sectors=None, sector_evidence=None):
    validate_session(session)
    records = [r for r in session['records'] if r['id']==record_id]
    if len(records)!=1: raise ValueError('Unknown or duplicate record ID.')
    record=records[0]
    if outcome not in {'assigned','outside_taxonomy','needs_more_text'}:
        raise ValueError('Choose assigned, outside_taxonomy, or needs_more_text.')
    if not reviewer.strip() or not notes.strip():
        raise ValueError('Reviewer and rationale are required.')
    valid={t['id'] for t in session['policy']['topics']}
    if len(topics)!=len(set(topics)) or not set(topics)<=valid:
        raise ValueError('Unknown or duplicate topic IDs.')
    if (outcome=='assigned') != bool(topics):
        raise ValueError('Only assigned outcomes may contain topics, and require at least one.')
    if set(evidence)!=set(topics):
        raise ValueError('Provide evidence for every assigned topic, and no others.')
    for quote in evidence.values():
        if not isinstance(quote,str) or not quote.strip() or not (quote in record['title'] or quote in record['summary']):
            raise ValueError('Evidence must be an exact excerpt of the title or summary.')
    # Keep changes separate from validation; invalid input leaves old records intact.
    if affected_sectors is not None:
        valid_sectors={sector['id'] for sector in session['policy'].get('sectors',[])}
        if len(affected_sectors)!=len(set(affected_sectors)) or not set(affected_sectors)<=valid_sectors:
            raise ValueError('Unknown or duplicate affected-sector IDs.')
        sector_evidence=sector_evidence or {}
        if set(sector_evidence)!=set(affected_sectors):
            raise ValueError('Provide evidence for every affected sector.')
        for quote in sector_evidence.values():
            if not isinstance(quote,str) or not quote.strip() or not (quote in record['title'] or quote in record['summary']):
                raise ValueError('Sector evidence must be an exact input excerpt.')
    elif sector_evidence:
        raise ValueError('Sector evidence requires affected-sector labels.')
    updated={**record,'outcome':outcome,'topics':list(topics) if outcome!='needs_more_text' else None,
             'evidence':evidence,'affected_sectors':affected_sectors,'sector_evidence':sector_evidence or {},'notes':notes.strip(),'reviewer':reviewer.strip(),
             'reviewed_at':datetime.now(timezone.utc).isoformat()}
    if record['outcome'] != 'pending':
        updated['history'] = record.get('history', []) + [{k:record[k] for k in ('outcome','topics','evidence','affected_sectors','sector_evidence','notes','reviewer','reviewed_at')}]
    record.update(updated)


def export_reference(session, allow_incomplete=False):
    validate_session(session)
    scored=[r for r in session['records'] if r['outcome'] in {'assigned','outside_taxonomy'}]
    unresolved=[{'id':r['id'],'outcome':r['outcome'],'notes':r['notes']} for r in session['records'] if r['outcome'] not in {'assigned','outside_taxonomy'}]
    if unresolved and not allow_incomplete:
        raise ValueError(f'{len(unresolved)} records are pending or need more text; use --allow-incomplete to explicitly exclude them.')
    if not scored: raise ValueError('No resolved records to export.')
    for record in scored:
        # Revalidate persisted annotations without changing their original timestamps.
        clone=json.loads(json.dumps(session))
        annotate(clone,record['id'],record['outcome'],record['topics'],record['evidence'],record['notes'],record['reviewer'] or '',record.get('affected_sectors'),record.get('sector_evidence'))
    return {'basis':'User-entered blind annotations. Reviewer identity is self-reported, not externally verified.',
            'taxonomy_version':session['policy']['version'],'policy_hash':session['policy_hash'],
            'total_input_count':len(session['records']),'scored_count':len(scored),
            'excluded_records':unresolved,
            'labels':{r['id']:r['topics'] for r in scored},
            'affected_sectors':{r['id']:r['affected_sectors'] for r in scored if r.get('affected_sectors') is not None},
            'annotations':{r['id']:{'rationale':r['notes'],'evidence':r['evidence'],
                'reviewer':r['reviewer'],'reviewed_at':r['reviewed_at'],
                'outcome':r['outcome'],'sector_evidence':r.get('sector_evidence',{}),'review_status':'user_submitted'} for r in scored}}


def run_interactive(session, path, reviewer, record_id=None, limit=5):
    print('Topic IDs: '+', '.join(t['id'] for t in session['policy']['topics']))
    sectors={s['id'] for s in session['policy'].get('sectors',[])}
    if sectors: print('Affected sectors (separate axis): '+', '.join(sorted(sectors)))
    print('No model predictions or proposed reference labels are displayed. q saves/exits; s skips.')
    completed=0
    for record in session['records']:
        if record_id is not None and record['id'] != record_id: continue
        if record_id is None and record['outcome']!='pending': continue
        print('\n'+record['id']+'\n'+record['title']+'\n'+record['summary'])
        print('Source: '+str(record['source_url']))
        while True:
            answer=input('Topics (comma-separated), outside, more, s, or q: ').strip()
            if answer=='q': return
            if answer=='s': break
            topics=[] if answer in {'outside','more'} else [t.strip() for t in answer.split(',') if t.strip()]
            outcome={'outside':'outside_taxonomy','more':'needs_more_text'}.get(answer,'assigned')
            valid={t['id'] for t in session['policy']['topics']}
            if answer not in {'outside','more'} and (not topics or not set(topics)<=valid or len(topics)!=len(set(topics))):
                print('Enter unique topic IDs from the list.');continue
            evidence={topic:input(f'Exact supporting excerpt for {topic}: ') for topic in topics}
            affected_sectors=None; sector_evidence={}
            if sectors:
                sector_answer=input('Affected sectors (comma-separated, empty for none, ? if not reviewed): ').strip()
                if sector_answer!='?':
                    affected_sectors=[x.strip() for x in sector_answer.split(',') if x.strip()]
                    if not set(affected_sectors)<=sectors or len(affected_sectors)!=len(set(affected_sectors)):
                        print('Invalid affected sectors; annotation not saved.');continue
                    sector_evidence={sector:input(f'Exact supporting excerpt for sector {sector}: ') for sector in affected_sectors}
            notes=input('Why? (required): ')
            try:
                annotate(session,record['id'],outcome,topics,evidence,notes,reviewer,affected_sectors,sector_evidence)
            except ValueError as exc:
                print('Not saved: '+str(exc));continue
            save(path,session);completed+=1;print('Saved.');break
        if completed>=limit:
            print(f'Batch complete: {completed} annotations saved. Run the command again to continue.');return
    print('Review pass finished; skipped/pending and needs-more-text records are not resolved labels.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    init=commands.add_parser('init');init.add_argument('input',type=Path)
    init.add_argument('--policy',required=True,type=Path);init.add_argument('--session',required=True,type=Path)
    run=commands.add_parser('run');run.add_argument('--session',required=True,type=Path);run.add_argument('--reviewer',required=True);run.add_argument('--record',help='Revisit one record, retaining annotation history');run.add_argument('--limit',type=int,default=5,help='Maximum saved annotations per run (default 5)')
    status=commands.add_parser('status');status.add_argument('--session',required=True,type=Path)
    export=commands.add_parser('export');export.add_argument('--session',required=True,type=Path)
    export.add_argument('--output',required=True,type=Path);export.add_argument('--allow-incomplete',action='store_true')
    args=parser.parse_args()
    try:
        if args.command=='init':
            if args.session.exists(): raise ValueError('Session already exists; use a new filename to preserve prior work.')
            data=initialize(json.loads(args.input.read_text()),json.loads(args.policy.read_text()))
            save(args.session,data);print(f'Created blind review with {len(data["records"])} bills.');return
        session=json.loads(args.session.read_text());validate_session(session)
        if args.command=='run':
            if args.limit<1: raise ValueError('--limit must be positive.')
            if args.record and args.record not in {r['id'] for r in session['records']}:
                raise ValueError('Unknown record ID.')
            run_interactive(session,args.session,args.reviewer,args.record,args.limit)
        elif args.command=='status':
            print(json.dumps({outcome:sum(r['outcome']==outcome for r in session['records']) for outcome in ['pending','assigned','outside_taxonomy','needs_more_text']},indent=2))
        elif args.command=='export':
            if args.output.resolve()==args.session.resolve(): raise ValueError('Export must not overwrite session.')
            reference=export_reference(session,args.allow_incomplete);save(args.output,reference)
            print(f'Exported {reference["scored_count"]}/{reference["total_input_count"]} records.')
    except (ValueError,KeyError,TypeError,OSError,EOFError,KeyboardInterrupt) as exc:
        parser.exit(1,f'Review stopped: {exc}\nSaved annotations are retained.\n')


if __name__=='__main__': main()
