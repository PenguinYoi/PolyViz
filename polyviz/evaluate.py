"""Evaluate multi-label predictions against explicit, potentially provisional labels."""
import argparse
import hashlib
import json
from pathlib import Path
from .classifier import TAXONOMY, convert


def metrics(rows):
    tp = sum(len(set(row['expected']) & set(row['predicted'])) for row in rows)
    fp = sum(len(row['extra']) for row in rows)
    fn = sum(len(row['missing']) for row in rows)
    exact = sum(row['exact_match'] for row in rows)
    return {'count':len(rows), 'exact_matches':exact,
            'exact_match_rate':exact/len(rows) if rows else None,
            'true_positive_labels':tp, 'extra_labels':fp, 'missed_labels':fn,
            'micro_precision':tp/(tp+fp) if tp+fp else None,
            'micro_recall':tp/(tp+fn) if tp+fn else None,
            'micro_f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None}


def evaluate(bills, reference, taxonomy):
    labels = reference['labels']
    if len({bill['id'] for bill in bills}) != len(bills):
        raise ValueError('Duplicate bill IDs.')
    if set(labels) != {bill['id'] for bill in bills}:
        raise ValueError('Review label IDs must exactly match bill IDs.')
    valid = {topic['id'] for topic in taxonomy['topics']}
    rows = []
    annotations = reference.get('annotations', {})
    for bill in bills:
        expected, actual = set(labels[bill['id']]), set(bill['topics'])
        if not actual <= valid or not expected <= valid:
            raise ValueError('Reference or predictions contain unknown topics.')
        if len(bill['topics']) != len(actual):
            raise ValueError('Duplicate predicted topics.')
        annotation = annotations.get(bill['id'], {})
        rows.append({'id':bill['id'], 'state':bill['state'], 'expected':sorted(expected),
                     'predicted':sorted(actual), 'missing':sorted(expected-actual),
                     'extra':sorted(actual-expected), 'exact_match':expected==actual,
                     'ambiguous':annotation.get('ambiguous'),
                     'reference_rationale':annotation.get('rationale')})
    per_topic = {}
    for topic in sorted(valid):
        tp = sum(topic in row['expected'] and topic in row['predicted'] for row in rows)
        fp = sum(topic in row['extra'] for row in rows)
        fn = sum(topic in row['missing'] for row in rows)
        per_topic[topic] = {'support':tp+fn, 'predicted':tp+fp, 'true_positive':tp,
                            'extra':fp, 'missed':fn,
                            'precision':tp/(tp+fp) if tp+fp else None,
                            'recall':tp/(tp+fn) if tp+fn else None,
                            'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None}
    report = {'taxonomy_version':taxonomy['version'],
              'reference_basis':reference.get('basis','Not provided'),
              'methods':sorted({b['classification']['method'] for b in bills}),
              'models':sorted({b['classification'].get('model','none') for b in bills}),
              'thresholds':sorted({b['classification']['threshold'] for b in bills if 'threshold' in b['classification']}),
              **metrics(rows), 'per_topic':per_topic,
              'per_state':{state:metrics([r for r in rows if r['state']==state]) for state in sorted({r['state'] for r in rows})},
              'subsets': {
                  'multiple_expected_topics':metrics([r for r in rows if len(r['expected'])>1]),
                  'no_expected_topic':metrics([r for r in rows if not r['expected']])},
              'results':rows}
    if annotations:
        report['subsets']['clear_reference'] = metrics([r for r in rows if r['ambiguous'] is False])
        report['subsets']['ambiguous_reference'] = metrics([r for r in rows if r['ambiguous'] is True])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path)
    parser.add_argument('labels',type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--taxonomy',type=Path,default=TAXONOMY)
    parser.add_argument('--allow-partial-reference',action='store_true',help='Explicitly score only IDs in a partial reference; report excluded coverage')
    parser.add_argument('--require-user-review',action='store_true',help='Require user-submitted annotations, not assistant draft labels')
    parser.add_argument('--predictions',type=Path,help='Evaluate saved output instead of keyword rules')
    args = parser.parse_args()
    try:
        protected = [args.input.resolve(),args.labels.resolve(),args.taxonomy.resolve()]
        if args.predictions: protected.append(args.predictions.resolve())
        if args.output.resolve() in protected:
            raise ValueError('Report output must not overwrite inputs.')
        taxonomy = json.loads(args.taxonomy.read_text())
        reference = json.loads(args.labels.read_text())
        if reference.get('taxonomy_version',taxonomy['version']) != taxonomy['version']:
            raise ValueError('Reference policy/taxonomy version differs; do not compare across label definitions.')
        if args.require_user_review and any(reference.get('annotations',{}).get(i,{}).get('review_status') != 'user_submitted' for i in reference['labels']):
            raise ValueError('Every scored reference must be user-submitted; assistant drafts cannot be counted as human review.')
        bills = [convert(bill,taxonomy) for bill in json.loads(args.input.read_text())]
        if args.predictions:
            predictions = json.loads(args.predictions.read_text())['bills']
            if len({b['id'] for b in bills}) != len(bills) or {b['id'] for b in predictions} != {b['id'] for b in bills}:
                raise ValueError('Prediction IDs must exactly match input IDs.')
            originals = {b['id']:b for b in bills}
            for prediction in predictions:
                original = originals[prediction['id']]
                if any(prediction.get(k) != original[k] for k in ('title','summary','state')):
                    raise ValueError('Prediction text/state differs from evaluation input.')
                if prediction['classification']['taxonomy_version'] != taxonomy['version']:
                    raise ValueError('Prediction taxonomy version differs.')
            bills = predictions
        if not bills: raise ValueError('No bills to evaluate.')
        total_count = len(bills)
        excluded = sorted({b['id'] for b in bills}-set(reference['labels']))
        if args.allow_partial_reference:
            if not set(reference['labels']) <= {b['id'] for b in bills}:
                raise ValueError('Reference contains IDs outside the input.')
            bills=[b for b in bills if b['id'] in reference['labels']]
            if not bills: raise ValueError('No reviewed records to score.')
        report = evaluate(bills,reference,taxonomy)
        report.update(total_input_count=total_count, scoring_coverage=len(bills)/total_count, excluded_reference_ids=excluded)
        paths={'input':args.input,'reference':args.labels,'taxonomy':args.taxonomy}
        if args.predictions: paths['predictions']=args.predictions
        report['file_hashes']={name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in paths.items()}
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2)+'\n')
    except (ValueError,TypeError,KeyError,OSError) as exc:
        parser.exit(1,f'Error: {exc}\n')
    print(json.dumps({k:v for k,v in report.items() if k not in {'results','per_topic','per_state','file_hashes'}},indent=2))
    print(f'Full report: {args.output}')


if __name__=='__main__': main()
