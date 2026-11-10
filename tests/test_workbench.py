import tempfile
import unittest
from pathlib import Path
from chemdb import Store, analyze

ROOT = Path(__file__).resolve().parents[1]

class WorkbenchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.store = Store(ROOT, Path(cls.tmp.name) / 'test.sqlite')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_sources_and_search(self):
        s = self.store
        self.assertEqual(s.search({'source':'compound'})['total'], 2424)
        self.assertEqual(s.search({'source':'bbb'})['total'], 10648)
        self.assertEqual(s.search({'source':'drugbank'})['total'], 14313)
        self.assertEqual(s.search({'q':"' OR 1=1 --"})['total'], 0)
        self.assertEqual(s.search({'q':'zzzz_not_a_molecule'})['items'], [])
        self.assertNotEqual(s.search({'page':'1'})['items'][0]['id'],s.search({'page':'2'})['items'][0]['id'])

    def test_structure_and_invalid_input(self):
        self.assertAlmostEqual(analyze('CCO')['mw'],46.069,places=2)
        for smi in ['', 'not_smiles', 'C1CC']:
            with self.assertRaises(ValueError): analyze(smi)
        self.assertIsNone(self.store.detail('drugbank:DB00001')['smiles'])

    def test_similarity_identity_and_bounds(self):
        r = self.store.detail('compound:tmy0')
        out = self.store.similar(r['smiles'], 1.0)
        self.assertTrue(any(x['id']==r['id'] and x['similarity']==1 for x in out['items']))
        for v in [-1, 2, float('nan')]:
            with self.assertRaises(ValueError):self.store.similar('CCO',v)

    def test_screen_explanations_and_history(self):
        out=self.store.screen({'mw_max':300,'logp_max':3,'hbd_max':5,'hba_max':10,'psa_max':100})
        self.assertGreater(out['total'],0)
        self.assertTrue(all(x['mw']<=300 and x['logp']<=3 for x in out['items']))
        self.assertTrue(out['items'][0]['reasons'])
        saved=self.store.save_run('测试筛选',out['params'],out['ids'])
        self.assertEqual(self.store.run(saved['id'])['ids'],out['ids'])
        self.assertEqual(self.store.run(saved['id'])['params'],out['params'])
        with self.assertRaises(ValueError):self.store.screen({'mw_max':'nan'})
        with self.assertRaises(ValueError):self.store.save_run('',{},[])

    def test_quality_provenance(self):
        q=self.store.quality()
        self.assertEqual(len(q['sources']),3)
        self.assertTrue(all(len(x['sha256'])==64 for x in q['sources']))
        self.assertEqual(sum(x['rows'] for x in q['sources']),27385)

if __name__ == '__main__':unittest.main()
