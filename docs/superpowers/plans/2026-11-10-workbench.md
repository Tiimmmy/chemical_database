# Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 交付真实可运行的化合物工作台与完整截图 PDF。
**Architecture:** RDKit 计算与 SQLite 数据持久化；标准库 HTTP API；原生浏览器前端。截图与 PDF 通过 Playwright 复现。
**Tech Stack:** Python 3.12, RDKit, openpyxl, SQLite, HTML/CSS/JS, Playwright。
**Spec:** docs/superpowers/specs/2026-11-10-workbench-design.md

## Global Constraints
- 不改变原始数据；不将来源标签解释为预测。
- 仅在本地运行；所有截图必须来自最终应用。
- 无申请表时软件名版本暂定，实际源程序量单独统计。

## Review Focus
- 非法 SMILES 与非有限阈值应返回清晰错误。
- 无结构 DrugBank 条目须提供来源内容且禁止伪造计算。
- 查询特殊字符不得注入 SQL 或 HTML。
- 分页、空结果、保存记录和导出须保持条件一致。
- 截图与最终功能、源代码统计须可核对。

### Task 1: 数据和计算服务
Files: chemdb.py, server.py, tests/test_workbench.py, requirements.txt, run.sh
- [ ] 先写并运行真实数据、过滤、相似性、校验、保存导出测试。
- [ ] 实现 Store(root, db_path)、search(params)、detail(id)、similar(smiles, threshold)、screen(params)、save_run(name, params, ids)、quality()。
- [ ] 导入三个源文件，记录 SHA256、数量和缺失/重复/非法结构指标。
- [ ] 运行 unittest 验证。

### Task 2: 完整交互界面
Files: web/index.html, web/app.js, web/style.css
- [ ] 实现总览、检索、详情、相似度、筛选、对比、质量、历史。
- [ ] 真实浏览器验证筛选、翻页、保存、刷新、导出与错误提示。

### Task 3: 操作说明和证据
Files: tools/capture.py, tools/build_manual.py, README.md, deliverables/*
- [ ] 按实际流程截取全部页面和关键操作结果。
- [ ] 生成 PDF、功能截图清单、源码统计及申请表核对说明。
- [ ] 检查 PDF 页数、截图尺寸、文本和视觉质量。
- [ ] 独立代码审查，修复实质问题后重新验证。

## 执行记录
直接在用户指定目录开发，保留既有文件；不自动提交或发布。采用现有解释器避免受限网络安装。

### 当前验证状态
- 数据和计算服务：10 项 Python 测试通过。
- 前端标题转义：Node 回归测试通过。
- 独立审查：三项重要问题已修复并增加回归验证。
- 浏览器/截图/PDF：未完成。沙箱禁止 socket 创建，真实服务无法启动；已提供普通终端一键生成命令。
- 已生成不含截图的说明书编写稿和独立源代码统计；未伪造最终 PDF。
