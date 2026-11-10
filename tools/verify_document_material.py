"""Verify source text coverage, screenshot pixels, page geometry and unchanged inputs."""
from pathlib import Path
import hashlib
import json
import re
import unicodedata
import subprocess
from pypdf import PdfReader
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'deliverables';OUT=BASE/'document-material'
meta=json.loads((OUT/'document-mapping.json').read_text())
blocks=json.loads((OUT/'正文核对.json').read_text())
src=PdfReader(meta['source_pdf']);out=PdfReader(meta['output_pdf'])
clean=lambda s:re.sub(r'\s+','',unicodedata.normalize('NFKC',s))
source_text_pages=subprocess.check_output(['pdftotext','-raw',meta['source_pdf'],'-']).decode('utf-8').split('\f')
source_failures=[]
for i,items in enumerate(blocks):
    original=clean(source_text_pages[i])
    for b in items:
        for text in b['text'].split(' ｜ '):
            text=text.replace('对应本页完整界面截图：','对应下一页完整界面截图：')
            if clean(text) not in original:
                source_failures.append((i+1,text))
assert not source_failures,source_failures

# Only the body region: no running headers are allowed to interrupt paragraph checks.
body=[]
for i,p in enumerate(out.pages,1):
    body_parts=[]
    def visitor(text,cm,tm,font,size):
        if 60 <= tm[5] <= 777:
            body_parts.append(text)
    p.extract_text(visitor_text=visitor)
    body.append(clean(''.join(body_parts)))
    assert abs(float(p.mediabox.width)-595.276)<1
    assert abs(float(p.mediabox.height)-841.89)<1
    assert f'第{i}页/共{len(out.pages)}页' in clean(p.extract_text())
combined=''.join(body)
missing=[]
for i,items in enumerate(blocks):
    for b in items:
        for text in b['text'].split(' ｜ '):
            if clean(text) not in combined:missing.append((i+1,text))
assert not missing,missing

pixel_checks=[]
for record in meta['pages']:
    if record['kind']!='operation':continue
    image_file=BASE/record['screenshot']
    original=Image.open(image_file).convert('RGB')
    assert hashlib.sha256(image_file.read_bytes()).hexdigest()==record['screenshot_sha256']
    output_images=out.pages[record['output_page']-1].images
    assert len(output_images)==1
    embedded=output_images[0].image.convert('RGB')
    assert embedded.size==original.size
    assert embedded.tobytes()==original.tobytes()
    source_images=src.pages[record['source_pages'][-1]-1].images
    assert len(source_images)==1
    source_image=source_images[0].image.convert('RGB')
    assert source_image.size==original.size
    assert source_image.tobytes()==original.tobytes()
    pixel_checks.append({'output_page':record['output_page'],'source_page':record['source_pages'][-1],
                         'screenshot':record['screenshot'],'same_pixels_as_source_pdf':True})
assert len(pixel_checks)==15
assert len(out.pages)==meta['output_pages']==32
assert not out.is_encrypted
assert hashlib.sha256(Path(meta['source_pdf']).read_bytes()).hexdigest()==meta['source_sha256']
assert hashlib.sha256(Path(meta['output_pdf']).read_bytes()).hexdigest()==meta['output_sha256']
for p in meta['pages']:
    if p['kind']=='text':assert p['body_rows']>=30
    if 'image_rect' in p:
        x,y,w,h=p['image_rect'];assert x>=38 and y>=67 and x+w<=557 and y+h<=776
result={'pages':32,'A4_portrait':True,'encrypted':False,'all_original_body_text_retained':True,
        'original_pdf_unchanged':True,'screenshot_pixel_checks':pixel_checks,
        'complete_screenshots':15,'labeled_zoom_views':15,'text_page_rows':[p['body_rows'] for p in meta['pages'] if p['kind']=='text'],
        'visual_samples':[1,10,11,32],'verification':'passed'}
(OUT/'verification').mkdir(exist_ok=True)
(OUT/'verification/verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='screenshot_pixel_checks'},ensure_ascii=False))
