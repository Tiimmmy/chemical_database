"""Local chemical data indexing, reproducible screening, and structure analysis."""
import csv
import hashlib
import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from openpyxl import load_workbook
from rdkit import Chem, DataStructs, RDLogger, rdBase
from rdkit.Chem import Descriptors, Crippen, Lipinski, rdMolDescriptors, rdFingerprintGenerator
from rdkit.Chem.Draw import rdMolDraw2D

RDLogger.DisableLog('rdApp.*')
GENERATOR = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)
SOURCES = {'compound': 'compound_info.csv', 'bbb': 'Dataset/BBB_10648.csv', 'drugbank': 'DrugBankAll.xlsx'}
PROPERTIES = ('mw', 'logp', 'hbd', 'hba', 'psa')


def molecule(smiles):
    if not isinstance(smiles, str) or not smiles.strip() or len(smiles) > 10000:
        raise ValueError('请输入有效 SMILES，长度不超过 10000 字符')
    mol = Chem.MolFromSmiles(smiles.strip())
    if mol is None or mol.GetNumAtoms() == 0 or mol.GetNumAtoms() > 1000:
        raise ValueError('SMILES 无法解析或分子超过 1000 个原子，请检查环闭合、括号与元素符号')
    return mol


def analyze(smiles):
    mol = molecule(smiles)
    return {'canonical': Chem.MolToSmiles(mol), 'mw': round(Descriptors.MolWt(mol), 3),
            'logp': round(Crippen.MolLogP(mol), 3), 'hbd': Lipinski.NumHDonors(mol),
            'hba': Lipinski.NumHAcceptors(mol), 'psa': round(rdMolDescriptors.CalcTPSA(mol), 3)}


def structure(smiles):
    mol = molecule(smiles)
    drawer = rdMolDraw2D.MolDraw2DSVG(600, 340)
    drawer.drawOptions().padding = .12
    drawer.DrawMolecule(mol)
    drawer.FinishDrawing()
    return drawer.GetDrawingText()


def number(value, name, low, high):
    try:
        n = float(value)
    except (ValueError, TypeError):
        raise ValueError(f'{name} 必须是数值') from None
    if not math.isfinite(n) or n < low or n > high:
        raise ValueError(f'{name} 必须在 {low} 至 {high} 之间')
    return n


class Store:
    def __init__(self, root, db_path=None):
        self.root = Path(root)
        self.path = Path(db_path or self.root / 'runtime/chemical.sqlite')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._bootstrap()
        with self.connect() as db:
            rows = db.execute('SELECT id,canonical FROM records WHERE canonical IS NOT NULL').fetchall()
        # Each unique structure is fingerprinted once, but all source rows are retained.
        self.fp_cache = {}
        self.fp_rows = []
        for row in rows:
            smi = row['canonical']
            if smi not in self.fp_cache:
                self.fp_cache[smi] = GENERATOR.GetFingerprint(Chem.MolFromSmiles(smi))
            self.fp_rows.append((row['id'], self.fp_cache[smi]))

    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        return db

    def _bootstrap(self):
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS records (
              id TEXT PRIMARY KEY, source TEXT, source_row INTEGER, name TEXT,
              smiles TEXT, canonical TEXT, mw REAL, logp REAL, hbd INTEGER, hba INTEGER,
              psa REAL, label TEXT, payload TEXT, issue TEXT);
            CREATE INDEX IF NOT EXISTS source_idx ON records(source);
            CREATE INDEX IF NOT EXISTS canonical_idx ON records(canonical);
            CREATE TABLE IF NOT EXISTS sources (source TEXT PRIMARY KEY, path TEXT, sha256 TEXT,
              rows INTEGER, invalid INTEGER, missing INTEGER, duplicates INTEGER, imported TEXT);
            CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT, created TEXT, params TEXT, ids TEXT, provenance TEXT);
            ''')
            for source, relative in SOURCES.items():
                path = self.root / relative
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                old = db.execute('SELECT sha256 FROM sources WHERE source=?', (source,)).fetchone()
                if old and old['sha256'] == digest:
                    continue
                print(f'Indexing {relative}', flush=True)
                db.execute('DELETE FROM records WHERE source=?', (source,))
                seen = set()
                invalid = missing = duplicates = count = 0
                for count, row in enumerate(self._rows(path), start=1):
                    smi = row.get('SMILES') or None
                    name = row.get('ID') or row.get('DrugBank-ID') or f'BBB-{count:05d}'
                    identifier = f'{source}:{name}'
                    props = dict.fromkeys(('canonical', *PROPERTIES))
                    issue = ''
                    if smi:
                        try:
                            props = analyze(smi)
                        except ValueError:
                            invalid += 1
                            issue = '无法解析结构'
                    elif source != 'drugbank':
                        missing += 1
                        issue = '缺少结构'
                    key = props['canonical'] or name
                    if key in seen:
                        duplicates += 1
                    seen.add(key)
                    payload = {k: v for k, v in row.items() if k and k != 'Mol'}
                    label = row.get('if_active', row.get('BBB', ''))
                    values = (identifier, source, count + 1, name, smi, props['canonical'],
                              *(props[p] for p in PROPERTIES), label,
                              json.dumps(payload, ensure_ascii=False), issue)
                    db.execute('INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)', values)
                db.execute('INSERT OR REPLACE INTO sources VALUES (?,?,?,?,?,?,?,?)',
                           (source, relative, digest, count, invalid, missing, duplicates,
                            datetime.now(timezone.utc).isoformat()))

    @staticmethod
    def _rows(path):
        if path.suffix == '.csv':
            with path.open(encoding='utf-8-sig', newline='') as handle:
                yield from csv.DictReader(handle)
        else:
            book = load_workbook(path, read_only=True, data_only=True)
            rows = book.active.iter_rows(values_only=True)
            headers = next(rows)
            for values in rows:
                yield {key: '' if value is None else str(value) for key, value in zip(headers, values)}
            book.close()

    @staticmethod
    def unpack(row):
        result = dict(row)
        if 'payload' in result:
            result['payload'] = json.loads(result['payload'])
        return result

    def search(self, params):
        page = int(number(params.get('page', 1), '页码', 1, 100000))
        size = int(number(params.get('size', 12), '每页条数', 1, 100))
        conditions, args = [], []
        source = params.get('source', '')
        if source:
            if source not in SOURCES:
                raise ValueError('未知数据源')
            conditions.append('source=?')
            args.append(source)
        q = str(params.get('q', '')).strip()
        if len(q) > 1000:
            raise ValueError('搜索词不能超过 1000 字符')
        if q:
            conditions.append('(instr(lower(name),lower(?))>0 OR instr(smiles,?)>0 OR instr(lower(payload),lower(?))>0)')
            args.extend([q, q, q])
        label = params.get('label', '')
        if label:
            conditions.append('label=?')
            args.append(label)
        where = ' WHERE ' + ' AND '.join(conditions) if conditions else ''
        with self.connect() as db:
            total = db.execute('SELECT count(*) FROM records' + where, args).fetchone()[0]
            items = db.execute('SELECT id,source,name,smiles,mw,logp,hbd,hba,psa,label,issue FROM records' + where +
                               ' ORDER BY source,id LIMIT ? OFFSET ?', [*args, size, (page - 1) * size]).fetchall()
        return {'items': [dict(r) for r in items], 'total': total, 'page': page, 'size': size}

    def detail(self, identifier):
        with self.connect() as db:
            row = db.execute('SELECT * FROM records WHERE id=?', (identifier,)).fetchone()
            if row is None:
                raise ValueError('记录不存在')
            result = self.unpack(row)
            result['related'] = [dict(r) for r in db.execute(
                'SELECT id,source,name,label FROM records WHERE canonical=? AND id!=? LIMIT 20',
                (result['canonical'], identifier))] if result['canonical'] else []
            result['related_total'] = db.execute('SELECT count(*) FROM records WHERE canonical=? AND id!=?',
                (result['canonical'], identifier)).fetchone()[0] if result['canonical'] else 0
            return result

    def similar(self, smiles, threshold=.4):
        threshold = number(threshold, '相似度阈值', 0, 1)
        mol = molecule(smiles)
        fp = GENERATOR.GetFingerprint(mol)
        scores = DataStructs.BulkTanimotoSimilarity(fp, [pair[1] for pair in self.fp_rows])
        matches = sorted(((score, self.fp_rows[i][0]) for i, score in enumerate(scores) if score >= threshold),
                         key=lambda x: (-x[0], x[1]))
        items = []
        for score, identifier in matches[:60]:
            record = self.detail(identifier)
            record['similarity'] = round(score, 6)
            items.append(record)
        return {'items': items, 'total': len(matches), 'query': analyze(smiles), 'threshold': threshold,
                'algorithm': 'Morgan radius=2 / 2048 bits / Tanimoto', 'limit': 60}

    def screen(self, params):
        if not isinstance(params, dict):
            raise ValueError('筛选条件须为对象')
        defaults = {'mw_max': 500, 'logp_max': 5, 'hbd_max': 5, 'hba_max': 10, 'psa_max': 140}
        clean = {key: number(params.get(key, default), key, -20 if key == 'logp_max' else 0,
                              20 if key == 'logp_max' else 10000) for key, default in defaults.items()}
        source = params.get('source', 'compound')
        if source not in ('compound', 'bbb', 'all'):
            raise ValueError('筛选数据源必须有分子结构')
        clean['source'] = source
        conditions = ['canonical IS NOT NULL'] + [f'{p}<=?' for p in PROPERTIES]
        args = [clean[p + '_max'] for p in PROPERTIES]
        if source != 'all':
            conditions.append('source=?')
            args.append(source)
        with self.connect() as db:
            rows = db.execute('SELECT id,source,name,smiles,mw,logp,hbd,hba,psa,label FROM records WHERE ' +
                              ' AND '.join(conditions) + ' ORDER BY mw,id', args).fetchall()
        items = []
        for row in rows[:100]:
            r = dict(row)
            r['reasons'] = [f'{p.upper()} {r[p]} ≤ {clean[p + "_max"]:g}' for p in PROPERTIES]
            items.append(r)
        return {'items': items, 'ids': [r['id'] for r in rows], 'total': len(rows), 'params': clean, 'limit': 100}

    def quality(self):
        with self.connect() as db:
            sources = [dict(r) for r in db.execute('SELECT * FROM sources ORDER BY source')]
            labels = [dict(r) for r in db.execute('SELECT source,label,count(*) AS count FROM records GROUP BY source,label')]
            metrics = dict(db.execute('SELECT count(canonical) AS structures,count(DISTINCT canonical) AS unique_structures FROM records').fetchone())
            drug_missing = [dict(r) for r in db.execute("SELECT json_extract(payload,'$.State') AS state,count(*) AS count FROM records WHERE source='drugbank' GROUP BY state")]
        return {'sources': sources, 'labels': labels, **metrics, 'drug_states': drug_missing,
                'rdkit': rdBase.rdkitVersion,
                'quality_note': '重复按各源内规范化 SMILES（无结构时按 ID）统计，保留全部来源行；DrugBank 设计上无 SMILES。'}

    def save_run(self, name, params, ids):
        name = str(name).strip()
        if not name or len(name) > 100:
            raise ValueError('记录名称须为 1 至 100 字符')
        # Recompute on the server: clients cannot forge an archived result list.
        result = self.screen(params)
        if ids != result['ids']:
            raise ValueError('结果与条件不一致，请重新执行筛选')
        provenance = {'sources': self.quality()['sources'], 'rdkit': rdBase.rdkitVersion,
                      'algorithm': 'RDKit properties; inclusive upper bounds',
                      'snapshot': result['items'], 'snapshot_limit': 100}
        with self.connect() as db:
            cur = db.execute('INSERT INTO runs(name,created,params,ids,provenance) VALUES (?,?,?,?,?)',
                             (name, datetime.now(timezone.utc).isoformat(), json.dumps(result['params']),
                              json.dumps(ids), json.dumps(provenance, ensure_ascii=False)))
            return {'id': cur.lastrowid}

    def runs(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT id,name,created,json_array_length(ids) AS count FROM runs ORDER BY id DESC')]

    def run(self, identifier):
        with self.connect() as db:
            row = db.execute('SELECT * FROM runs WHERE id=?', (identifier,)).fetchone()
        if row is None:
            raise ValueError('筛选记录不存在')
        result = dict(row)
        for field in ('params', 'ids', 'provenance'):
            result[field] = json.loads(result[field])
        return result
