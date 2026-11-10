"""HTTP-handler tests execute through in-memory streams, without opening ports."""
import io
import json
import unittest
from email.message import Message
from types import SimpleNamespace
from pathlib import Path
from chemdb import Store
from server import Handler, safe_cell

class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store=Store(Path(__file__).resolve().parents[1])

    def request(self, path, body=None, origin=None):
        h=Handler.__new__(Handler)
        h.path=path
        h.server=SimpleNamespace(store=self.store)
        h.wfile=io.BytesIO()
        h.rfile=io.BytesIO(json.dumps(body).encode() if body is not None else b'')
        h.headers=Message()
        h.headers['Host']='127.0.0.1:8765'
        h.headers['Content-Type']='application/json'
        h.headers['Content-Length']=str(len(h.rfile.getvalue()))
        if origin:h.headers['Origin']=origin
        result={}
        h.send_response=lambda status:result.update(status=status)
        h.send_header=lambda key,val:result.update({key:val})
        h.end_headers=lambda:None
        h.log_error=lambda *args:None
        if body is None:h.do_GET()
        else:h.do_POST()
        result['body']=h.wfile.getvalue()
        return result

    def test_json_routes_and_static(self):
        for path in ['/api/overview','/api/quality','/api/search?source=compound&q=tmy0','/api/detail?id=drugbank:DB00001','/api/runs','/','/app.js','/style.css']:
            with self.subTest(path=path):self.assertEqual(self.request(path)['status'],200)

    def test_errors(self):
        for path in ['/api/detail?id=absent','/api/search?page=nan','/api/screen?mw_max=nan','/api/similar?smiles=invalid','/api/search?source=unknown']:
            with self.subTest(path=path):self.assertEqual(self.request(path)['status'],400)
        self.assertEqual(self.request('/../../chemdb.py')['status'],404)
        self.assertEqual(self.request('/api/runs',{},'https://outside.example')['status'],400)

    def test_csv_real_results(self):
        result=self.request('/api/export?source=compound&q=tmy0')
        self.assertEqual(result['status'],200)
        self.assertIn('compound:tmy0',result['body'].decode('utf-8-sig'))
        self.assertEqual(safe_cell('=SUM(A1)'),"'=SUM(A1)")
        self.assertEqual(safe_cell(-0.472),-0.472)

    def test_malformed_write_body(self):
        for body in [[], {'name':'x','params':None,'ids':[]}, {'name':'x','params':[],'ids':[]}]:
            with self.subTest(body=body):self.assertEqual(self.request('/api/runs',body)['status'],400)

    def test_structure_svg(self):
        result=self.request('/api/structure?id=compound:tmy0')
        self.assertEqual(result['status'],200)
        self.assertIn(b'<svg',result['body'])

if __name__=='__main__':unittest.main()
