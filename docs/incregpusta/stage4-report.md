# 阶段 4 完成报告：确定性 buffer trace 与 one-shot fresh replay

> 状态：Stage 4 功能实现、独立复审与正确性验收完成；ecc-tools 已封存为 `eff4706f77a882d84317341f78e567ef5262b6d1`，parent 提交在本报告入库后创建，均不推送
> 日期：2026-09-01
> 基线：parent `8787d4b1a6743169a2ff4dcb4c173832577dbd8c`，ecc-tools `5877ba0671da77ee6a69ad9765f1d9c761923965`
> 范围：确定性 greedy selector、fixed semantic trace generator/replayer、synthetic/real production loading、CPU/full 与 CSR full 逐批比较；不含 Dual-CSR、CUDA、closed-loop 多模式优化或物理 IDB 提交

## 1. 结论

阶段 4 已把 timing-driven buffer insertion 固化为可生成、可冻结、可跨进程重放的 semantic trace。generation 在唯一 CPU/full reference 上逐轮观察候选、选择正收益插入并完整重算；replay 只消费 replay-safe semantic edits，不读取 generation-only 的 slack、gain 或预制 timing 答案。

synthetic 与 real-design 两类 workload 共用同一 production fresh loader 和 callback-scoped adapter。每个 cumulative prefix 在独立 child process 中重新解析五件 source artifact、建立 fresh session、执行 Stage 3 transaction、运行 native CPU/full 与 CSR full，并逐字段比较 Database、resolver、host CSR、reference input、timing result和累计 semantic trace。源 artifact、primary IDB、可选 logical view与物理投影在运行前后保持不变。

本阶段不声称增量性能。所有成功路径仍执行完整 CPU/full；`cpu/incremental`、`gpu/full`、`gpu/incremental` 以及真实 parasitic replay 均明确拒绝或记录为不支持。完成结论以功能字段、生命周期和 fresh replay 一致性为主，完整性摘要只辅助确认 artifact 身份。

## 2. 已交付功能

### 2.1 Selector 与 observation

- `NativeBufferObservationExtractor` 从已完成 full timing 的 raw Database 枚举 single-driver、data-only、合法 instance-input 候选；clock、sequential、gating 与未物化 timing 均按稳定规则过滤或 typed reject。
- `GreedyBufferCandidateSelector` 先按 net slack 与 stable semantic refs 选择 top-k critical nets，再按实际 Elmore gain、pin/cell/port stable bytes 选择每网唯一候选。
- gain 统一使用 kΩ、pF、ns，并按固定 binary64 顺序计算 `benefit`、`penalty`、table-derived buffer delay 与最终 gain；`±0`、负值、NaN、Inf、overflow 全部拒绝。
- selector 没有随机 ranking 分支。property seeds 只置乱测试输入并进入 synthetic creation token，所有 seed 的接受语义顺序保持一致。

### 2.2 Fixed trace contract

- replay header 与 payload 使用 strict tagged union，区分 `synthetic` 和 `real_design`，每层拒绝 unknown field、duplicate key、错误版本与 variant/header 不一致。
- 直接复用 Stage 3 `CreationToken`、`StableNodeRef`、`StableNetRef` 与 `DesignEditPlan`；trace 不保存 dense ID、native rank、pointer 或 session-local object。
- replay 投影不包含 selector operands、gain/slack/load receipt或 expected timing；篡改 generation-only evidence 不改变 replay 语义。
- 两批 synthetic trace 覆盖 existing net 插入，以及 batch 2 继续分裂 batch 1 的 created output net，证明 created→created resolver和 reverse 一删一增 contract。

### 2.3 One-shot production replay

- `FreshBaselineRunner::withFreshBaseline` 是唯一入口；stack-only `BufferReplayContext` 不能复制、移动、堆构造或逃逸 callback。
- adapter 在同一 production loader callback 与 OperationGuard 内完成 baseline capture/release、coordinator、translate、native full、CSR full proof、seal 与 publish；opaque proof不返回、不缓存、不序列化。
- process-local one-shot 状态为 `unused→entered→finished`。同一进程第二次调用在 artifact、IDM、STA 与 loader 之前得到 `fresh_process_reuse_rejected`，loader invocation count仍为1。
- controller 对 generation、每个 prefix和重复证据分别启动新 child；PID、loader count与one-shot state只进入 noncanonical run envelope，不参与 trace equality。

### 2.4 Source 与停止语义

- synthetic 每次物化 distinct tech LEF、cell LEF、Liberty、Verilog、SDC 五个 regular files；real trace读取同样五类 source refs。
- preloader负例覆盖五个 role逐一缺失，以及 cell LEF symlink canonical-alias 到 tech LEF；六个 case都在 loader/work 之前 typed reject并证明原 source bytes不变。相同字符串路径 alias另由 contract/schema层拒绝。
- 首轮空接受不是合法 zero-batch trace：production negative-gain路径返回 `kInvalidArtifact`，generation保持0、coordinator保持Idle、无 execute/publish且source不变。
- 已有一批后的 terminal empty 是合法停止：结构性 guard branch使 round 1唯一正收益 `target:A` 被接受，round 2的四个 critical nets共有五个非正收益候选；created output net是唯一正收益但明确为 `non_critical_net`。critical slack与它保持大于1ns裕量，不依赖浮点末位或摘要排序。

## 3. 论文规则与工程定义

| 项目 | 论文给定 | ECC Stage 4 冻结 |
|---|---|---|
| critical selection | 按 slack 选 critical nets | setup max slack升序，semantic net/driver bytes确定性 tie-break |
| 实验轮廓 | top-1000×1、top-100×10、buffer-count sweep | protocol-only profiles；小 fixture使用 `engineering_smoke`，不冒充论文规模 |
| insertion | 在候选 pin前插 buffer | single-driver data net、单 sink move、每网每批最多一个、冲突整批reject |
| gain | Elmore近似收益 | 版本化 RC/operating point、实际 Liberty capacitance/table lookup、binary64固定顺序 |
| rounds | 每轮修改后重新评估 | 每个非空 batch后完整 native CPU/full重算；空批、轮数、总量分别记录stop reason |
| randomness | 未冻结 | selector无随机分支；real seed为0，synthetic seed只进入token/trace |
| replay identity | 未给出 | Stage 3 stable refs/creation token、strict schema、fixed semantic edits |
| correctness | 未给出仓库验收口径 | native↔CSR逐字段、fresh child一致、source Database/IDB不变 |

## 4. Trace、profile 与可比性

冻结输入位于：

- `src/operation/iSTA/test/timing_edit/traces/synthetic_two_batch.json`；
- `src/operation/iSTA/test/timing_edit/traces/real_buffer_fanout.json`；
- `src/operation/iSTA/test/timing_edit/traces/manifest.json`；
- 对应 templates位于 `traces/templates/`。

两条冻结主trace的as-built规模为：

- `synthetic_two_batch`：seed 42，2 batches/3 edits；batch 1为1 edit及16 forward+16 reverse semantic operations，batch 2为2 edits及32+32，并继续分裂batch 1的created output net；
- `real_buffer_fanout`：seed 0，1 batch/4 edits及64+64 operations，依次移动 `y0→u4:A`、`y1→u4:B`、`y2→u5:A`、`y3→u5:B`。每个edit物化一个buffer和一个output net。

schema version为 v1。`paper_protocol_top1000_x1` 与 `paper_protocol_top100_x10` 只声明 `protocol_only`；两条冻结主trace均使用 `engineering_smoke`，固定为 `non_comparable/engineering_rc_no_physical`。工程 RC只参与 selector近似，STA timing仍由实际 Liberty、pin capacitance和full analyzer产生。

完整性字段保留用于确认读取了同一冻结 artifact，不作为 timing、topology、source unchanged或fresh一致性的替代证明。

## 5. 功能证据

每个成功 batch和prefix均验证：

- semantic edit、creation token、original/created net、moved sink与reverse一删一增；
- native Database的design、instances、pins、nets与derived freshness；
- host CSR/reference input的nodes、arcs、adjacency、FIFO、order/level、electrical closure与CPU/full↔CSR full timing逐字段相等；
- generation与full-prefix replay的功能receipt相等；两条冻结主trace的每个prefix均由三个独立fresh child逐字段比较；
- source role、logical/canonical path、size与exact bytes不变；
- primary IDB design、instance/master/type/status/orient/location、pin/net连接、wire/segment/layer/point/via/rect投影与计数不变；可选logical view同样不变且无SPEF。

derived-tamper测试先破坏隔离 candidate 的派生 timing，再由full rerun恢复；parasitic boundary精确返回 `full_with_record`且没有apply/execute/publish。以上证据来自功能对象和typed lifecycle receipt，不来自摘要值。

## 6. 独立审查与修正

详细计划先处理 callback lifetime、五件distinct source artifact和one-shot fresh process三项阻断，独立设计审查最终 `APPROVE`。

实现期独立只读审查推动并复核了以下修正：

- paper profile跨批 created-net引用改为完整 creation token，并补齐profile/role/ordinal负例；
- observation fixture的sink/net/arc/timing point全部重键到一致身份并先通过 native Database validator；
- parasitic boundary改为真实 analysis context，分别验证translator policy与coordinator零写入；
- Stage 4 inventory区分 runtime direct依赖与Stage 3 frozen target的传递闭包；
- first-empty typed error不再被OperationGuard字符串化，adapter在loader关闭与source检查后重抛原类型；
- terminal fixture先移除 clock-tree fanout，再增加真实 guard timing branch，消除约1 ULP的top-k边界依赖；
- Ninja dependency database经recompact后，Stage 4 exact object/depfile/nm inventory恢复并通过。

最终代码审查结论为 `APPROVE`，无 blocker、major或minor。所有 Stage 4 新文件严格少于700物理行；两个最大文件均为699行。source tree无 `.orig`、`.rej`、`__pycache__` 或 `.pyc` 泄漏。

## 7. 正确性与回归结果

| 门禁 | 结果 |
|---|---|
| Stage 4 `^ista_buffer_` | 20/20 PASS |
| Stage 4 unit/property/integration/smoke | 14/14、5/5、6/6、2/2 PASS；labels有重叠 |
| Stage 3 `^ista_timing_edit_` | 16/16 PASS |
| Stage 2完整 `^ista_csr_` | 74/79功能/真实流程通过；5项历史静态门见下文 |
| parent 12个冻结STA pytest | 227/227 PASS |
| parent non-PDK pytest | 1665 passed、8 skipped、4 deselected、13 xfailed、2 warnings；无失败 |

Stage 2剩余5项不属于功能失败：Step 5、Step 4 isolation、Step 6和Step 8 inventory各因共享 Ninja `.ninja_deps` 缺少一个旧对象记录失败；Step 7 inventory仍冻结Stage 2时代的全局 `unit/property/smoke=87/20/7`，而当前目录已合法新增Stage 3/4 tests。binding contract在匹配构建时Python 3.11 runtime后通过，real differential fresh-process、projection fresh、reference input、scatter与session功能路径均通过。按总体验收优先级，这5项单独记录，不通过改摘要或旧数量常量掩盖。

Stage 4完整20项本轮约4秒；真实 replay的fresh隔离来自独立进程退出，不宣称loader可在同一进程重置全局IDM/DataManager，也不把该时间解释为增量speedup。

## 8. 用户可见行为、配置与提交边界

没有新增parent Python用户API，也没有改变默认STA运行模式。child新增两个内部library、一个build-only production probe、20个CTest和strict schema/fixtures；`src/operation/iSTA/CMakeLists.txt` 与test CMake只负责注册这些边界。

阶段提交按仓库边界分两步：child只含Stage 4 source/test/fixtures；parent只含更新后的submodule gitlink、`stage4-detailed-plan.md`、本报告和总体计划状态。用户已有 `CLAUDE.md` 与 `stage1-stage2-meeting-report.md` 保留且不纳入提交。没有push。

## 9. 已知限制与下一 gate

- 仅支持组合逻辑、single-driver、单sink move的buffer insertion；不支持任意删除、general existing→existing edit或物理IDB提交。
- selector的engineering RC不等于真实物理RC；当前real trace明确 `non_comparable`。
- 每批仍运行native CPU/full与CSR full，没有Dual-CSR、mixed levelization、CUDA或speedup结论。
- fresh证据依赖one-shot child process；同一进程重复loader被主动拒绝。
- 真实parasitic与placement-bound edit仍为typed boundary，不冻结成功trace。

Stage 5只能消费本阶段冻结的 replay-safe semantic edits。进入前必须继续保持：不读取generation-only答案；以同一fixed trace比较full与Dual-CSR；失败不污染published state；正确性仍以topology、电气量、timing与fresh replay逐字段一致为主。
