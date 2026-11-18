import csv
from pathlib import Path
import tempfile
import unittest
from polyviz.transfer_audit import prepare_florida
from polyviz.external_review import fingerprint


class TransferAuditTests(unittest.TestCase):
    def test_duplicate_conflicting_invalid_and_fit_overlap_records(self):
        rows=[('HB:1-1993','School rules','1993','6'),('HB:1-1993','School rules','1993','6'),
              ('HB:2-1993','Conflicting rules','1993','3'),('HB:2-1993','Conflicting rules','1993','6'),
              ('HB:3-1993','Invalid label','1993','113'),('HB:4-1993','','1993','6'),
              ('HB:5-1993','Hospital rules','1993','3'),
              ('HB:6-1993','Provides 100 dollars','1993','1'),('HB:7-1993','Provides 200 dollars','1993','1')]
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'source.csv'
            with path.open('w',newline='') as f:
                writer=csv.writer(f);writer.writerow(['id','Bill_Title','year','majortopic']);writer.writerows(rows)
            records,counts=prepare_florida(path,[fingerprint('Hospital rules')])
        self.assertEqual(len(records),2)
        self.assertEqual(counts['duplicate_bill_rows_removed'],1)
        self.assertEqual(counts['conflicting_bill_rows'],2)
        self.assertEqual(counts['invalid_native_code_rows'],1)
        self.assertEqual(counts['pa_fit_or_calibration_text_overlap_rows'],1)
        self.assertEqual(counts['duplicate_title_rows_removed'],1)
