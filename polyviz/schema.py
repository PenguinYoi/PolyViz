"""Versioned bill schema and controlled, advisory issue candidates. No APIs."""
import argparse
from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
ISSUES=ROOT/'data/issue-taxonomy.json'
AXES=('issue_tags','affected_sectors','policy_actions')


def to_v2(bill, detect=False, taxonomy=None):
    """Preserve legacy topics and identities; never infer new labels in migration."""
    result=deepcopy(bill)
    topics=result.get('policy_topics',result.get('topics',[]))
    if 'policy_topics' in result and 'topics' in result and result['topics']!=topics:
        raise ValueError('Conflicting topics and policy_topics; resolve before migration.')
    result['policy_topics']=list(topics)
    result['topics']=list(topics)  # Compatibility alias for existing evaluators.
    dates=dict(result.get('dates',{}))
    for key in ('introduced','enacted','effective'):
        legacy=result.get(key+'_date')
        if legacy and dates.get(key) and legacy!=dates[key]:
            raise ValueError('Conflicting '+key+' dates.')
        dates.setdefault(key,legacy)
        if dates[key] is not None:date.fromisoformat(dates[key])
    result['dates']=dates
    for axis in AXES:result.setdefault(axis,[])
    if not detect:return result
    taxonomy=taxonomy or json.loads(ISSUES.read_text())
    text='\n'.join([result.get('title',''),result.get('summary','')])
    evidence=[]
    # These matches are intentionally not promoted to assigned labels. Negation,
    # repeal and operative meaning require a semantic or reviewed decision.
    for axis in AXES:
        for label in taxonomy[axis]:
            for alias in label.get('aliases',[]):
                pattern=r'(?<!\w)'+re.escape(alias).replace(r'\ ',r'[\s-]+')+r'(?!\w)'
                for found in re.finditer(pattern,text,re.I):
                    evidence.append({'axis':axis,'label':label['id'],'excerpt':found.group(),
                                     'start':found.start(),'end':found.end(),
                                     'status':'candidate_not_assigned'})
    result['issue_classification']={
        'method':'controlled_alias_candidates','method_version':'1',
        'taxonomy_version':taxonomy['version'],
        'taxonomy_sha256':hashlib.sha256(json.dumps(taxonomy,sort_keys=True).encode()).hexdigest(),
        'input_sha256':hashlib.sha256(text.encode()).hexdigest(),
        'input_format':'title + newline + summary','review_status':'needs_review',
        'outcome':'candidates_found' if evidence else 'unresolved',
        'candidates':evidence,
        'note':'Candidates are not assignments. Negation, repeal, citations and operative provisions have not been verified. No candidates does not establish absence.'}
    return result


def migrate(document):
    if not isinstance(document,dict) or document.get('schema_version') not in (1,2):
        raise ValueError('Expected a schema-version 1 or 2 bill document.')
    result=deepcopy(document)
    result['bills']=[to_v2(bill) for bill in result['bills']]
    result['schema_version']=2
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:
        if args.input.resolve()==args.output.resolve():raise ValueError('Preserve input; choose another output.')
        result=migrate(json.loads(args.input.read_text()))
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2)+'\n')
    except (OSError,ValueError,TypeError,KeyError) as exc:parser.exit(1,f'Migration error: {exc}\n')
    print(f'Migrated {len(result["bills"])} bills without reclassification.')


if __name__=='__main__':main()
