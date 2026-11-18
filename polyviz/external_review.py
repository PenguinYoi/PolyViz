"""Train and run a local reviewer from externally coded Pennsylvania legislation.

Source-native primary-topic prediction is NOT PolyViz multi-label verification.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

SOURCE_URL = 'https://minio.la.utexas.edu/compagendas/datasetfiles/AlltopicsBillsandResolutionsRegularSessions1979_2019_11132019_CAP.csv'
SOURCE_PAGE = 'https://comparativeagendas.net/datasets_codebooks'
SOURCE_HASH = '0d9909058b2f00d6005840484d5fb711930e039c49b060dd6d48e2ba4d1bded3'
DEFAULT_SOURCE = Path('data/raw/external/pa_cap.csv')
DEFAULT_MODEL = Path('data/models/pa-primary-v2')
NATIVE_TOPICS = {
 '1':'Fiscal and economic issues','2':'Civil rights and liberties','3':'Health',
 '4':'Agriculture','5':'Labor, employment, immigration','6':'Education',
 '7':'Environment','8':'Energy','9':'Immigration','10':'Transportation',
 '12':'Law, crime, and family','13':'Social welfare',
 '14':'Community development and housing','15':'Banking, finance, domestic commerce',
 '16':'Defense','17':'Space, science, technology, communications','18':'Foreign trade',
 '19':'International affairs and foreign aid','20':'State government operations',
 '21':'Public lands and water management','24':'Local government and governance'}
# Broad overlaps are deliberately not treated as an exact crosswalk. In particular,
# native law/family, housing/development and sector-specific tax labels differ.
OVERLAPS = {'3':['healthcare'],'5':['labor'],'6':['education'],'7':['environment'],
            '8':['energy'],'10':['transportation'],'12':['public_safety'],'14':['housing']}


def write_json(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')


def fingerprint(text):
    """Group identical descriptions even when only numbers or punctuation differ."""
    text = re.sub(r'\d+(?:[.,]\d+)*',' NUMBER ',text.casefold())
    return ' '.join(re.findall(r'[a-z]+',text))


def read_source(path):
    records=[]; excluded=Counter()
    with path.open(encoding='utf-8-sig',newline='') as source:
        reader=csv.DictReader(source)
        required={'bill_id','bill_no','year','nuc','majortopic','subtopic','subtype','commemorative','source'}
        if not required <= set(reader.fieldnames or []):
            raise ValueError('Source CSV does not match the documented PA dataset schema.')
        for row in reader:
            number=re.sub(r'\s+','',row['bill_no']).upper()
            match=re.fullmatch(r'(HB|SB)0*(\d+)',number)
            if not match or row['subtype'] not in {'B','null',''}:
                excluded['not_eligible_bill']+=1;continue
            if row['commemorative']=='1':
                excluded['commemorative']+=1;continue
            if row['majortopic'] not in NATIVE_TOPICS or len(row['nuc'].strip())<20:
                excluded['missing_label_or_text']+=1;continue
            bill_id=row['bill_id']
            if not re.match(r'^\d{4}0(?:HB|SB)\d+$',bill_id):
                excluded['unrecognized_session_identity']+=1;continue
            start=int(bill_id[:4]);number=match[1]+str(int(match[2]))
            records.append({'id':f'PA-{start}-{start+1}-REGULAR-{number}',
                'source_id':bill_id,'session_start':start,'text':row['nuc'].strip(),
                'native_topic':row['majortopic'],'native_subtopic':row['subtopic'],
                'source_url':row['source'].strip('#')})
    if not records: raise ValueError('No eligible labeled bills in source.')
    if len({r['id'] for r in records})!=len(records):
        raise ValueError('Duplicate source bill identities; inspect before training.')
    return records,dict(excluded)


def chronological_split(records):
    groups=defaultdict(list)
    for record in records: groups[fingerprint(record['text'])].append(record)
    unique=[];conflicts=0;duplicates=0
    for group in groups.values():
        if len({r['native_topic'] for r in group})>1:
            conflicts+=len(group);continue
        earliest=min(group,key=lambda r:(r['session_start'],r['source_id']))
        unique.append(earliest);duplicates+=len(group)-1
    train=[r for r in unique if r['session_start']<2011]
    calibration=[r for r in unique if 2011<=r['session_start']<2013]
    test=[r for r in unique if r['session_start']>=2013]
    if not all([train,calibration,test]): raise ValueError('Temporal train/calibration/test sets must all be nonempty.')
    return train,calibration,test,{'duplicate_descriptions_removed':duplicates,
                                  'conflicting_label_group_rows_excluded':conflicts}


def fit_sigmoids(scores, labels, classes):
    """Fit monotone Platt-style sigmoid maps on a disjoint calibration period."""
    import numpy as np
    from scipy.optimize import minimize
    from scipy.special import expit
    scores=np.asarray(scores,dtype=float)
    if not np.isfinite(scores).all(): raise ValueError('Nonfinite calibration scores.')
    parameters=[]
    for column,category in enumerate(classes):
        x=scores[:,column];positive=np.array([label==category for label in labels])
        n_pos=int(positive.sum());n_neg=len(labels)-n_pos
        target=np.where(positive,(n_pos+1)/(n_pos+2),1/(n_neg+2))
        def objective(params):
            z=params[0]*x+params[1]
            residual=expit(z)-target
            # Avoid vector matmul: some platform BLAS builds emit spurious
            # overflow/divide warnings in sklearn's scalar-gradient sigmoid fit.
            loss=np.sum(np.logaddexp(0,z)-target*z)+1e-6*params[0]**2
            gradient=np.array([np.sum(residual*x)+2e-6*params[0],np.sum(residual)])
            return float(loss),gradient
        initial=[0.,float(np.log((n_pos+1)/(n_neg+1)))]
        result=minimize(objective,initial,jac=True,method='L-BFGS-B',bounds=[(0,None),(None,None)])
        if not result.success or not np.isfinite(result.x).all():
            raise ValueError(f'Sigmoid calibration failed for native topic {category}.')
        parameters.append(result.x.tolist())
    return parameters


def calibrated_probabilities(scores, parameters):
    import numpy as np
    from scipy.special import expit
    scores=np.asarray(scores,dtype=float);parameters=np.asarray(parameters,dtype=float)
    if scores.ndim!=2 or parameters.shape!=(scores.shape[1],2):
        raise ValueError('Invalid score/calibration dimensions.')
    probabilities=expit(scores*parameters[:,0]+parameters[:,1])
    denominator=probabilities.sum(axis=1,keepdims=True)
    if not np.isfinite(probabilities).all() or (denominator<=0).any():
        raise ValueError('Invalid calibrated probabilities.')
    return probabilities/denominator


def train_model(source_path, model_dir):
    import joblib
    import numpy as np
    import sklearn
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics import accuracy_score,classification_report,f1_score
    from sklearn.svm import LinearSVC
    if (model_dir/'reviewer.joblib').exists():
        raise ValueError('Model already exists; use a new --model-dir to preserve its evaluation.')
    source_hash=hashlib.sha256(source_path.read_bytes()).hexdigest()
    if source_hash!=SOURCE_HASH:
        raise ValueError('Source snapshot checksum differs from the inspected research download; inspect provenance before training.')
    records,excluded=read_source(source_path)
    train,calibration,test,dedup=chronological_split(records)
    print(f'Eligible bills: {len(records)}; train={len(train)}, calibration={len(calibration)}, test={len(test)}',flush=True)
    vectorizer=TfidfVectorizer(ngram_range=(1,2),min_df=3,max_df=0.98,
                               max_features=60000,sublinear_tf=True,strip_accents='unicode')
    x_train=vectorizer.fit_transform([r['text'] for r in train])
    base=LinearSVC(C=1.0,class_weight='balanced',random_state=20261118,dual='auto',max_iter=5000)
    base.fit(x_train,[r['native_topic'] for r in train])
    x_cal=vectorizer.transform([r['text'] for r in calibration])
    calibration_parameters=fit_sigmoids(base.decision_function(x_cal), [r['native_topic'] for r in calibration], base.classes_)
    model=base
    print('Fitted and calibrated on separate earlier sessions; evaluating untouched later sessions.',flush=True)
    y=[r['native_topic'] for r in test]
    probabilities=calibrated_probabilities(model.decision_function(vectorizer.transform([r['text'] for r in test])),calibration_parameters)
    ranking=np.argsort(probabilities,axis=1)[:,::-1]
    predicted=[str(model.classes_[order[0]]) for order in ranking]
    top3=sum(expected in [str(model.classes_[i]) for i in order[:3]] for expected,order in zip(y,ranking))/len(y)
    # Fixed before test evaluation. These are abstention controls, not a guarantee.
    confident=[i for i,order in enumerate(ranking) if probabilities[i,order[0]]>=0.8
               and probabilities[i,order[0]]-probabilities[i,order[1]]>=0.25]
    unknown_test=sorted(set(y)-set(model.classes_))
    report={'task':'External source-native SINGLE primary-topic prediction, not PolyViz multi-label accuracy',
        'source':{'dataset':'Pennsylvania Policy Database Project / Comparative Agendas',
                  'download_url':SOURCE_URL,'dataset_page':SOURCE_PAGE,
                  'sha256':hashlib.sha256(source_path.read_bytes()).hexdigest(),
                  'label_provenance':'researcher_hand_coded_primary_topic',
                  'coverage':'Pennsylvania, 1979–2016; eligible regular-session bills only'},
        'calibration_method':'Independent monotone sigmoid per native class, fitted only on 2011–2012 sessions; normalized across classes. Stable elementwise gradients avoid platform BLAS warnings.',
        'created_at':datetime.now(timezone.utc).isoformat(), 'sklearn_version':sklearn.__version__,
        'eligible_records':len(records),'exclusions':excluded,**dedup,
        'split':{'train':{'count':len(train),'session_start_before':2011},
                 'calibration':{'count':len(calibration),'session_start_range':[2011,2012]},
                 'test':{'count':len(test),'session_start_from':2013},
                 'grouping':'All descriptions normalized for numbers/punctuation; identical groups kept only at earliest occurrence. Conflicting native-label groups excluded before splitting. Near duplicates can remain.'},
        'primary_topic_accuracy':float(accuracy_score(y,predicted)),
        'macro_f1':float(f1_score(y,predicted,average='macro',zero_division=0)),
        'top3_primary_topic_recall':float(top3),
        'high_score_subset':{'probability_cutoff':0.8,'margin_cutoff':0.25,
            'count':len(confident),'coverage':len(confident)/len(test),
            'primary_topic_accuracy':sum(y[i]==predicted[i] for i in confident)/len(confident) if confident else None},
        'unseen_test_classes':unknown_test,
        'train_class_counts':dict(Counter(r['native_topic'] for r in train)),
        'calibration_class_counts':dict(Counter(r['native_topic'] for r in calibration)),
        'test_class_counts':dict(Counter(y)),
        'per_native_topic':classification_report(y,predicted,output_dict=True,zero_division=0),
        'limitations':['Single state and older periods; cross-state/current-bill accuracy is unknown.',
            'Source codes can mix policy instruments and sectors; no exact mapping to the PolyViz draft taxonomy.',
            'Single primary label does not establish that other topics are absent.',
            'Numerically normalized exact duplicates are excluded; similar paraphrases may remain.',
            'Calibration is fitted on a separate period; scores are not guarantees under domain shift.']}
    model_dir.mkdir(parents=True,exist_ok=True)
    # Serialize only locally generated models. The CLI never downloads model pickles.
    joblib.dump({'vectorizer':vectorizer,'model':model,'calibration':calibration_parameters,'report':report},model_dir/'reviewer.joblib',compress=3)
    lookup={r['id']:{**{k:r[k] for k in ('source_id','native_topic','native_subtopic','source_url')},'text_fingerprint':hashlib.sha256(fingerprint(r['text']).encode()).hexdigest()} for r in records}
    write_json(model_dir/'source_lookup.json',lookup)
    write_json(model_dir/'report.json',report)
    print(json.dumps({key:report[key] for key in ['primary_topic_accuracy','macro_f1','top3_primary_topic_recall','high_score_subset']},indent=2))
    return report


def decision(candidates, topics, state, exact_label=None):
    top=candidates[0]
    score=top['score'];margin=score-candidates[1]['score'] if len(candidates)>1 else score
    overlaps=OVERLAPS.get(top['native_topic'],[])
    if exact_label is not None:
        status='external_native_label_available'
    elif score<0.8 or margin<0.25:
        status='uncertain'
    elif not overlaps:
        status='native_category_has_no_simple_crosswalk'
    elif set(overlaps)&set(topics):
        status='broad_topic_agreement'
    else:
        status='possible_topic_disagreement'
    return {'status':status,'verification_status':'polyviz_labels_not_verified',
            'native_candidates':candidates,'score_margin':margin,
            'broad_topic_overlaps':overlaps,'exact_source_label':exact_label,
            'cross_state_transfer':state!='PA',
            'note':'Source-trained primary-topic suggestions are an automated second opinion, not a complete or verified multi-label reference. Source subjects do not separately confirm direct topics or affected sectors.'}


def review_bills(input_path,model_dir,output_path):
    import joblib
    from .classifier import TAXONOMY,convert
    if output_path.resolve()==input_path.resolve(): raise ValueError('Review output must differ from input.')
    bundle=joblib.load(model_dir/'reviewer.joblib')
    lookup=json.loads((model_dir/'source_lookup.json').read_text())
    payload=json.loads(input_path.read_text())
    if isinstance(payload,dict) and 'bills' in payload:
        bills=payload['bills']
    else:
        taxonomy=json.loads(TAXONOMY.read_text())
        bills=[convert(b,taxonomy) for b in (payload if isinstance(payload,list) else [payload])]
    if not bills or len({b['id'] for b in bills})!=len(bills): raise ValueError('Expected nonempty unique bill records.')
    texts=[]
    for b in bills:
        if not isinstance(b.get('title'),str) or not isinstance(b.get('summary',''),str): raise ValueError('Bill title and summary must be strings.')
        title=b['title'];summary=b.get('summary','')
        texts.append(title if title==summary else title+'\n'+summary)
    model=bundle['model']; probabilities=calibrated_probabilities(model.decision_function(bundle['vectorizer'].transform(texts)),bundle['calibration'])
    from .alignment import align_topics
    for bill,text,scores in zip(bills,texts,probabilities):
        order=scores.argsort()[::-1][:3]
        candidates=[{'native_topic':str(model.classes_[i]),'name':NATIVE_TOPICS[str(model.classes_[i])],
                     'score':float(scores[i])} for i in order]
        bill['external_review']=decision(candidates,bill.get('topics',[]),bill['state'],lookup.get(bill['id']))
        source_match=lookup.get(bill['id'])
        bill['external_review']['source_input_text_matches']=(source_match.get('text_fingerprint')==hashlib.sha256(fingerprint(text).encode()).hexdigest()) if source_match else None
        bill['policy_alignment']=align_topics(bill['title'],bill.get('summary',''),bill.get('topics',[]),bill['external_review'])
    document={'schema_version':1,'reviewer':'pa-source-trained-primary-v2',
        'source_sha256':bundle['report']['source']['sha256'],
        'review_summary':dict(Counter(b['external_review']['status'] for b in bills)),
        'policy_alignment_summary':dict(Counter(b['policy_alignment']['status'] for b in bills)),
        'bills':bills}
    write_json(output_path,document)
    print(json.dumps({'native_review_summary':document['review_summary'],'policy_alignment_summary':document['policy_alignment_summary']},indent=2));return document


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    download=commands.add_parser('download');download.add_argument('--output',type=Path,default=DEFAULT_SOURCE)
    train=commands.add_parser('train');train.add_argument('--source',type=Path,default=DEFAULT_SOURCE);train.add_argument('--model-dir',type=Path,default=DEFAULT_MODEL)
    review=commands.add_parser('review');review.add_argument('input',type=Path);review.add_argument('--model-dir',type=Path,default=DEFAULT_MODEL);review.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:
        if args.command=='download':
            if args.output.exists(): raise ValueError('Source file already exists; preserve the source snapshot or choose a new filename.')
            with urlopen(Request(SOURCE_URL,headers={'User-Agent':'PolyViz research pilot'}),timeout=60) as response:
                data=response.read(50_000_001)
            if len(data)>50_000_000: raise ValueError('Source exceeds the 50 MB download cap.')
            if not data.startswith(b'id,bill_id,'): raise ValueError('Download is not the expected dataset CSV.')
            args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(data)
            print(f'Downloaded {len(data)} bytes; sha256={hashlib.sha256(data).hexdigest()}')
        elif args.command=='train': train_model(args.source,args.model_dir)
        else: review_bills(args.input,args.model_dir,args.output)
    except (OSError,ValueError,KeyError,TypeError,ImportError) as exc:
        parser.exit(1,f'External review error: {exc}\n')


if __name__=='__main__': main()
