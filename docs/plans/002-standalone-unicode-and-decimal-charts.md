---
plan_id: CHARTS-002
status: reviewed
feature_name: "中文数据传输、小数图形与独立运行收口"
author: [Codex]
created_at: 2026-10-31
updated_at: 2026-10-31
plan_revision: 1
current_step: 5
total_steps: 8
base_branch: main
base_commit: a5aa170c564f22a42f7a518a6d02d28650f15d32
depends_on: ["CHARTS-001"]
supersedes_spec_components: ["docs/specs/charts/basic-capabilities.md"]
new_spec_components: ["docs/specs/charts/standalone-runtime.md"]
touched_goals: []
---

# CHARTS-002：中文数据传输、小数图形与独立运行收口

## 0. 变更摘要

复用001的CSV→映射→图表→工程→SVG闭环，补齐中文路径/工程名传输与小数值域/刻度的基本可用性，固定正式独立启动和真实双端门。001及其历史计数保持原样；不引入新的图表生态或OS依赖。

## 1. 目标

用户从本机含中文、空格和URL特殊字符的目录导入CSV，用中文工程名保存、删源后重开并导出；Vue与原生VM结果逐字一致。柱图对受支持正/负/小数/零数据具有正确域、基线和刻度，屏幕与导出符合独立几何oracle。

非目标：远程数据源、实时仪表盘、新图种、任意精度数学、多写者仓储、Rust后端全映射、OS集成与Linux。保留VM HTTP为正式后端选择，不把改Rust作为本包启动前置。

## 2. 架构方案

开发、内部检查和最终复审顺序使用同一个 `D:/autostack/auto-charts` 独立 clone、`main` 分支；不新建应用 worktree、不在 AutoOS 子模块中实现，一 app 一写入者，复审时暂停实现写入。框架变更必须在实际 owner 仓另走其 Plan/worktree 规约；本计划不自动取得框架源写入权。

用户本轮授权（2026-10-31）：建立后续计划、更新本 app README/roadmap、提交与推送这些文档；**暂不实施，不更新 AutoOS 子模块**。后续实施需另行进入 work。应用验收与交付不以 AutoOS 装配或 Linux 为前置；Linux 仍 `WAIT_DISTRO_M1`。OS 组合版本由未来统一集成计划接收，本计划 merge 只交付 app，不改父仓 gitlink、manifest 或 `.gitmodules`。

实现保持纯 `.at`，复用公开 SDK 与既有测试；不手写业务 Rust、不改生成 Rust/Vue 或临时生成目录来交付修复。`docs/specs/` 是现实现单源；下面的规范增量只是提案，本轮不写 canonical Spec、旧 ledger 或手工索引。原始截图/日志/报告本地保存，Plan 记录命令、退出码、版本/hash 和摘要；不提交新的非 Markdown 证据附件。

保持 `csv.at`/`chart_project.at` 和v1工程内嵌数据；修复前后可打开已有工程，失败不覆盖旧工程或导出。运输层优先复用当前公开Http/JSON/查询绑定；不能用仅ASCII文件名的限制绕过中文任务，不能复制一个私有HTTP栈。框架确有缺陷时按当前owner提最小前置，其他应用任务不等待它。

## 3. 技术栈

应用 `.at`、AutoVM HTTP、现有BarChart/SVG；Vue Playwright、原生MCP、Python独立CSV/XML/几何oracle。复用 `tests/basic/verify_basic.py`、`probe_api.py`、001的原有几何oracle与CSV预算，不泛化到未冻结的line/area/donut。

## 4. 需求分析与背景调查

- 已观察：前端在GET query中直接拼接path/name/out_path，服务端import/save/export走GET标量；001因旧Http body分歧这样规避。Vue fetch percent编码CJK，当前auto-web `server_route.rs::url_decode`仍逐字节转char；G-6b不能视为已关闭。
- 已观察：屏幕bar_chart Init将小数文本截成int求域/刻度；后端 `chart_project.at::parse_dec_hundredths`读全部小数但仅保留前两位。当前已接受的更长小数存在屏幕/导出不同精度，需同时固定数据解释与展示，不能只改标签。
- 001支持≤10MiB、≤10000行、≤64列、1..4数值列、绝对值预算10000000；实际边界与Spec有差异时T-00明确逐项对账，不静默收窄已有合法输入。正常有符号/零/CSV引用/删除源后重开与输出失败保全是回归。
- 当前中文解码与HTTP生成实际owner为auto-web；001内auto-lang旧归属只保留历史。已有公开JSON体或UTF-8修复是否可用由T-00先核实，不预建框架仓或重做Web生态。

| 源文件 | SHA256（完整值） |
|---|---|
| `docs/specs/charts/basic-capabilities.md` | `e466ffd748594987271488b74fc44397516ed682149f460d1724bc582ce237de` |
| `docs/plans/evidence/001/capability-decision.md` | `915831940861476ed5cee79ba0a37f6239f984d55b9f33b6fbc89035dcf94663` |
| `src/back/api.at` | `ba6e7de789ca837e3e08680a3a2254a2904414addc9ee3bac8037de85298f03a` |
| `src/back/chart_project.at` | `00484b53c018bbc41a64e3c243f37173142c422ba4c55715db4b7580890a837d` |
| `src/front/app.at` | `8e30ea78780639fd03dfaf91851e501823396475a1293c0707e9439aab3db28c` |
| `src/front/components/bar_chart.at` | `7845b3b4bd3a405f875191c6a70b58c2830d54813c35e312b06f9fafc897ffca` |
| `tests/basic/verify_basic.py` | `a6c53cec0e0aab285ac94914e94a775096b83233ed8b06328fd1210f59625959` |
| `auto-web` 观察版本 | `c48924f3381e775b8435c3989e739df347570f2c` |
| `D:/autostack/auto-web/crates/auto-web/src/api_gen.rs` | `364d347f22f72290d1595ca887867e458294f6092fb5776d6cbcac1c4aeb1aa5` |
| `D:/autostack/auto-web/crates/auto-web/src/http_server/server_route.rs` | `5e5ccda16f1c242e5772e537ff1db8616b148e081a2db0c07486f9398e4b1a45` |

## 5. 详细设计

1. **T-00 决策稿（新增）** `docs/plans/evidence/002/standalone-decision.md`：固定CLI/tool/当前API版本，探测Vue/VM的UTF-8 query/JSON body全链路、已存在公共API、正式split启动/冷准备及预算，给出app接缝或最小auto-web前置。表明每一条已观察结论与尚待运行验证假说。
2. **传输一致性**：路径/名字/CSV内容在客户端→绑定→文件/工程→回读全过程逐字保留。CJK、空格、`+ & # % ? =`和百分号字面量分别有合法对照，不做双重decode或将字面`+`误作空格。变更类save/export优先迁到现有可用POST体；若现有SDK不支持，T-00先闭合最小前置，不以长期有副作用GET和手工ASCII转义洗绿。已有v1工程格式兼容，不承诺旧有缺陷API永远不变。
3. **小数与几何**：CSV原文存储不被改写；数据解释在屏幕/导出一致，零域退化不吞非零小数，负值基线正确，刻度不重复/不误标整数。T-00冻结现有浮点/可证定点策略及其实际精度，至少0.1/0.2、±0.5、25.5及0.001/0.002必须可区分；不能继续静默截断后声称原值精确。任意精度不承诺，超过可表示精度必须明示策略，不能临时禁用所有小数。
4. **独立启动**：正式VM HTTP split profile，不依赖OS；README统一给Windows可执行准备/启动命令。无app target/gen缓存的准备有阶段和有界超时，坏tool/端口冲突明确失败，只管理本次进程/隔离数据，不清共享框架target。
5. **永久门**：扩展原有 `python tests/basic/verify_basic.py --profile vue|vm`，新增传输/几何用例由T-04落地；独立oracle从CSV原值计算域/基线/逐柱坐标并解析输出XML，不以两端使用同一错误算法相等为通过。工程成功存盘后删除源CSV重开继续导出，失败后下一次合法保存必须成功。

### 规范增量

| delta_id | add/modify/retire | docs/specs/... target | before/after rule | rationale | acceptance IDs |
|---|---|---|---|---|---|
| SD-01 | modify | docs/specs/charts/basic-capabilities.md | 中文降级/整数域/百位截断 → 正式传输、共同明确精度、双工件真实几何及兼容 | 修真实用户数据可用性 | AC-02/03/04 |
| SD-02 | add | docs/specs/charts/standalone-runtime.md | 新增准备/split启动、预算、当前owner与双端永久门 | 独立启动可复验 | AC-01/05 |

## 6. 测试设计

CH-01..06均owner_stage=work，T-04在既有门中使其可执行，拟补测试数据/断言路径为新建并明确与旧API预算门整合；本轮不生成fixture或运行产品。

| Case ID | AC / invariant | 输入/入口 | 区分性 oracle / 预期 | 覆盖边界 |
|---|---|---|---|---|
| CH-01 | AC-01 | 无app构建缓存的文档准备＋Vue/原生独立split启动；占用端口/坏tool | 实际页面/窗口与后端就绪、data_dir正确；失败非零且不碰既有实例 | 不要求Rust后端 |
| CH-02 | AC-02 | 真实UI填中文目录、中文工程名，空格/+&#%?=文件名分别作为有效路径；往返两次 | 后端实际打开的文件sha与独立读源一致，磁盘/重开名字逐字相等；%2520与空格不混淆 | Windows合法文件名；字面?在平台不合法时测工程名/公开绑定层 |
| CH-03 | AC-03 | [0.1,0.2]、[-0.5,0,0.5]、[-300,0,25.5]、[0.001,0.002]、全零、四系列 | 独立计算域/基线/柱坐标；屏幕±1px、SVG±0.01px；不等数据不得塌成同柱或截整数域 | 容差基于560×300逻辑视窗，其他缩放先归一 |
| CH-04 | AC-04 | 旧v1工程、删源重开、坏CSV/非法数值/不可写导出及预算边界 | 旧工程保真；失败旧文件/有效数据hash不变；恢复后下一次保存/导出成功 | 保留001预算与错误分类 |
| CH-05 | AC-02/03/05 | 解码旧字节算法、强制整数域/百位截断的隔离反例 | 中文/小数区分性断言失败，总门非零；还原合法对照通过 | 不在生产库作变异 |
| CH-06 | AC-05 | 原有双端CSV→映射→工程→SVG全流程＋新用例 | 必需实际UI任务均执行，无skip/pending/零场景，错误不被示例数据覆盖 | 柱图合同，非全部图种 |

最终review在同一clone以独立上下文复核真实传输和独立几何oracle；不自动新建agent/chat，不执行无关语言全仓Cargo。

## 7. 验收标准

- AC-01（owner_stage=work）：正式独立VM HTTP双端准备/启动和故障语义明确，CH-01通过。
- AC-02（owner_stage=work）：中文/特殊字符的路径与名字经真实UI及服务端逐字保真，CH-02通过；不得仅API raw UTF-8成功而Vue失败。
- AC-03（owner_stage=work）：合法小数的域/基线/刻度与柱高真实正确，屏幕/SVG符合独立oracle与精度说明，CH-03通过。
- AC-04（owner_stage=work）：既有工程、CSV预算/错误、删源重开及失败后恢复保全成立，CH-04通过。
- AC-05（owner_stage=work）：旧/新真实双端门和CH-05/06完整执行，反例可检测，SD候选与README/roadmap符合结果。
- AC-06（owner_stage=review）：冻结提交独立复审AC-01..05、SD-01/02和实际框架消费版本。
- AC-07（owner_stage=merge）：本app规范/归档/计数/提交push闭合；不动旧001或AutoOS pin。

## 8. 执行步骤

- [x] T-00（owner_stage=work；依赖001交付；AC-01/02/03）：完成传输/数值/启动全路径有界探针，冻结精度、预算及最小owner前置，不先重写CSV/HTTP栈。
  [✅ 已完成 2026-11-01] 决策稿 `docs/plans/evidence/002/standalone-decision.md`。实测：服务端 POST JSON body 标量与 whole-body 单 str 形参均逐字 UTF-8（P2a/P3）；GET query `+`→空格、%XX latin-1 乱码、`&` 截断（P1b/c/d）；真 UI 红态两轨 CJK 路径导入均失败（vue=三重破坏；VM 运行时自行百分号编码——001「VM raw OK」已漂移）；`Http.post(url, record)` VM 轨退化句柄串（G-6a 复现）、vue 轨绿；冻结 POST+单 `payload str` whole-body+首字节剥壳设计。float 实测 f64 语义、`.to_string()`≈%.8g、0.001/0.002 可区分、`10000000.001→"10000000"`；拼接陷阱（无 to_string 输出位型）。三形态启动实测可用。001 probe 断言 `y="122.85713"` 已随运行时漂移（现 `122.85714`），T-04 改容差断言。
- [x] T-01（owner_stage=work；依赖T-00及真实必要前置；AC-02）：修前端/API传输接缝，先建立CH-02反例再实现、回放，保留v1工程。
  [✅ 已完成 2026-11-01] 反例先行（红态已录决策稿 §2.2）：真 UI 两轨 CJK 路径导入均失败（vue=乱码+`+`→空格+`&`截断；VM 运行时自行百分号编码）。实现：import/validate/save/export/project_get 迁 POST+单 `payload str` whole-body（首字节 `"` vs `{` 剥壳兼容 vue JSON.stringify 外壳），原 GET 端点保留兼容；前端 5 调用站点迁移。附带修复 slug_of CJK 逐字节拼接丢弃缺陷（`a中b→ab`、全 CJK 坍缩 `chart` 互撞）→整体 replace 折叠，名称/slug 预算 ≤192 字节。回放：两轨 `已导入 3 行 × 2 列` + 中文工程名保存/打开 ✓（决策稿 §7）。
- [x] T-02（owner_stage=work；依赖T-00；AC-03）：统一屏幕/导出的合法数值解释、域/基线/刻度，建立CH-03独立oracle并排除旧截断反例。（F-1 已修复 b6e6bcf，闭合证据见 §9 工作回执）
  [🔶 部分完成→修复中 2026-11-01] 已交付：后端 `parse_value`（float，替代定点百位）；阶梯含负指数档+1e-7 相对容差；刻度 = k·step 乘法求值、标签 `label_of_k(k,m,e)` 整数重构（f32 噪声隔离，T-00 修正：VM float=f32）。组件：数据面改吃 `rows_frag` 字符串单元（绕开 VM 轨数字小数通道归零 D1）、`parse_decimal` 自解析、调用位 `key: chartEpoch` 强制重算（D2，框架 PLAN-536/os-016 挂载身份语义）。独立 oracle（Python f64）：导出几何 48/48；CH-05 区分性自检。F-1 已修复（b6e6bcf）：相异 f32 精确哨兵 + 精确十进制边界判定，probe_api 增补持久边界用例全绿。
- [x] T-03（owner_stage=work；依赖T-00/01/02；AC-01/04）：收口正式独立准备/启动、错误分类、旧工程/失败恢复，不增加OS依赖。
  [✅ 已完成 2026-11-01] 三形态启动实测（决策稿 §1/§4）；端口占用→`os error 10048` 非零失败且不碰既有实例；冷准备 `auto build -r vm` 实测 0.4s（CLI 解释运行）；README 固化准备/启动/失败语义。CH-04：旧 v1 工程打开+内嵌导出 ✓；目录占位导出明确失败且既有导出不动、恢复后同一导出成功 ✓（VM 缺省路径制造——MCP 输入焦点仅首 input 可靠，登记 G-9）；vue 显式路径目录失败 ✓。
- [x] T-04（owner_stage=work；依赖T-03；AC-05）：扩展原有双profile门，跑CH-01..06及必要旧预算/几何回归、反控；准备SD候选。
  [✅ 已完成 2026-11-01] `verify_basic.py` 扩展：CH-01 启动就绪、CH-02 CJK/`%20` 字面对照/中文工程名保存打开导出、CH-03 屏幕基线/刻度 ±1px+标签逐字（VM 状态读数）与 vue SVG path ±1px、CH-04 旧工程/删源/失败保全/恢复、CH-05 区分性自检、CH-06 全序列。门结果：**VM 43/43、Vue 14/14、probe_api 0 失败（容差化重写 001 漂移断言）**。t02 独立几何 oracle 48/48。原始门日志/JSON 在 plan-artifacts（本地）。SD 候选见 Plan §5（slug/名称 192 字节、f32 策略、全零退化 [0,100] 文字修正待 merge 落 canonical）。
- [x] T-05（owner_stage=work；依赖T-04；AC-01..05）：复核漂移、精度与兼容证据、README/roadmap，提交execution_done。
  [✅ 已完成 2026-11-01] 决策稿修订（f32 修正、D1/D2/G-9 框架缺口登记、假说闭合 §7）；README 002 交付状态+三形态启动/失败语义；roadmap 第 2 行更新（work 交付 5/8，待复审/merge）；兼容：原 GET 端点保留、v1 工程格式不变、001 预算不变。工作树提交见 §9。
- [ ] T-06（owner_stage=review；依赖T-05；AC-06）：同clone独立上下文最终复审，源码相同不替代独立数值/字节对账。
- [ ] T-07（owner_stage=merge；依赖T-06 pass；AC-07）：仅app规范/归档/提交push收尾，AutoOS版本留未来统一计划。

## 9. 复审记录

- stage: new | plan_id: CHARTS-002 | plan_revision: 1 | outcome: pass（仅有界 T-00 就绪，产品与双端验收未执行） | next: work/T-00（等待后续实施指令）。
- 现有归档计划、Spec 与源码保持原样；旧验收只证明其冻结版本与已声明范围。应用提交/push 不升级 AutoOS 组合版本。
- stage: work | plan_id: CHARTS-002 | plan_revision: r1 | outcome: pass（execution_done） | worktree: D:/autostack/auto-charts（main，Plan §2 单 clone 纪律） | branch: main | base_commit: e5e91a9 | code_commit: 061feb4 | dependency_revisions: auto CLI 0.1.0+plan-890-verified-r7-t19-5-g55c98c7（auto-man 1eeac78）；auto-web ec9c4ba（只读核对） | task_ids: T-00..T-05 | evidence: 决策稿 docs/plans/evidence/002/standalone-decision.md（§2 传输红绿/§3 f32 数值/§6 D1·D2·G-9 缺口/§7 假说闭合）；门：VM 43/43、Vue 14/14、probe_api 0 失败、导出几何 oracle 48/48（原始日志/JSON 本地 D:/autostack/plan-artifacts/plan-002/，不入仓） | blockers: 无 | next_responsible_role: review（T-06 独立复审 AC-06；merge 统一回归门归 review/merge 拥有，保持待办）
- stage: goal | plan_id: CHARTS-002 | plan_revision: r1 | round: 1 | from: drafting | to: execution_done | status: execution_done | outcome: pass | worktree: D:/autostack/auto-charts | commit: 061feb4 | next: review
- stage: work | plan_id: CHARTS-002 | plan_revision: r1 | outcome: pass（F-1 修复，execution_done 恢复） | worktree: D:/autostack/auto-charts | branch: main | base_commit: f8741d2 | code_commit: b6e6bcf | dependency_revisions: 同前（auto CLI plan-890-verified-r7-t19-5-g55c98c7 / auto-web ec9c4ba 只读） | task_ids: T-02（F-1） | evidence: 修复=DEC_ERR_RANGE 改 -1e9（f32 精确、与 SYNTAX(-2e9) 相异）+ parse_value 精确整数部分边界判定先于 f32 舍入；闭合 oracle=probe_api 新增持久边界用例全绿（10000000/10000001→err_value_range；9999999/9999999.5/9999999.9/-9999999.99 接受；abc→err_cell 行2列1），probe 门 0 失败；兄弟路径手算几何（[-0.25,0.75] 刻度[0,0.5]、柱 260/20、基线 200）5/5 ✓，9999999.5 验证+导出 ✓。vue 门证据复用（前端/组件代码未触碰，fixture 均 <1e7 不受哨兵/边界影响）；vm 门 43/43（review 基线 061feb4）对未变 fixture 仍有效；冻结基线统一复跑保持 merge 拥有待办。**复审探针期望修正**：复审时我预期 "9999999.9"/"-9999999.99" → err_value_range 系探针错误（001 定点契约实际接受 |v|<1e7 含小数），正确期望为接受，已按 001 一致口径修正——该部分属探针缺陷单列，不弱化有效断言（F-1 本体=10000000 误报 err_cell 与 9999999.5 误拒，均实证保留）。**环境事件**：并发会话（plan-002 共享 scratch 命名空间冲突，文件特征为另一仓库 native-ui 探针）于 2026-11-02 05:58-06:02 清空原 plan-002 草稿范围并反复清扫全部 auto.exe 进程（本会话 service11/service_f1/service_f1b 被杀、vm 门复跑中止于 7 PASS）；本计划草稿证据改用新登记范围 D:/autostack/plan-artifacts/plan-002-auto-charts/（merge 清理时一并处理；原 plan-002/ 残留属另一会话，本会话不动）。 | blockers: 无（环境清扫下的 vm 门整跑留 merge 统一回归门，已记录） | next_responsible_role: review（F-1 受影响范围复审：probe_api 边界块 + 兄弟几何；其余评审范围维持 T-06 记录）
- stage: goal | plan_id: CHARTS-002 | plan_revision: r1 | round: 3 | from: executing | to: execution_done | status: execution_done | outcome: pass | worktree: D:/autostack/auto-charts | commit: b6e6bcf | next: review
- stage: review | review_scope: final（F-1 修复复审重审） | reviewer_identity/limitations: 与实现同会话（limitation 已声明），裁定由工件重构——在 b6e6bcf 冻结基线上新鲜重跑 | plan_id: CHARTS-002 | plan_revision: r1 | outcome: pass（reviewed） | worktree_path: D:/autostack/auto-charts | branch: main | reviewed_commit: b6e6bcf（代码）+ 22fdfc4（计划簿记） | base_commit: f8741d2（needs_fix 记录） | dependency_revisions: auto CLI plan-890-verified-r7-t19-5-g55c98c7 / auto-web ec9c4ba（只读） | spec_inputs: docs/specs/charts/basic-capabilities.md；决策稿 §3/§5 | acceptance_results: F-1 复现集在修复基线全部反转——10000000/10000001→err_value_range ✓、9999999/9999999.5/9999999.9/-9999999.99→接受 ✓、abc→err_cell(行2列1) 对照 ✓（probe 门 0 失败，exit 0）；兄弟路径（[-0.25,0.75] 刻度[0,0.5]、柱 260/20、基线 200、9999999.5 接受）全部 ✓；既有 probe 套件（CSV/工程/导出几何容差 oracle）未受修复影响同轮全绿 | pending_closeout_gates: 冻结基线统一回归（merge 所有，本日执行）；canonical Spec SD-01/02 落地、归档、push（merge） | findings: 无新增；F-1 关闭（旧例闭环+不变量闭环：哨兵 f32 精确相异 + 精确整数边界判定，兄弟与对照未现新回归） | evidence: 本地 plan-002-auto-charts/probe_rereview.log + 本记录内嵌结果 | next: merge（T-07）
- 目标授权记录：用户 /goal「完成计划002」= 全链授权（work 含本 Plan §2 单 clone/main 纪律的 worktree 约定、review、有界修复、merge），后续阶段继承，不再询问。
- stage: review | review_scope: final | reviewer_identity/limitations: 与实现同会话（ limitation 已声明），裁定全部由工件重构——三门前置证据、自选输入的独立 API/几何探针、f32 哨兵直接等值探针（px_sentinel eq=1, half_eq_big=1，探针代码已还原不入库） | plan_id: CHARTS-002 | plan_revision: r1 | outcome: needs_fix | worktree_path: D:/autostack/auto-charts | branch: main | reviewed_commit: 061feb4（代码）+ 8d45023（计划簿记，非语义） | base_commit: e5e91a9 | dependency_revisions: auto CLI 0.1.0+plan-890-verified-r7-t19-5-g55c98c7 / auto-web ec9c4ba（只读） | spec_inputs: docs/specs/charts/basic-capabilities.md（现行为源，SD-01 目标）；决策稿 standalone-decision.md §3/§5/§6 | acceptance_results: AC-01 pass（启动三形态+端口占用 os error 10048 非零不碰既有实例+冷构建 0.4s）；AC-02 pass（VM/vue 门 CJK 全序列+独立探针双 body 形态歧视/含引号花括号工程名逐字往返）；AC-03 partial（几何手算 [-0.25,0.75] 5/5 ✓、语法矩阵 6/6 ✓，但 F-1 边界分类/收纳回归）；AC-04 partial（旧工程/删源/失败保全/恢复 ✓，预算边界分类受 F-1）；AC-05 pass（门重跑 VM 43/43、Vue 14/14、probe 0 失败；README/roadmap 与证据一致；SD 候选在案）；AC-06 本记录；AC-07 pending（merge） | pending_closeout_gates: 冻结基线统一回归（merge 所有）；canonical Spec SD-01/02 落地（merge 所有） | findings: **F-1（P1，契约内回归，owner T-02）** 值预算边界分类失效：(a) f32 使 DEC_ERR_SYNTAX(-2e9) 与 DEC_ERR_RANGE(-1999999999) 坍缩为同值（px_sentinel 实测 eq=1、range_neg 打印 -2000000000），validate_rows 先判 SYNTAX → 一切 |v|≥1e7 拒绝误报 err_cell（复现：validate "10000000"/"10000001"/"9999999.9" → err_cell，契约要求 err_value_range；"9999999"→ok、"9999998.5"→ok 对照成立）；(b) 预算内 "9999999.5"（001 定点百位路径可接受）被 f32 进位到恰 1e7 后拒收（px_sentinel half_eq_big=1）。render_bar_svg 两哨兵同归 ""（err_render 泛化，无可见错码，同根）。修复方向供 work 验证：精确十进制域比较（int_part+frac）先于 f32 舍入 + f32 可精确表示的相异哨兵（如 -2e9/-1e9）；闭合 oracle：verify_basic 增补预算边界用例 "10000000"→err_value_range、"10000001"→err_value_range、"9999999.5"→ok、"abc"→err_cell 行2列1，并复跑受影响门。非阻塞观察（契约外，不列修复）：body 键 "payload" 与形参同名时 whole-body 容忍被按名绑定抢占（恶意客户端可致 500），契约未承诺该形态。 | evidence: 本地 D:/autostack/plan-artifacts/plan-002/probes/review_vm_gate.log、review_vue_gate.log、review_probe_gate.log；本记录内嵌复现命令与实际响应 | next: work（F-1 有界修复）

## 10. 待澄清事项

本次规划没有待用户重新确认的产品方向。T-00 负责核实技术能力与实际 owner，决策稿必须先闭合再进入依赖实现。若探针显示必须改变目标、降低必需验收或扩大跨仓写入范围，报告具体证据并保留受影响任务未完成；不得用占位、跳过、API 预操作或历史总数替代必需用户任务。
