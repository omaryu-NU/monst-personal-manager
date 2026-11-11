import unittest
from catalog_image_probe_gate import verify_report


def sample():
    return {'dryRun':True,'attempted':2,'verifiedCount':1,'updatedRecords':0,'rateLimited':False,
            'results':[{'id':'112','status':'verified','http_status':200},{'id':'113','status':'http_error','http_status':404}]}

class TestPhase15ProbeGate(unittest.TestCase):
    def test_good(self): self.assertEqual(verify_report(sample()),[])
    def test_rate_limit(self):
        r=sample();r['rateLimited']=True
        self.assertTrue(verify_report(r))
    def test_apply_not_allowed(self):
        r=sample();r['dryRun']=False;r['updatedRecords']=1
        self.assertGreaterEqual(len(verify_report(r)),2)
    def test_limit(self):
        r=sample();r['attempted']=4
        self.assertTrue(verify_report(r))
    def test_verified_mismatch(self):
        r=sample();r['verifiedCount']=2
        self.assertTrue(verify_report(r))
    def test_bad_results(self):
        r=sample();r['results']=[]
        self.assertTrue(verify_report(r))
    def test_no_candidates(self):
        r={'dryRun':True,'attempted':0,'verifiedCount':0,'updatedRecords':0,'rateLimited':False,'results':[]}
        self.assertEqual(verify_report(r),[])

if __name__=='__main__': unittest.main()
