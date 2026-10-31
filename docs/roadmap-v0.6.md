# auto-charts：独立可用性路线图

更新：2026-10-31。实际能力以Spec和冻结交付证据为准。

| 顺序 | 计划/成果 | 当前状态 | 边界/下一步 |
|---|---|---|---|
| 1 | [001用户数据到图表](plans/archived/001-data-to-chart.md) | 已交付归档/r2；VM26/26、Vue10/10与独立几何oracle有历史记录；旧计数5/7及勾选滞后保留 | 真实CSV/工程/柱图/SVG；中文query与小数域/百位截断边界不视为已关闭 |
| 2（当前） | [002中文、小数与独立运行](plans/002-standalone-unicode-and-decimal-charts.md) | drafting/r1、0/8，未实施 | T-00先核验现有公开传输/浮点与实际owner，修app接缝或消费最小前置，保留旧v1工程 |
| 后续 | AutoOS统一装配 | 未启动 | 各app单独运行门完成后由OS计划接收固定SHA；本轮不改pin |
| 后续 | Linux支持 | WAIT_DISTRO_M1 | 等发行版Nix＋COSMIC基础；不阻塞002的本机任务 |

002要求中文/特殊字符路径与名字逐字往返、小数柱域/基线/刻度正确、屏幕与SVG按独立oracle对账；旧工程删源重开与失败后的下一次保存仍成立。保持VM HTTP为正式后端，无须先实现Rust全映射。必需UI门不以raw API成功替代。

远程数据源、实时仪表盘、新图种和多写者仓储不在本轮。开发与顺序复审在D:/autostack/auto-charts独立clone main；本轮只计划/README/roadmap并push，不实现，不改现实现Spec/旧ledger，不更新OS子模块。

[README](../README.md) · [现实现规范](specs/charts/basic-capabilities.md)
