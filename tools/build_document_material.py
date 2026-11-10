#!/usr/bin/python3
"""Re-typeset the existing complete manual into a traceable A4 portrait deposit PDF."""
import hashlib
import json
import math
from html.parser import HTMLParser
from pathlib import Path

from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from build_program_material import init_fonts, draw_text, width

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'deliverables'
OUT=BASE/'document-material'
NAME='化合物数据与可解释筛选系统'
VERSION='V1.0'
SOURCE=BASE/(NAME+VERSION+'_软件操作说明书.pdf')
PDF=BASE/(NAME+VERSION+'_文档鉴别材料.pdf')
LEFT,RIGHT,TOP,BOTTOM=39,556,775,68
BODY_SIZE=10.5


class Node:
    def __init__(self,tag='',attrs=None):
        self.tag=tag;self.attrs=dict(attrs or []);self.children=[]
    def text(self):
        return ''.join(c if isinstance(c,str) else c.text() for c in self.children)
    def find(self,tag):
        for c in self.children:
            if isinstance(c,Node):
                if c.tag==tag:yield c
                yield from c.find(tag)


class Parser(HTMLParser):
    def __init__(self):
        super().__init__();self.root=Node();self.stack=[self.root]
    def handle_starttag(self,tag,attrs):
        n=Node(tag,attrs);self.stack[-1].children.append(n)
        if tag not in ('meta','link','img','br','hr','input'):self.stack.append(n)
        if tag=='br':self.stack[-1].children.append('\n')
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==tag:
                self.stack=self.stack[:i];break
    def handle_data(self,data):self.stack[-1].children.append(data)


def norm(text):return ' '.join(text.split())


def blocks(node,page):
    result=[]
    for c in node.children:
        if isinstance(c,str):continue
        if c.attrs.get('class') in ('page-top','page-bottom'):continue
        if c.tag in ('h1','h2','p','li','pre'):
            text=norm(c.text())
            if text:result.append({'text':text,'kind':c.tag,'source_page':page})
        elif c.tag=='table':
            for row in c.find('tr'):
                cells=[norm(x.text()) for x in row.children if isinstance(x,Node) and x.tag in ('th','td')]
                result.append({'text':' ｜ '.join(cells),'kind':'table','source_page':page})
        else:result.extend(blocks(c,page))
    return result


def wrap(text,size=BODY_SIZE):
    lines=[];current='';used=0
    for char in text:
        w=width(char,size)
        if current and used+w>RIGHT-LEFT:
            lines.append(current);current='';used=0
        current+=char;used+=w
    if current:lines.append(current)
    return lines


def rows_for(items):
    rows=[]
    for item in items:
        for text in wrap(item['text']):
            rows.append(dict(item,text=text))
    return rows


def balance(rows):
    count=max(1,math.ceil(len(rows)/45))
    if count>1 and len(rows)//count<30:count-=1
    base,extra=divmod(len(rows),count);result=[];start=0
    for i in range(count):
        size=base+(i<extra);result.append(rows[start:start+size]);start+=size
    return result


def digest(file):return hashlib.sha256(file.read_bytes()).hexdigest()


def prepare():
    parser=Parser();parser.feed((BASE/'manual.html').read_text())
    sections=list(parser.root.find('section'))
    assert len(sections)==38,'Source manual structure changed; check the input PDF first.'
    manifest=json.loads((BASE/'screenshot-manifest.json').read_text())
    assert len(manifest['screenshots'])==15
    source_blocks=[blocks(n,i+1) for i,n in enumerate(sections)]
    pages=[]
    intro=sum(source_blocks[:4],[])
    for rows in balance(rows_for(intro)):
        pages.append({'kind':'text','rows':rows,'source_pages':sorted({r['source_page'] for r in rows})})
    for i,shot in enumerate(manifest['screenshots']):
        path=BASE/shot['file'];assert digest(path)==shot['sha256']
        items=source_blocks[4+2*i]+source_blocks[5+2*i]
        # The image moves onto the same operation page; update only this cross-reference.
        for item in items:
            item['text']=item['text'].replace('对应下一页完整界面截图：','对应本页完整界面截图：')
        rows=rows_for(items)
        image_size=Image.open(path).size
        pages.append({'kind':'operation','rows':rows,'shot':shot,'source_pages':[5+2*i,6+2*i],'image_size':image_size})
        # A clipped PDF view of the same source PNG, explicitly additional to the full image.
        # No output bitmap is modified and the complete original remains on the preceding page.
        x,y=432,132
        crop=(x,y,min(1700,image_size[0]-x),min(2000,image_size[1]-y))
        pages.append({'kind':'zoom','shot':shot,'source_pages':[6+2*i],'image_size':image_size,'crop':crop})
    tail=sum(source_blocks[34:],[])
    for rows in balance(rows_for(tail)):
        pages.append({'kind':'text','rows':rows,'source_pages':sorted({r['source_page'] for r in rows})})
    return sections,source_blocks,manifest,pages


def build():
    OUT.mkdir(exist_ok=True);init_fonts()
    source_hash=digest(SOURCE)
    sections,source_blocks,manifest,pages=prepare()
    assert len(pages)<60
    pdf=canvas.Canvas(str(PDF),pagesize=A4,pageCompression=1)
    pdf.setTitle(NAME+' '+VERSION+' 文档鉴别材料（软件操作说明书）')
    pdf.setAuthor('')
    pdf.setSubject('基于既有38页操作说明书完整整理，保留全部15张真实界面截图及正文，A4纵向')
    pdf.setCreator('Existing manual document material generator / ReportLab')
    source_map=[]
    for index,p in enumerate(pages,1):
        draw_text(pdf,LEFT,812,NAME+' '+VERSION,10)
        label=f'第 {index} 页 / 共 {len(pages)} 页'
        draw_text(pdf,RIGHT-width(label,9),812,label,9)
        pdf.line(LEFT,800,RIGHT,800)
        source_label='原说明书第 '+ '、'.join(map(str,p['source_pages']))+' 页'
        draw_text(pdf,LEFT,787,'文档鉴别材料 · 软件操作说明书',8)
        draw_text(pdf,RIGHT-width(source_label,7.5),787,source_label,7.5)
        y=TOP-13
        if p['kind'] in ('text','operation'):
            size=BODY_SIZE if p['kind']=='text' else 9.4
            # Rewrap at the final body size, preserving all content and evidence strings.
            rows=p['rows']
            leading=min(16.5,(TOP-BOTTOM-20)/max(1,len(rows)-1)) if p['kind']=='text' else 12.5
            for row in rows:
                draw_text(pdf,LEFT,y,row['text'],size)
                y-=leading
            if p['kind']=='text':
                assert len(rows)>=30 or index==len(pages)
                assert y>BOTTOM-20
            else:
                image_file=BASE/p['shot']['file']
                iw,ih=p['image_size']
                available=y-BOTTOM-8
                assert available>250,(index,available,len(rows))
                scale=min((RIGHT-LEFT)/iw,available/ih)
                dw,dh=iw*scale,ih*scale
                xx=LEFT+(RIGHT-LEFT-dw)/2;yy=y-8-dh
                pdf.drawImage(str(image_file),xx,yy,dw,dh)
                p['image_rect']=[xx,yy,dw,dh]
        else:
            draw_text(pdf,LEFT,y,'局部放大 · '+p['shot']['title'],12);y-=23
            for text in wrap('本页为前页完整截图中工作区的局部放大，便于阅读。全部界面及其上下文见前页完整截图。',10):
                draw_text(pdf,LEFT,y,text,10);y-=16
            draw_text(pdf,LEFT,y,'放大范围：原图左上角坐标及宽高 '+str(p['crop'])+' 像素。',8);y-=20
            iw,ih=p['image_size'];cx,cy,cw,ch=p['crop']
            scale=min((RIGHT-LEFT)/cw,(y-BOTTOM)/ch)
            dw,dh=cw*scale,ch*scale
            xx=LEFT+(RIGHT-LEFT-dw)/2;yy=y-dh
            pdf.saveState()
            clip=pdf.beginPath();clip.rect(xx,yy,dw,dh);pdf.clipPath(clip,stroke=0)
            pdf.drawImage(str(BASE/p['shot']['file']),xx-cx*scale,yy-(ih-cy-ch)*scale,iw*scale,ih*scale)
            pdf.restoreState()
            p['image_rect']=[xx,yy,dw,dh]
        pdf.line(LEFT,48,RIGHT,48)
        draw_text(pdf,LEFT,34,'完整文档交存 · 操作步骤、结果说明及原始界面证据',8)
        pdf.showPage()
        source_map.append({'output_page':index,'kind':p['kind'],'source_pages':p['source_pages'],
                           'body_rows':len(p.get('rows',[])),
                           **({'screenshot':p['shot']['file'],'screenshot_sha256':p['shot']['sha256']} if 'shot' in p else {}),
                           **({'crop':p['crop']} if 'crop' in p else {}),
                           **({'image_rect':p['image_rect']} if 'image_rect' in p else {})})
    pdf.save()
    assert digest(SOURCE)==source_hash
    result={'source_pdf':str(SOURCE),'source_sha256':source_hash,'source_pages':38,
            'source_html_sha256':digest(BASE/'manual.html'),'output_pdf':str(PDF),'output_sha256':digest(PDF),
            'output_pages':len(pages),'full_screenshots':15,'additional_zoom_views':15,'pages':source_map,
            'content_edits':['仅将操作页“对应下一页完整界面截图”改为“对应本页完整界面截图”，适配图文合页；正文与原图完整保留。'],
            'rule_sources':['https://www.ncac.gov.cn/xxfb/flfg/bmgz/202410/t20241015_869486.html',
             'https://banshi.beijing.gov.cn/pubtask/task/1/110000000000/3e283672-76be-4c8c-98e8-0bebe9bd06bf_app.html']}
    (OUT/'document-mapping.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    (OUT/'正文核对.json').write_text(json.dumps(source_blocks,ensure_ascii=False,indent=2))
    note=f'''文档鉴别材料编制说明（供核对，不并入提交PDF）
软件名称：{NAME}
版本：{VERSION}
来源：{SOURCE.name}，38页。
来源PDF SHA256：{source_hash}
产物：{PDF.name}，{len(pages)}页，A4纵向，可检索文字，无加密。

编制范围：完整保留原说明书正文、表格内容、15张完整真实截图、操作步骤、结果说明、技术特点、源码统计、申请表核对与维护内容。表格转为按行连续排列的文本。将原操作文字页与相邻截图页合并，增加15个明确标注的局部放大页，帮助阅读。所有截图复用原PNG，不重绘或替换界面；局部放大通过PDF裁切视窗实现，完整图仍在相邻前页。
文本版面：正文连续重排，纯文字页至少30行；图文页保留实际操作文字及图像，不用重复内容补足行数。页眉含软件名称、版本和右上角连续页码。当前不足60页，完整提供，不截取前后片段。
原件：原操作说明书PDF及原图不改动。document-mapping.json记录新旧页对应、原图校验值、局部视窗范围及产物校验值。
唯一正文位置说明调整：“对应下一页完整界面截图”改为“对应本页完整界面截图”，与新编排对应。

名称、版本、申请人等请按最终申请表核对；本次未编造或补写权利人信息。原文关于源码行数的统计仍为运行程序579物理行/542非空行。验证工具统计为原说明书编制时的范围，后续新增材料生成工具不属于运行程序。
格式参考：国家版权局《计算机软件著作权登记办法》第十条；北京市政务服务“计算机软件著作权登记初审”。来源链接见document-mapping.json。
复现：/usr/bin/python3 tools/build_document_material.py
'''
    (OUT/'编制说明与原文对应.txt').write_text(note)
    print(json.dumps({'pdf':str(PDF),'pages':len(pages),'full_screenshots':15,'zoom_views':15,
                      'text_page_rows':[p['body_rows'] for p in source_map if p['kind']=='text']},ensure_ascii=False))

if __name__=='__main__':build()
