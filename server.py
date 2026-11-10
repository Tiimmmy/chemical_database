"""Loopback-only web application. Start with python server.py."""
import argparse
import csv
import io
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from chemdb import Store, structure

ROOT = Path(__file__).resolve().parent


def safe_cell(value):
    if isinstance(value, (int, float)):
        return value
    s = '' if value is None else str(value)
    return "'" + s if s.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else s


class Handler(BaseHTTPRequestHandler):
    def send(self, body, content_type='application/json; charset=utf-8', status=200, filename=None):
        if not isinstance(body, (str, bytes)):
            body = json.dumps(body, ensure_ascii=False, allow_nan=False)
        if isinstance(body, str):
            body = body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store')
        if filename:
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        try:
            self.route_get()
        except (ValueError, TypeError, KeyError) as e:
            self.send({'error': str(e)}, status=400)
        except Exception as e:
            self.log_error('%s', e)
            self.send({'error': '服务处理失败，请查看运行终端'}, status=500)

    def route_get(self):
        url = urlsplit(self.path)
        p = {k: v[0] for k, v in parse_qs(url.query).items()}
        store = self.server.store
        path = url.path
        if path == '/api/overview' or path == '/api/quality':
            self.send(store.quality())
        elif path == '/api/search':
            self.send(store.search(p))
        elif path == '/api/detail':
            self.send(store.detail(p['id']))
        elif path == '/api/structure':
            self.send(structure(store.detail(p['id'])['smiles']), 'image/svg+xml')
        elif path == '/api/similar':
            self.send(store.similar(p.get('smiles'), p.get('threshold', .4)))
        elif path == '/api/screen':
            self.send(store.screen(p))
        elif path == '/api/runs':
            self.send(store.runs())
        elif path == '/api/run':
            self.send(store.run(int(p['id'])))
        elif path == '/api/export':
            self.export(p)
        else:
            relative = 'index.html' if path == '/' else path.lstrip('/')
            file = (ROOT / 'web' / relative).resolve()
            if not file.is_relative_to(ROOT / 'web') or not file.is_file():
                self.send({'error': '页面不存在'}, status=404)
                return
            mime = mimetypes.guess_type(file.name)[0] or 'application/octet-stream'
            self.send(file.read_bytes(), mime + ('; charset=utf-8' if mime.startswith('text/') else ''))

    def export(self, p):
        store = self.server.store
        if p.get('kind') == 'run':
            data = store.run(int(p['id']))
            self.send(data, filename=f'screening-{data["id"]}.json')
            return
        if p.get('kind') == 'screen':
            result = store.screen(p)
            ids = result['ids']
        else:
            p = dict(p, size=100, page=1)
            first = store.search(p)
            ids = [r['id'] for r in first['items']]
            for page in range(2, (first['total'] + 99) // 100 + 1):
                ids.extend(r['id'] for r in store.search(dict(p, page=page))['items'])
        output = io.StringIO()
        fields = ['id', 'source', 'source_row', 'name', 'smiles', 'canonical', 'mw', 'logp', 'hbd', 'hba', 'psa', 'label']
        writer = csv.writer(output)
        writer.writerow(fields)
        with store.connect() as db:
            for identifier in ids:
                row = db.execute('SELECT * FROM records WHERE id=?', (identifier,)).fetchone()
                writer.writerow(safe_cell(row[k]) for k in fields)
        self.send('\ufeff' + output.getvalue(), 'text/csv; charset=utf-8', filename='chemical-results.csv')

    def do_POST(self):
        try:
            host = self.headers.get('Host', '')
            origin = self.headers.get('Origin')
            if origin and origin != 'http://' + host:
                raise ValueError('不接受跨站写入')
            if urlsplit(self.path).path != '/api/runs':
                self.send({'error': '接口不存在'}, status=404)
                return
            length = int(self.headers.get('Content-Length', 0))
            if not 0 < length <= 2000000:
                raise ValueError('请求体为空或过大')
            if not self.headers.get('Content-Type', '').startswith('application/json'):
                raise ValueError('请求格式须为 JSON')
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError('请求体须为 JSON 对象')
            self.send(self.server.store.save_run(body['name'], body['params'], body['ids']), status=201)
        except (ValueError, TypeError, KeyError) as e:
            self.send({'error': str(e)}, status=400)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    store = Store(ROOT)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    server.store = store
    print(f'化合物数据与可解释筛选系统 V1.0 — http://127.0.0.1:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

if __name__ == '__main__':
    main()
