"""Audit an unchanged Pennsylvania reviewer on Florida's published native codes."""
from collections import Counter,defaultdict
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
from urllib.request import Request,urlopen
from .external_review import DEFAULT_MODEL,DEFAULT_SOURCE,NATIVE_TOPICS,calibrated_probabilities,chronological_split,fingerprint,read_source,write_json

URL='https://minio.la.utexas.edu/compagendas/datasetfiles/Florida_Legislative_Bills_2nd_Ed.csv'
EXPECTED_HASH='34b79b6d75b39003da712030d46c34b4d2e62b4b2e189cf59a8e139b8cd0f97a'
DEFAULT_FL=Path('data/raw/external/fl_cap.csv')


def prepare_florida(path,known_fingerprints=()):
    groups=defaultdict(list);counts=Counter()
    with path.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if not {'id','Bill_Title','year','majortopic'}<=set(reader.fieldnames or []):
            raise ValueError('Florida CSV schema differs from inspected source.')
        for row in reader:
            counts['raw_rows']+=1
            if row['majortopic'] not in NATIVE_TOPICS:
                counts['invalid_native_code_rows']+=1;continue
            if not re.fullmatch(r'(?:HB|SB):\d+-\d{4}',row['id']) or not row['Bill_Title'].strip():
                counts['invalid_identity_or_text_rows']+=1;continue
            groups[row['id']].append(row)
    unique=[]
    for identity,rows in sorted(groups.items()):
        if len({r['majortopic'] for r in rows})!=1:
            counts['conflicting_bill_ids']+=1;counts['conflicting_bill_rows']+=len(rows);continue
        counts['duplicate_bill_rows_removed']+=len(rows)-1
        chosen=max(rows,key=lambda r:len(r['Bill_Title']))
        unique.append({'id':identity,'year':int(chosen['year']),
                       'title':chosen['Bill_Title'].strip(),'native_topic':chosen['majortopic']})
    text_groups=defaultdict(list)
    for row in unique:text_groups[fingerprint(row['title'])].append(row)
    result=[];known=set(known_fingerprints)
    for text,rows in sorted(text_groups.items()):
        if len({r['native_topic'] for r in rows})!=1:
            counts['conflicting_title_rows']+=len(rows);continue
        if text in known:
            counts['pa_fit_or_calibration_text_overlap_rows']+=len(rows);continue
        counts['duplicate_title_rows_removed']+=len(rows)-1
        result.append(min(rows,key=lambda r:(r['year'],r['id'])))
    if not result:raise ValueError('No eligible Florida titles after exclusions.')
    return result,dict(counts)


def audit(source,pa_source,model_dir,output):
    import joblib
    import numpy as np
    from sklearn.metrics import accuracy_score,f1_score,classification_report
    if hashlib.sha256(source.read_bytes()).hexdigest()!=EXPECTED_HASH:
        raise ValueError('Florida snapshot checksum differs; inspect the new source first.')
    artifact=model_dir/'reviewer.joblib';before=hashlib.sha256(artifact.read_bytes()).hexdigest()
    bundle=joblib.load(artifact)
    pa_records,_=read_source(pa_source);train,cal,_,_=chronological_split(pa_records)
    known={fingerprint(r['text']) for r in train+cal}
    records,counts=prepare_florida(source,known)
    scores=calibrated_probabilities(bundle['model'].decision_function(bundle['vectorizer'].transform([r['title'] for r in records])),bundle['calibration'])
    order=np.argsort(scores,axis=1)[:,::-1];classes=bundle['model'].classes_
    predicted=[str(classes[row[0]]) for row in order];expected=[r['native_topic'] for r in records]
    selected=[i for i,row in enumerate(order) if scores[i,row[0]]>=0.8 and scores[i,row[0]]-scores[i,row[1]]>=0.25]
    assert hashlib.sha256(artifact.read_bytes()).hexdigest()==before,'Audit changed the fitted model.'
    report={'task':'Cross-state primary-native-topic agreement on source-provided Florida codes, NOT PolyViz direct-topic/sector accuracy',
      'source':{'dataset':'Florida Policy Agendas Project, second edition','url':URL,
                'codebook_url':'https://minio.la.utexas.edu/compagendas/codebookfiles/CAP_Project_Codebook_1.pdf',
                'sha256':EXPECTED_HASH,'label_provenance':'Published research-project native major-topic codes; per-record coding/validation process is not identified in the file.'},
      'model':'unchanged_pa_primary_v2','model_sha256':before,'training_state':'PA','evaluation_state':'FL',
      'years':sorted({r['year'] for r in records}),'count':len(records),'filters':counts,
      'primary_topic_agreement':float(accuracy_score(expected,predicted)),
      'macro_f1':float(f1_score(expected,predicted,average='macro',zero_division=0)),
      'top3_primary_topic_recall':sum(y in [str(classes[j]) for j in row[:3]] for y,row in zip(expected,order))/len(records),
      'high_score_subset':{'probability_cutoff':0.8,'margin_cutoff':0.25,'count':len(selected),
                          'coverage':len(selected)/len(records),
                          'primary_topic_agreement':sum(expected[i]==predicted[i] for i in selected)/len(selected) if selected else None},
      'per_native_topic':classification_report(expected,predicted,output_dict=True,zero_division=0),
      'limitations':['Title-only Florida input differs from Pennsylvania legislative descriptions.',
                    'The Florida codebook adapts Pennsylvania categories; their meanings are not guaranteed identical.',
                    'Duplicates and conflicting/invalid source codes were excluded, not silently corrected.',
                    'No training, calibration, or threshold tuning used Florida labels in this audit.',
                    'Single primary source labels do not establish absence of secondary policy topics.',
                    'This is not a representative all-state or current-session benchmark.']}
    write_json(output,report)
    write_json(Path('data/generated/fl_transfer_predictions.json'),{'records':[{**r,'predicted_native_topic':p,'score':float(scores[i,order[i,0]])} for i,(r,p) in enumerate(zip(records,predicted))]})
    print(json.dumps({k:report[k] for k in ['count','years','primary_topic_agreement','macro_f1','top3_primary_topic_recall','high_score_subset']},indent=2))
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=DEFAULT_FL);p.add_argument('--pa-source',type=Path,default=DEFAULT_SOURCE)
    p.add_argument('--model-dir',type=Path,default=DEFAULT_MODEL)
    p.add_argument('--output',type=Path,default=Path('examples/evaluation/external/fl_transfer_report.json'))
    p.add_argument('--download',action='store_true',help='Allow public source download if the Florida file is absent')
    args=p.parse_args()
    try:
        if args.output.resolve() in {args.source.resolve(),args.pa_source.resolve(),(args.model_dir/'reviewer.joblib').resolve()}:
            raise ValueError('Report must not overwrite source data or model.')
        if not args.source.exists() and args.download:
            with urlopen(Request(URL,headers={'User-Agent':'PolyViz research pilot'}),timeout=45) as response:data=response.read(20_000_001)
            if len(data)>20_000_000 or not data.startswith(b'id,Bill_Title,'):raise ValueError('Unexpected Florida download.')
            args.source.parent.mkdir(parents=True,exist_ok=True);args.source.write_bytes(data)
        audit(args.source,args.pa_source,args.model_dir,args.output)
    except (ValueError,OSError,KeyError,ImportError) as exc:p.exit(1,f'Transfer audit error: {exc}\n')


if __name__=='__main__':main()
