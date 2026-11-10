"""Operate the real running application; capture screenshots and validate interactions."""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'deliverables'


def capture(base_url='http://127.0.0.1:8765'):
    OUT.mkdir(exist_ok=True)
    (OUT / 'screenshots').mkdir(exist_ok=True)
    manifest, errors, checks = [], [], []
    evidence_files = ['chemdb.py','server.py','web/index.html','web/app.js','web/style.css','run.sh',
                      'compound_info.csv','Dataset/BBB_10648.csv','DrugBankAll.xlsx']
    source_hashes = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in evidence_files}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel='chrome')
        context = browser.new_context(viewport={'width':1280,'height':850}, device_scale_factor=2,
                                      locale='zh-CN', accept_downloads=True)
        page = context.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.set_default_timeout(30000)

        def visit(hash_path):
            page.goto(base_url + '/#' + hash_path)
            page.locator('.busy').wait_for(state='hidden')
            expect(page.locator('h1')).to_be_visible()

        def snap(slug, title, steps, result):
            page.evaluate('document.fonts.ready')
            page.wait_for_function("Array.from(document.images).every(i=>i.complete)")
            broken = page.locator('img').evaluate_all('(imgs)=>imgs.filter(i=>!i.naturalWidth).length')
            if broken:
                raise AssertionError(f'{slug}: {broken} broken images')
            page.locator('#toast').evaluate("e=>e.style.display='none'")
            file = OUT / 'screenshots' / (slug + '.png')
            page.screenshot(path=str(file), full_page=True, animations='disabled')
            from PIL import Image
            with Image.open(file) as img: width, height = img.size
            manifest.append({'file':str(file.relative_to(OUT)), 'title':title, 'steps':steps,
                             'result':result,'url':page.url,'width':width,'height':height,
                             'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
                             'captured_at':datetime.now(timezone.utc).isoformat()})
            print('Captured',slug,flush=True)

        visit('overview')
        expect(page.locator('.metric').first).to_contain_text('27,385')
        snap('01-overview','数据总览与研究入口',[
            '启动服务后，在浏览器打开本地地址。左侧导航进入数据总览。',
            '核对全部来源记录、可解析结构、唯一结构及 BBB 标签数量。',
            '通过数据资产分布确认三个文件；点击开始检索或进入可解释筛选继续研究。'],
            '总记录数应为 27,385，来源分别为 2,424、10,648 和 14,313 条。结构数以实际解析结果为准。')

        visit('explore')
        expect(page.locator('tbody tr')).to_have_count(8)
        snap('02-search','多源检索与分页',[
            '点击多源检索，选择化合物数据集。',
            '关键词支持 ID、SMILES 与来源原文的文本包含匹配；标签可选 active、inactive 或 BBB 0/1。',
            '点击查询；下方查看结果总数、性质、来源标签。点击下一页继续浏览。'],
            '默认每页 8 条；表格显示计算性质，记录名称可进入详情。来源标签与预测结果严格区分。')
        first = page.locator('tbody tr').first.inner_text()
        page.get_by_role('button',name='下一页',exact=True).click()
        expect(page.locator('.pager')).to_contain_text('第 2 /')
        assert page.locator('tbody tr').first.inner_text()!=first
        checks.append('分页显示不同记录')
        page.locator('input[name=q]').fill('tmy0')
        page.get_by_role('button',name='查询',exact=True).click()
        expect(page.locator('tbody tr')).to_have_count(1)
        with page.expect_download() as d:
            page.get_by_role('link',name='导出全部匹配 CSV').click()
        d.value.save_as(str(OUT/'search-example.csv'))
        assert 'compound:tmy0' in (OUT/'search-example.csv').read_text(encoding='utf-8-sig')
        snap('03-search-filtered','关键词定位与查询结果导出',[
            '在化合物数据集中输入 tmy0，点击查询。',
            '确认只返回相应记录，点击导出全部匹配 CSV。',
            '在下载目录查看 CSV；文件包含全部匹配记录，不受当前页限制。'],
            '实际导出文件包含记录 ID、来源、原文件行号、SMILES、标准化结构、性质和来源标签。')
        page.get_by_role('button',name='加入对比',exact=True).click()
        page.get_by_role('link',name='tmy0',exact=True).click()
        expect(page.locator('h1')).to_contain_text('tmy0')
        snap('04-detail','分子结构详情与原字段核对',[
            '点击检索结果中的 tmy0。查看二维结构、规范化 SMILES 和五项计算性质。',
            '在来源定位区确认文件及行号，点击右侧字段名称展开原始值。',
            '页面下方列出相同规范化结构的其他来源记录；可加入对比或将当前结构带入相似探索。'],
            '主表性质来自统一 RDKit 计算，原文件性质仍保留在详情中；并列呈现便于发现计算口径差异。')
        page.get_by_role('button',name='以此结构查相似分子').click()
        expect(page.locator('#similar-form')).to_be_visible()
        page.get_by_role('button',name='计算相似分子').click()
        expect(page.locator('.score').first).to_contain_text('1.000')
        snap('05-similarity','Morgan 指纹相似结构探索',[
            '从分子详情进入相似探索，SMILES 自动带入。也可手动输入其他有效结构。',
            '设置最低 Tanimoto 相似度（0 至 1），点击计算相似分子。',
            '结果按相似度降序排列，显示结构图、性质和来源；展开其余结果可查看更多匹配。'],
            '自身结构相似度为 1.000。接口最多返回前 60 条，页面先展示 6 条，其余可展开。相似度不代表药效。')
        page.locator('textarea[name=smiles]').fill('invalid_smiles')
        page.get_by_role('button',name='计算相似分子').click()
        expect(page.locator('#similar-results .error')).to_be_visible()
        snap('06-invalid','输入校验与错误恢复',[
            '在结构输入框填入无法解析的 SMILES，点击计算。',
            '查看错误提示，检查元素符号、括号与环闭合标记。',
            '改回有效 SMILES 后重新计算。阈值及筛选数值同样受到取值范围校验。'],
            '系统显示解析失败原因，保持输入表单，允许用户纠正后继续；不会展示伪造的分子结果。')

        visit('screen')
        page.locator('input[name=mw_max]').fill('300')
        page.locator('input[name=logp_max]').fill('3')
        page.locator('input[name=psa_max]').fill('100')
        page.get_by_role('button',name='执行筛选').click()
        expect(page.locator('#save-form')).to_be_visible()
        snap('07-screen','多条件可解释性质筛选',[
            '选择化合物数据集，设置 MW≤300、LogP≤3、HBD≤5、HBA≤10、TPSA≤100。',
            '点击执行筛选，系统要求全部条件同时满足，等于边界的条目计入。',
            '核对每条结果下方列出的五项命中依据；点击加入对比建立候选列表。'],
            '页面预览按 MW 升序的前 6 条命中；全部命中均可导出。默认条件可通过恢复默认条件按钮重置。')
        page.locator('#screen-results button[data-action=add]').nth(0).click()
        page.locator('#screen-results button[data-action=add]').nth(1).click()
        with page.expect_download() as d:
            page.get_by_role('link',name='导出全部命中 CSV').click()
        d.value.save_as(str(OUT/'screening-example.csv'))
        page.locator('#save-form input[name=name]').fill('低分子量候选初筛 · 操作示例')
        page.get_by_role('button',name='保存筛选记录').click()
        expect(page.locator('h1')).to_contain_text('低分子量候选初筛')
        run_url=page.url
        snap('08-run-detail','归档筛选条件与数据版本证据',[
            '筛选完成后，在名称框输入“低分子量候选初筛 · 操作示例”，点击保存筛选记录。',
            '系统保存当前已执行结果的参数和全部命中 ID，并进入归档详情。',
            '核对筛选条件、命中数、RDKit 版本及三份来源文件校验值，点击下载证据 JSON。'],
            'JSON 保留全部命中标识、前 100 条结果快照和来源指纹；名称及时间由实际操作产生。')
        with page.expect_download() as d:
            page.get_by_role('link',name='下载证据 JSON').click()
        d.value.save_as(str(OUT/'screening-evidence-example.json'))
        evidence=json.loads((OUT/'screening-evidence-example.json').read_text())
        assert evidence['params']['mw_max']==300 and evidence['ids']
        page.reload();expect(page.locator('h1')).to_contain_text('低分子量候选初筛')
        checks.append('保存记录刷新后仍可读取，证据 JSON 条件与实际输入一致')
        visit('compare')
        expect(page.locator('.compare-card')).to_have_count(3)
        snap('09-compare','候选结构与性质横向对比',[
            '从检索或筛选页加入最多三个候选，点击候选分子对比。',
            '上方并列显示结构和 SMILES，下方比较五项性质及来源标签。',
            '点击移除删除单个候选，点击清空候选清除列表；该列表保存于当前浏览器。'],
            '候选之间使用同一计算口径，原始标签只作来源信息，不据此给出跨实验效力排名。')
        page.reload();expect(page.locator('.compare-card')).to_have_count(3)
        page.get_by_role('button',name='移除',exact=True).first.click()
        expect(page.locator('.compare-card')).to_have_count(2)
        page.get_by_role('button',name='清空候选',exact=True).click()
        expect(page.locator('.empty')).to_contain_text('还没有候选')
        checks.append('候选列表持久化、单个移除与清空')
        visit('quality')
        snap('10-quality','数据质量审计与来源追踪',[
            '进入质量与溯源，检查来源文件数、非法结构数、缺失数和源内重复数。',
            '核对各文件的导入数量、导入日期与 SHA256。',
            '阅读质量规则，理解重复行保留、原字段并存以及完全相同结构关联的处理方式。'],
            'DrugBank 无 SMILES 是来源设计，不计入缺失结构。重复统计按源内规范化结构或无结构记录的 ID 进行。')
        visit('history')
        expect(page.locator('tbody')).to_contain_text('低分子量候选初筛')
        snap('11-history','筛选历史查询与证据下载',[
            '点击筛选记录，查看已保存名称、时间、命中数量和编号。',
            '点击名称进入归档详情，或直接点击导出 JSON。',
            '需要新的条件组合时，点击创建筛选记录，重新执行并另存一条记录。'],
            '历史记录保存在 SQLite；网页刷新不会丢失。记录不可在界面覆盖，以保留每次筛选证据。')

        visit('explore')
        page.locator('select[name=source]').select_option('bbb')
        page.locator('input[name=q]').fill('')
        page.locator('select[name=label]').select_option('1')
        page.get_by_role('button',name='查询',exact=True).click()
        expect(page.locator('tbody tr').first).to_contain_text('血脑屏障数据集')
        snap('12-bbb','血脑屏障来源标签查询',[
            '在多源检索中切换血脑屏障数据集，将关键词清空。',
            '选择 BBB 1 标签并查询；可改选 BBB 0 或全部标签进行比较。',
            '点击记录名称查看来源行及结构，必要时加入候选对比。'],
            'BBB 数值直接来自数据文件，本软件不将标签解释为新模型的预测输出。')
        page.locator('select[name=source]').select_option('drugbank')
        page.locator('select[name=label]').select_option('')
        page.locator('input[name=q]').fill('DB00001')
        page.get_by_role('button',name='查询',exact=True).click()
        expect(page.locator('tbody tr')).to_have_count(1)
        snap('13-drugbank','DrugBank 药物资料检索',[
            '选择 DrugBank 资料，来源标签切换为全部标签。',
            '输入 DB00001 后查询；也可按描述或机制中的英文词查询。',
            '结构性质显示为横线，加入对比按钮不可用。点击记录名称阅读原始资料。'],
            'DrugBank 文件没有 SMILES，本版本只提供资料检索和原文字段查看。')
        page.get_by_role('link',name='DB00001',exact=True).click()
        expect(page.locator('h1')).to_contain_text('DB00001')
        snap('14-drugbank-detail','DrugBank 原文阅读与字段展开',[
            '进入 DB00001 详情，核对来源文件及原文件行号。',
            '点击 Descrip、Indication、Mechanism 等字段名称展开原文，再次点击收起。',
            '原始数据未提供的字段明确显示为空，不补写推断内容。'],
            '原文按字段呈现，保留来源内容；结构区域明确提示此记录无可计算结构。')
        page.locator('summary').filter(has_text='Mechanism').click()
        expect(page.locator('details').filter(has=page.locator('summary',has_text='Mechanism'))).to_have_attribute('open','')
        visit('explore')
        page.locator('input[name=q]').fill('zzzz_no_match_2026')
        page.get_by_role('button',name='查询',exact=True).click()
        expect(page.locator('.empty')).to_contain_text('没有符合条件')
        snap('15-empty','空结果处理与条件调整',[
            '输入不存在的关键词后查询，查看零条结果及调整提示。',
            '检查当前数据来源和标签是否过度限制，清空关键词或改选条件后再次查询。',
            '无匹配结果时不会补充演示数据；导出可获得仅含表头的 CSV。'],
            '空结果属于正常查询状态，系统保留表单供用户继续操作。')
        assert not errors, errors
        checks.extend(['全部截图图片加载成功','页面无未捕获 JavaScript 异常','真实 CSV 和 JSON 下载完成'])
        browser.close()
    if any(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest for name,digest in source_hashes.items()):
        raise RuntimeError('采集期间源程序或数据发生变化，请重新采集')
    report={'source_hashes':source_hashes,'captured_at':datetime.now(timezone.utc).isoformat(),'base_url':base_url,
            'browser':'Google Chrome / Playwright','viewport':{'width':1280,'height':850,'device_scale_factor':2},
            'checks':checks,'screenshots':manifest,'js_errors':errors}
    (OUT/'screenshot-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8765')
    capture(parser.parse_args().url)
