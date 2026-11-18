import unittest
from polyviz.alignment import align_topics


def review(native,score=.95):
    return {'native_candidates':[{'native_topic':native,'score':score},{'native_topic':'6','score':.02}], 'status':'possible_topic_disagreement'}


class AlignmentTests(unittest.TestCase):
    def test_topics_and_sectors_stay_separate(self):
        r=align_topics('Student health','Requires mental health training for athletic coaches.',[],review('3'))
        self.assertEqual(r['suggested_additions'],['healthcare'])
        self.assertIn('education',r['affected_sector_suggestions'])
        self.assertFalse(r['applied'])
        self.assertEqual(r['verification_status'],'not_verified')

    def test_school_tax_is_not_automatically_education(self):
        r=align_topics('Tax relief','Grants tax exempt status regarding school taxes.',['taxation','education'],review('24'))
        self.assertEqual(r['suggested_removals'],['education'])
        r=align_topics('Tax relief','Changes school taxes and school funding.',['education'],review('24'))
        self.assertEqual(r['suggested_removals'],[])

    def test_negated_tax_changes_do_not_support_topic(self):
        for summary in ['No property taxes are changed.', 'Does not change property taxes.']:
            self.assertEqual(align_topics('',summary,[],review('24'))['supported_policy_topics'],[])

    def test_rename_with_substantive_change_is_not_excluded(self):
        self.assertEqual(align_topics('Airport','Renames a regional airport.',[],review('10'))['status'],'excluded_nonpolicy')
        r=align_topics('Airport','Renames a regional airport and funds transportation resources.',[],review('10'))
        self.assertEqual(r['suggested_additions'],['transportation'])

    def test_election_citation_is_not_subject(self):
        self.assertEqual(align_topics('Elections','',[],review('20'))['suggested_additions'],['elections'])
        self.assertEqual(align_topics('','Amends Elections Code section 10.',[],review('20'))['suggested_additions'],[])

    def test_low_score_does_not_become_supported(self):
        r=align_topics('Impounded vehicles','',[],review('10',.6))
        self.assertEqual(r['status'],'uncertain')
        self.assertEqual(r['suggested_additions'],[])

    def test_missing_business_category_is_retained_as_gap(self):
        r=align_topics('Licenses','Provides beverage licenses for facilities.',[],review('15'))
        self.assertEqual(r['status'],'taxonomy_gap')
        self.assertEqual(r['suggested_additions'],[])
