# 主题采纳合同（theme-adoption）

> 来源：auto-os/PLAN-056（2026-11-03 work 候选 T-03；本仓候选见 git log
> plan-056 提交）。宿主主合同：auto-os `docs/specs/shell/host-theme-policy-and-delivery.md`；
> 本批登记页：auto-os `docs/specs/apps/product-theme-batch-056.md`。

## 消费形态

- **固定快照**：`vendor/themes` = UI 管理渠道发布的官方主题包快照
  （`themes` 0.2.0，内容 digest
  `9fa07742dc68aa5377ae06cb2d966386002063f184c515b6c5dddf8a6bef838e`，
  per-file sha256 与源包校验同律）。快照不可二次编辑、非第二权威源；
  升级 = UI 发新快照替换 + 本仓重验。
- **pac 声明**：`dep themes { path: "vendor/themes" }`；`theme` 键保持
  缺省 = **follow 宿主**（宿主策略完整快照 > 本 design 默认 > legacy 回退；
  显式值会以 pac 优先级压过跟随——本仓原有显式 theme 键已按此退役/保持缺省）。
- **源内导入**：`use themes.themes: Auto`——缺此行包主题不入收集链，
  design/follow 候选按 C-11 未注册整帧拒绝（031 合同）。
- **design 默认**：静态 light（无 dark_mode 位；原无 theme 键、token 类默认浅色语义不变）；
  `dark_mode` 模型位语义沿 458 机制（family 链激活时由已提交策略派生 mode
  驱动，被拒候选的 legacy 翻转不得污染）。

## 豁免与不变量

- **内容域豁免**：图表 series 数据色为图表组件内容域，不随主题映射染色；VM HTTP split 与数据身份原样。
- 原完整适用业务门在采纳前后保持：verify_basic vm **43/43** + vue **14/14**（=CHARTS-002 交付口径，中文/小数/独立几何 oracle 含内）

## 验证与测试设施（os-056 冻结工具链：auto.exe 5858593b + auto-ui-tool 3493e746）

- 无改动。desktop_mcp 为源导入期演示态脚本（README 明示由上收入口取代）——其 0/11 为陈旧脚本非回归。
- CSV 导入/列映射/工程保存导出/失败保全原样。
