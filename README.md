# auto-charts

图表工坊，使用 AutoLang / AutoUI 开发的独立应用。

本仓是首批产品源码基线；当前能力以导入版本为准，仓库描述中的产品方向不表示全部已实现。

## 运行

安装对应版本的 `auto` CLI 后，从本仓根执行：

```sh
# vue 前端 + AutoVM HTTP 后端（缺省后端是 a2r rust 轨，本仓不用）
AUTO_BACKEND_IMPL=vm auto run

# VM 窗口 + VM HTTP 后端（merged 模式无 HTTP 服务器，本仓后端能力需 split）
AUTO_VM_WITH_HTTP=1 auto run -r vm
```

前端端口：`17850`；后端端口：`17851`（`pac.at` `back_port`，可 `-F/-B` 覆盖）。
后端数据目录：`AUTO_CHARTS_DATA` 环境变量 → 缺省 `USERPROFILE/.auto-charts`。

共享 StyleKit 已固定在 `vendor/stylekit`，无需相邻 auto-lang 示例目录。

## 基础能力验收（CHARTS-001）

```sh
# 后端 HTTP 探针（先启动：AUTO_CHARTS_DATA=<隔离目录> auto service --server vm）
python tests/basic/probe_api.py [base_url]

# 双端真实任务验收：导入 → 列映射 → 图表 → 保存 → 重开 → 导出 SVG
python tests/basic/verify_basic.py --profile vm    # VM 窗口（MCP 驱动）
python tests/basic/verify_basic.py --profile vue   # vue + Playwright
```

`tests/desktop_mcp.py` 为源导入期的演示态脚本（依赖旧 monorepo 布局的
`auto.exe` 相对路径与已退役的流式演示字段），由上收入口取代。

## 来源与组合

来源提交、路径与文件 hash 见 `SOURCE-IMPORT.json`。首次导入提交保留在 `source-sync` 分支；完整 v0.5 恢复后从该基线导入差异，再与产品开发线合并。

AutoOS 通过 [`apps/024-charts`](https://github.com/auto-stack/auto-os/tree/v0.6-dev/apps/024-charts) submodule 固定本仓版本；教学 Demo 保留在来源仓。

已有测试随源导入；端口与平台相关测试需要按本仓配置准备运行环境。安装/启动与双端完整功能验收是不同检查项。

## 基本能力补齐计划（2026-10-29）

[CHARTS-001：用户数据到图表、保存与导出](docs/plans/archived/001-data-to-chart.md) 已交付（2026-10-29，r2 复审 pass，reviewed e3375e2）：用户任务能力实现并通过双端验收（见上节），canonical 规范见 [docs/specs/charts/basic-capabilities.md](docs/specs/charts/basic-capabilities.md)。
总状态与前置见 [AutoOS B类总跟踪表](https://github.com/auto-stack/auto-os/blob/main/docs/plans/b-apps-basic-capabilities.md)。基础能力通过后再考虑Linux；A类统一等待 auto-os-distro 完成 Nix＋COSMIC 基础，后续增强另会话。

开发使用独立 clone `D:/autostack/auto-charts` 的 main；AutoOS 内对应子模块仅固定已交付提交，流程见 [App开发与子模块](https://github.com/auto-stack/auto-os/blob/main/docs/design/strategy/app-submodule-workflow.md)。
