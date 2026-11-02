# auto-charts：独立可用性路线图

更新：2026-11-02。实际能力以Spec和冻结交付证据为准。

| 顺序 | 计划/成果 | 当前状态 | 边界/下一步 |
|---|---|---|---|
| 1 | [001用户数据到图表](plans/archived/001-data-to-chart.md) | 已交付归档/r2；VM26/26、Vue10/10与独立几何oracle有历史记录；旧计数5/7及勾选滞后保留 | 真实CSV/工程/柱图/SVG；中文query与小数域/百位截断边界由002闭合 |
| 2（当前） | [002中文、小数与独立运行](plans/archived/002-standalone-unicode-and-decimal-charts.md) | 已交付归档（2026-11-02，r1 8/8）：中文/特殊字符 POST body 逐字往返、小数域/基线/刻度双端 float 统一+整数标签、独立启动与失败保全；统一回归门 VM 43/43、Vue 14/14、probe 0 失败；canonical Spec basic-capabilities（修订）+ standalone-runtime（新增） | VM 轨框架缺口 D1/D2 已绕开并登记（决策稿 §6，owner auto-lang/auto-ui）；AutoOS 组合版本由统一集成计划接收 |
| 后续 | AutoOS统一装配 | 未启动 | 各app单独运行门完成后由OS计划接收固定SHA；002 merge 不改pin |
| 后续 | Linux支持 | WAIT_DISTRO_M1 | 等发行版Nix＋COSMIC基础；不阻塞002的本机任务 |

002交付后：中文/特殊字符路径与名字逐字往返、小数柱域/基线/刻度正确、屏幕与SVG按独立oracle对账均已由双端真实UI门覆盖（[决策稿](plans/evidence/002/standalone-decision.md)、[现实现规范](specs/charts/basic-capabilities.md)、[独立运行规范](specs/charts/standalone-runtime.md)）；旧工程删源重开与失败后的下一次保存仍成立。保持VM HTTP为正式后端，无须先实现Rust全映射。必需UI门不以raw API成功替代。

远程数据源、实时仪表盘、新图种和多写者仓储不在本轮。开发与顺序复审在D:/autostack/auto-charts独立clone main。

[README](../README.md) · [现实现规范](specs/charts/basic-capabilities.md)
