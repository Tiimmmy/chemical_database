#!/usr/bin/python3
"""Produce complete, traceable source-code deposit material without changing source files.
Uses the system Python's ReportLab; does not require a browser or a local server.
"""
import hashlib
import html
import json
import math
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'deliverables' / 'program-material'
NAME = '化合物数据与可解释筛选系统'
VERSION = 'V1.0'
FILES = ['run.sh', 'server.py', 'chemdb.py', 'web/index.html', 'web/style.css', 'web/app.js']
STEM = NAME + VERSION + '_程序鉴别材料'
FONT_SIZE = 8.2
CODE_X, RIGHT = 88, 565
WIDTH = RIGHT - CODE_X


def init_fonts():
    paths = [('Mono', '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'),
             ('CJK', '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf'),
             ('Sans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
    for name, path in paths:
        pdfmetrics.registerFont(TTFont(name, path))


def font_for(char):
    for name in ('Mono', 'CJK', 'Sans'):
        if ord(char) in pdfmetrics.getFont(name).face.charWidths:
            return name
    raise ValueError(f'No embedded font supports {char!r}')


def width(text, size=FONT_SIZE):
    return sum(pdfmetrics.stringWidth(char, font_for(char), size) for char in text)


def draw_text(pdf, x, y, text, size=FONT_SIZE):
    current, run = None, ''
    for char in text + '\0':
        font = font_for(char) if char != '\0' else None
        if font != current and run:
            pdf.setFont(current, size)
            pdf.drawString(x, y, run)
            x += pdfmetrics.stringWidth(run, current, size)
            run = ''
        run += char
        current = font


def wrap_exact(line):
    """Only split presentation rows; joining fragments reproduces the original line."""
    result, chunk, used = [], '', 0
    for char in line:
        char_width = width(char)
        if chunk and used + char_width > WIDTH:
            result.append(chunk)
            chunk, used = '', 0
        chunk += char
        used += char_width
    if chunk:
        result.append(chunk)
    assert ''.join(result) == line
    return result


def make_rows():
    files, rows = [], []
    for index, relative in enumerate(FILES, 1):
        path = ROOT / relative
        raw = path.read_bytes()
        lines = raw.decode('utf-8').splitlines()
        label = f'S{index}'
        files.append({'code':label, 'path':relative, 'physical_lines':len(lines),
                      'nonblank_lines':sum(bool(s.strip()) for s in lines),
                      'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest()})
        for lineno, line in enumerate(lines, 1):
            if not line.strip():
                continue
            if '\t' in line:
                raise ValueError(f'{relative}:{lineno}: tabs require an explicit display mapping')
            for part, fragment in enumerate(wrap_exact(line), 1):
                rows.append({'file':relative, 'file_code':label, 'line':lineno,
                             'part':part, 'text':fragment})
    rebuilt = defaultdict(list)
    for row in rows:
        rebuilt[(row['file'], row['line'])].append(row['text'])
    for relative in FILES:
        for line, text in enumerate((ROOT / relative).read_text().splitlines(), 1):
            if text.strip():
                assert ''.join(rebuilt[(relative,line)]) == text
    return files, rows


def paginate(rows):
    # Balanced pages: all pages have at least 50 visible, nonempty source rows.
    # No filler, duplicated source, blank padding, or truncation.
    count = max(1, len(rows) // 50)
    per_page, extra = divmod(len(rows), count)
    pages, start = [], 0
    for i in range(count):
        size = per_page + (i < extra)
        pages.append(rows[start:start+size])
        start += size
    assert start == len(rows)
    return pages


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    init_fonts()
    files, rows = make_rows()
    pages = paginate(rows)
    pdf_path = OUT / (STEM + '.pdf')
    pdf = canvas.Canvas(str(pdf_path), pagesize=A4, pageCompression=1)
    pdf.setTitle(NAME + ' ' + VERSION + ' 程序鉴别材料')
    pdf.setSubject('实际运行源程序完整交存；全部源文件；A4纵向；原文件行号与折行映射')
    pdf.setCreator('Project source material generator / ReportLab')
    html_pages, total_number = [], 0
    for page_number, page_rows in enumerate(pages, 1):
        pdf.setFillColorRGB(0,0,0)
        draw_text(pdf, 31, 812, NAME + ' ' + VERSION, 10.5)
        page_label = f'第 {page_number} 页 / 共 {len(pages)} 页'
        draw_text(pdf, RIGHT - width(page_label,9), 812, page_label, 9)
        pdf.setLineWidth(.5)
        pdf.line(31, 801, RIGHT, 801)
        identifiers = list(dict.fromkeys((r['file_code'],r['file']) for r in page_rows))
        scope = '本页文件：' + '；'.join(k+' '+v for k,v in identifiers)
        draw_text(pdf, 31, 786, scope, 7.5)
        leading = min(13.5, 680 / max(1,len(page_rows)-1))
        y = 766
        html_rows = []
        for local_number, row in enumerate(page_rows, 1):
            total_number += 1
            row['material_row'] = total_number
            row['page'] = page_number
            row['page_row'] = local_number
            prefix = f'{row["file_code"]}:{row["line"]:04d}' + ('+' if row['part']>1 else ' ')
            draw_text(pdf, 31, y, f'{local_number:02d}', 7.2)
            draw_text(pdf, 47, y, prefix, 6.7)
            draw_text(pdf, CODE_X, y, row['text'])
            assert width(row['text']) <= WIDTH + .01
            assert y >= 80
            html_rows.append(f'<div class="row"><span>{local_number:02d}</span><span>{prefix}</span><code>{html.escape(row["text"])}</code></div>')
            y -= leading
        pdf.line(31, 55, RIGHT, 55)
        draw_text(pdf, 31, 42, '左栏为页内行号及原文件行号；“+”表示同一源码行的续排。源文件全部纳入，空白行不显示。', 7.2)
        draw_text(pdf, 31, 30, f'本页 {len(page_rows)} 排版行；源码量按原文件统计，折行不增加源程序量。', 7.2)
        pdf.showPage()
        html_pages.append(f'<section><header><b>{NAME} {VERSION}</b><span>{page_label}</span></header><p>{scope}</p>'+''.join(html_rows)+'<footer>原文件行号后的 + 为续排；完整源码，空白行不显示。</footer></section>')
    pdf.save()
    manifest = {'software_name':NAME,'version':VERSION,'created_at':datetime.now(timezone.utc).isoformat(),
                'selection':'完整交存当前工作台的全部6个运行程序文件；未选入数据、第三方依赖、测试、材料生成工具和既有独立离线脚本。',
                'physical_source_lines':sum(f['physical_lines'] for f in files),
                'nonblank_source_lines':sum(f['nonblank_lines'] for f in files),
                'typeset_rows':len(rows),'pages':len(pages),'page_rows':[len(p) for p in pages],
                'files':files,'rows':rows,'pdf_sha256':hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
                'rule_sources':['https://www.ncac.gov.cn/xxfb/flfg/bmgz/202410/P020241015604759788122.pdf',
                                'https://banshi.beijing.gov.cn/pubtask/task/1/110000000000/3e283672-76be-4c8c-98e8-0bebe9bd06bf.html']}
    (OUT/'source-mapping.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    style='''@page{size:A4;margin:0}body{background:#ddd;margin:0}section{background:white;box-sizing:border-box;width:210mm;height:297mm;padding:10mm 11mm;break-after:page;margin:0 auto 4mm}header{display:flex;justify-content:space-between;border-bottom:1px solid black;font:10pt sans-serif;padding-bottom:3mm}p{font:8pt sans-serif;margin:3mm 0}.row{display:grid;grid-template-columns:6mm 15mm 1fr;line-height:13.5pt;font:7pt/13.5pt monospace}.row code{white-space:pre;font:8.2pt/13.5pt "DejaVu Sans Mono","Droid Sans Fallback",monospace}footer{font:7pt sans-serif;border-top:1px solid black;margin-top:3mm;padding-top:2mm}@media print{body{background:white}section{margin:0}}'''
    (OUT/(STEM+'.html')).write_text('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>'+STEM+'</title><style>'+style+'</style></head><body>'+''.join(html_pages)+'</body></html>')
    with zipfile.ZipFile(OUT/'运行源程序原件.zip','w',zipfile.ZIP_DEFLATED) as z:
        for relative in FILES:
            z.write(ROOT/relative,relative)
    description=f'''程序鉴别材料编制说明（此文件不并入源程序PDF）
软件名称：{NAME}
版本号：{VERSION}

交付文件：{pdf_path.name}
版式：A4纵向、黑白文字、嵌入字体、可检索文本；{len(pages)}页，每页{min(map(len,pages))}至{max(map(len,pages))}个非空排版行。
范围：当前工作台全部6个运行源码文件；不足60页，未截取前后片段，未拼凑或补写代码。
实际程序量：{manifest['physical_source_lines']}物理行（含空白），{manifest['nonblank_source_lines']}非空行。
排版行数：{len(rows)}。长行因页面宽度连续折行，空白行不占版面；排版行数不是源程序量。
页内标识：S1至S6对应下列文件，后接原文件行号；“+”是同一物理行的续排。
末页结束于web/app.js的render();，是完整前端模块末尾。

文件清单：
'''+''.join(f'{f["code"]} {f["path"]} | 物理行 {f["physical_lines"]} | 非空行 {f["nonblank_lines"]} | SHA256 {f["sha256"]}\n' for f in files)+'''
原件与可追溯性：
运行源程序原件.zip 保存上述文件字节原件，包含原始空白行。
source-mapping.json 包含逐排版行与原文件行号的映射及文件、PDF校验值。
排版器已逐原文件非空行重组折行文本，确认与源码完全一致，未修改程序本体。
HTML提供可编辑副本；提交以已核验的PDF为准，编辑后需重新排版检查。

范围对应：
与现有操作说明书“运行程序”类别一致。不包括README、配置、数据文件、SQLite、第三方库、测试和材料生成器；旧数据采集及片段脚本不是本工作台入口，单独保留在原项目，不混入本次运行程序量。
申请表若覆盖这些旧脚本或另外的软件范围，需要重新界定范围并生成材料。

提交核对：
软件名称、版本及源程序量口径需与最终申请表完全一致。用户尚未提供申请表和权利人资料，本材料未编造权利人信息。当前579物理行可与操作说明书的同口径统计核对；后续源码变更后需重新生成。
本次不对代码权属或第三方数据许可作代为认定。

格式依据：
国家版权局《计算机软件著作权登记办法》第十条：不足60页提交全部源程序，通常每页不少于50行。
https://www.ncac.gov.cn/xxfb/flfg/bmgz/202410/P020241015604759788122.pdf
北京市政务服务“计算机软件著作权登记初审”：A4纵向，软件名称和版本页眉、右上角页码，最后一页为程序结束页。
https://banshi.beijing.gov.cn/pubtask/task/1/110000000000/3e283672-76be-4c8c-98e8-0bebe9bd06bf.html

复现命令：
/usr/bin/python3 tools/build_program_material.py
'''
    (OUT/'编制说明与申请表核对.txt').write_text(description)
    print(json.dumps({'pdf':str(pdf_path),'pages':len(pages),'page_rows':manifest['page_rows'],
                      'physical_source_lines':manifest['physical_source_lines'],'typeset_rows':len(rows)},ensure_ascii=False))

if __name__ == '__main__':
    build()
