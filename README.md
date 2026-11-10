# 化合物数据与可解释筛选系统 V1.0

基于现有本地数据新增的中文研究工作台。原始数据和旧脚本保持不变。

## 启动

```bash
cd /home/mytu/Project/personal/chemical_database
./run.sh
```

浏览器打开 http://127.0.0.1:8765 。默认仅监听本机。首次索引约需十余秒，实际用时取决于机器。

启动脚本优先采用 `CHEMDB_PYTHON`，其次使用本机已有 `/home/mytu/Software/miniforge3/envs/drug_info/bin/python`，否则使用 `python3`。
其他机器可创建 Python 3.12 环境并安装 `requirements.txt`。浏览器采集使用 Google Chrome；仅运行应用不需要 Playwright 或 Node。

```bash
CHEMDB_PYTHON=/path/to/python ./run.sh --port 8766
```

## 功能

- 总览：27,385 条来源记录（化合物 2,424、BBB 10,648、DrugBank 14,313）。
- 检索：来源、原文关键词、来源标签、分页和完整匹配 CSV 导出。
- 详情：二维结构、五项统一计算性质、原始字段、来源文件和行号；相同规范化结构关联。
- 相似探索：Morgan radius=2 / 2048 bits，Tanimoto 阈值与降序结果。
- 可解释筛选：MW、LogP、HBD、HBA、TPSA 上限同时生效，展示逐项命中依据。
- 候选对比：最多 3 条，保存在当前浏览器 localStorage。
- 质量溯源：非法、缺失、源内重复及文件 SHA256。
- 研究归档：参数、全部命中 ID、前 100 条结果快照、来源版本和计算库版本，JSON 导出。

DrugBank 文件无结构，提供资料检索和原文阅读，不参与结构计算。BBB/activity 是原始标签，不是预测。历史离线采集和片段脚本不属于本次界面功能。

## 一键生成真实截图与 PDF

在允许启动本地服务和 Chrome 的普通终端运行：

```bash
./generate_materials.sh
```

默认临时使用端口 8876，可用 `--port 8877` 更换。脚本使用独立启动的实际应用服务，完成真实操作与断言，采集 15 张完整截图；仅在全部步骤成功后生成最终 PDF。结束时关闭自己启动的服务。每次采集会新增一条示例筛选历史，不清除用户研究记录。

产物位于 `deliverables/`：

- `化合物数据与可解释筛选系统V1.0_软件操作说明书.pdf`：实际截图版操作说明书（生成成功后出现）。
- `manual.html`：同版可编辑 HTML 文档源文件。
- `screenshots/*.png`：1280×850 浏览器视口、2 倍像素密度、完整页面原图。
- `screenshot-manifest.json`：每张截图的地址、时间、尺寸、SHA256、操作步骤及结果说明。
- `source-inventory.json`：运行程序、验证工具和旧脚本分别统计，逐文件记录行数与校验值。
- `search-example.csv`、`screening-example.csv`、`screening-evidence-example.json`：实际界面下载文件。
- `capture-server.log`：采集期间服务日志；失败时据此检查。

目前受开发环境沙箱限制，启动监听端口报 `PermissionError: Operation not permitted`，浏览器端到端测试与截图/PDF 尚未完成。`manual-draft.html` 是不含截图的编写稿，不是最终提交材料。不能将后端测试通过视为浏览器验证通过。

## 测试

```bash
/home/mytu/Software/miniforge3/envs/drug_info/bin/python -m unittest discover -s tests -v
node tests/test_frontend.cjs
```

HTTP 测试直接调用真实处理器并使用内存流，不启动套接字。覆盖查询、异常输入、结构 SVG、CSV 数值保持、公式前缀保护及 JSON 请求校验。核心测试使用独立临时数据库导入真实数据。浏览器测试在 `tools/capture.py`，由材料生成脚本运行。

## 文件与维护

- `chemdb.py`：数据索引、分子计算、筛选与归档。
- `server.py`：本地 HTTP API 与文件响应。
- `web/`：前端页面、样式和交互。
- `runtime/chemical.sqlite`：索引与筛选历史，已加入 gitignore。
- `docs/superpowers/`：设计和执行计划。
- `tools/`：实际浏览器采集和文档生成。

停止服务后备份数据库及源文件。来源内容变化时启动会重建该来源索引。固定 RDKit 版本可维持计算口径；历史证据只记录前 100 条性质快照，全部结果 ID 均保存。需要完整性质表时同时下载 CSV。

软件名、版本、申请人、日期、功能和源程序统计口径应在申报前与申请表核对。此项目尚未提供申请表，未代填未知权属信息。源程序量使用实际物理行和非空行统计，数据、第三方依赖与截图不计入；代码鉴别材料不包含在本次 PDF 操作说明书中。
