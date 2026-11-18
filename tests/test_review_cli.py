import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from polyviz.classifier import TAXONOMY,convert
from polyviz.review import initialize,annotate,export_reference


class ReviewCLITests(unittest.TestCase):
    def test_partial_human_reference_requires_explicit_coverage(self):
        policy=json.loads(TAXONOMY.read_text())
        bills=[{'state':'CA','session_id':'TEST','bill_number':number,'title':'Housing assistance'} for number in ['AB1','AB2']]
        session=initialize(bills,policy)
        annotate(session,session['records'][0]['id'],'assigned',['housing'],{'housing':'Housing'},'Direct housing provision.','test-reviewer')
        reference=export_reference(session,True)
        predictions={'bills':[convert(bill,policy) for bill in bills]}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name,value in [('bills',bills),('reference',reference),('predictions',predictions)]:
                (root/(name+'.json')).write_text(json.dumps(value))
            command=[sys.executable,'-m','polyviz.evaluate',str(root/'bills.json'),str(root/'reference.json'),
                     '--predictions',str(root/'predictions.json'),'--require-user-review','--output',str(root/'report.json')]
            blocked=subprocess.run(command,capture_output=True,text=True)
            self.assertNotEqual(blocked.returncode,0)
            success=subprocess.run(command+['--allow-partial-reference'],capture_output=True,text=True)
            self.assertEqual(success.returncode,0,success.stderr)
            report=json.loads((root/'report.json').read_text())
            self.assertEqual(report['count'],1)
            self.assertEqual(report['total_input_count'],2)
            self.assertEqual(report['scoring_coverage'],0.5)

    def test_assistant_reference_cannot_claim_user_review(self):
        policy=json.loads(TAXONOMY.read_text())
        bills=[{'state':'CA','session_id':'TEST','bill_number':'AB1','title':'Housing'}]
        reference={'labels':{'CA-TEST-AB1':['housing']},'annotations':{'CA-TEST-AB1':{'review_status':'assistant_draft'}}}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/'bills.json').write_text(json.dumps(bills))
            (root/'reference.json').write_text(json.dumps(reference))
            result=subprocess.run([sys.executable,'-m','polyviz.evaluate',str(root/'bills.json'),str(root/'reference.json'),
                                   '--require-user-review','--output',str(root/'report.json')],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('user-submitted',result.stderr)
            self.assertFalse((root/'report.json').exists())


if __name__=='__main__': unittest.main()
