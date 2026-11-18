"""Transparent contextual crosswalk suggestions, separate from source predictions.

This layer never verifies or overwrites PolyViz labels. Rules apply across bills,
not to hard-coded bill identities. Their regression cases are not accuracy tests.
"""
import re
from .nli import prepare_passages

VERSION='1'
CODEBOOK='https://minio.la.utexas.edu/compagendas/codebookfiles/II._Policy_Topics_Coding_061719_1.pdf'


def align_topics(title,summary,topics,review):
    text=prepare_passages(title,summary)
    candidates=review['native_candidates']
    top=candidates[0];native=top['native_topic']
    margin=top['score']-candidates[1]['score'] if len(candidates)>1 else top['score']
    result={'version':VERSION,'policy_version':'2-draft','status':'uncertain',
            'supported_policy_topics':[], 'suggested_additions':[], 'suggested_removals':[],
            'affected_sector_suggestions':[], 'evidence':[], 'taxonomy_gaps':[],
            'analysis_eligibility':'not_determined','applied':False,
            'verification_status':'not_verified','codebook_url':CODEBOOK}
    def match(pattern): return re.search(pattern,text,re.I)
    def add(topic,pattern,reason,reference):
        found=match(pattern)
        if found:
            if topic not in result['supported_policy_topics']:result['supported_policy_topics'].append(topic)
            result['evidence'].append({'axis':'policy_topic','label':topic,'excerpt':found.group(0),
                                      'reason':reason,'source_codebook_context':reference})
        return found
    def sector(label,pattern,reason):
        found=match(pattern)
        if found and label not in result['affected_sector_suggestions']:
            result['affected_sector_suggestions'].append(label)
            result['evidence'].append({'axis':'affected_sector','label':label,'excerpt':found.group(0),'reason':reason})
    # Pure renaming is not a transport policy change. A rename plus substantive
    # changes must not be excluded based only on its first verb.
    pure_rename=re.fullmatch(r'\s*Renames\s+[^.;]+\.?\s*',summary,re.I)
    substantive=re.search(r'\b(?:and|also)\s+(?:changes?|revises?|requires?|authorizes?|funds?|amends?|provides?)\b',summary,re.I)
    if pure_rename and not substantive:
        result.update(status='excluded_nonpolicy',analysis_eligibility='exclude_pure_renaming',
                      suggested_removals=list(topics))
        result['evidence'].append({'axis':'analysis_eligibility','excerpt':summary,
                                  'reason':'The complete supplied summary describes only renaming; institution type alone does not establish a substantive policy change.'})
        return result
    if top['score']<0.8 or margin<0.25:
        return result
    # Distinguish a code citation from the actual operative subject.
    if native in {'20','2'}:
        add('elections',r'\b(?:elections?(?!\s+Code\b)|voter registration|campaign finance|redistricting)\b',
            'Explicit electoral subject within a broader government/civil-rights source category.',
            '206 voting rights; 2011 redistricting; 2012 electoral administration. These subtopics are context references, not predicted subtopic labels.')
    tax=None
    if native in {'1','24','15'}:
        unchanged=match(r'\b(?:no|not)\b[^.!?;]{0,65}\b(?:tax(?:es)?|tax rates?|tax credits?|tax exemptions?)\b[^.!?;]{0,35}\b(?:changed|amended|revised)\b')
        unchanged = unchanged or match(r'\b(?:does not|will not|without)\s+(?:change|amend|revise|changing|amending|revising)\b[^.!?;]{0,50}\btax')
        if not unchanged:
            tax=add('taxation',r'\b(?:tax exempt status|tax exemptions?|transaction tax|privilege tax|tax credits?|tax relief|ad valorem taxation|property tax(?:es)?|school taxes)\b',
                'Explicit tax instrument is supported by the description; broad local-government/commerce categories can contain tax provisions.',
                '107 state taxation; 2404 local taxes; sector-specific tax provisions may use sector codes.')
        # A school-tax exemption alone does not change instruction or school operations.
        school_tax=match(r'\bschool taxes\b')
        education_change=match(r'\b(?:curriculum|tuition|teacher duties|classroom instruction|school funding|school staffing)\b')
        if tax and school_tax and not education_change and 'education' in topics:
            result['suggested_removals'].append('education')
            result['evidence'].append({'axis':'policy_topic','label':'education','action':'suggest_removal',
                                      'excerpt':school_tax.group(0),'reason':'Only a school-tax reference is present; the supplied description does not establish an education provision.'})
    if native=='10':
        add('transportation',r'\b(?:abandoned (?:recreational |motor )?vehicles|impounded vehicles|vehicle impoundment|driver licensing|transportation resources|freight rail)\b',
            'Explicit vehicle/transport regulation, not an incidental mention of a vehicle.',
            '1000 transportation and vehicle regulation; source primary topic is not a complete multi-label reference.')
    if native=='3':
        add('healthcare',r'\b(?:mental health training|medical treatment|patient care|health insurance coverage)\b',
            'Explicit health-service or health-practice subject supports a healthcare suggestion.',
            '325 health training; 333 mental health; do not map every health-sector tax bill to healthcare.')
        sector('healthcare',r'\b(?:student health|mental health|medical treatment|patient care)\b','Health-related services or practice explicitly targeted.')
        # Students alone do not create an education policy topic.
        if match(r'\bstudent health\b'):
            sector('education',r'\bstudent health\b','Student services are an affected sector; this does not independently establish an educational duty or provision.')
    if native=='15':
        licensing=match(r'\b(?:beverage licenses|special licenses|fantasy contests|sports wagering|licensure)\b')
        if licensing:
            sector('commerce',r'\b(?:beverage licenses|special licenses|fantasy contests|sports wagering|licensure)\b','Commercial licensing or regulated commercial activity.')
        # Require a stated criminal/legal effect, not merely a Criminal Code citation.
        add('public_safety',r'\b(?:creating criminal offenses|increasing criminal penalties|shall not be convicted of gambling)\b',
            'Description explicitly changes criminal liability or offenses.',
            '1526 gambling/business regulation can overlap with criminal-law provisions; a separate substantive provision supports the extra topic.')
        if licensing and not result['supported_policy_topics']:
            result['taxonomy_gaps'].append({'native_topic':'15','domain':'business_licensing',
                                           'reason':'Commercial licensing does not automatically fit the ten policy topics. No new policy category is silently created.'})
    if native=='24' and not result['supported_policy_topics']:
        result['taxonomy_gaps'].append({'native_topic':'24','domain':'local_government_finance_or_governance',
                                       'reason':'Current description and broad source category do not identify a supported topic among the ten. Fuller text may reveal additional provisions.'})
        sector('government',r'\b(?:local government|community facilities districts|municipalities|county)\b','Local-government bodies explicitly targeted.')
    supported=set(result['supported_policy_topics']);existing=set(topics)
    result['suggested_additions']=sorted(supported-existing)
    if result['suggested_additions'] and result['suggested_removals']:
        result['status']='suggested_topic_revision'
    elif result['suggested_additions']:
        result['status']='suggested_topic_addition'
    elif result['suggested_removals']:
        result['status']='suggested_topic_removal'
    elif result['taxonomy_gaps']:
        result['status']='taxonomy_gap'
    elif supported:
        result['status']='contextually_aligned'
    elif review['status']=='broad_topic_agreement':
        result['status']='broad_agreement_only'
    else:
        result['status']='no_context_rule'
    return result
