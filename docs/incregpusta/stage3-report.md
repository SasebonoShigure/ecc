# 阶段 3 完成报告：结构编辑事务与 fresh CPU/full oracle

> 当前开发协议补充（开发检查分离）：CsrExecutionAuthorization 将受控提交授权与 full-exact 证明分开，OFF 无完整证明；generation、身份和原子提交/真实回滚始终检查。 后续改动必读 [开发检查规范](development-guidelines.md)，双模式实测与历史验收的区别见 [本轮实施报告](debug-checks-implementation-report.md)。原阶段验收数字保留为历史记录。

> 状态：Stage 3 功能实现、独立复审与定向验收完成；本地 child/parent 提交待按阶段边界封存
> 日期：2026-08-31
> 基线：parent `49f1bc99ed8a4126a6f4da2bfd3236cdb04df4e9`，ecc-tools `5609a3c932e7bcb6cfb2a2ee765f472e0615e395`
> 范围：generation-bound semantic buffer insertion、isolated native full recompute、CSR full proof、原子发布、fresh replay/recovery；不含 Dual-CSR、CUDA 或物理 IDB 提交

## 1. 结论

阶段 3 已建立可执行的三层结构编辑路径：跨 session 稳定的 `DesignEditPlan` 被规范化为不可变、可逆、generation-bound 的 `PreparedBatch`；候选编辑只在 detached raw Database 上展开并完整重建原生 timing graph；native CPU/full、CSR full 与 committed identity 全部验证通过后，coordinator 才以单一 no-throw ownership exchange 发布。

支持边界固定为组合逻辑、单 driver、data-only、无 active cycle 的两端口非反相 buffer insertion。clock/sequential、真实 parasitic、placement-bound、未知 execution mode/failpoint、numeric/collision/capacity 等越界输入均以 typed error 或明确 `full_with_record` 分类处理，不静默 fallback。

本阶段不声称增量性能。candidate execution 仍运行 GraphBuilder、DelayCalculator、ClockPropagator、TimingPropagator 与 TimingAnalyzer 的完整 CPU/full 流程；`cpu/incremental`、`gpu/full`、`gpu/incremental` 仍为 typed unsupported。

验收以功能逐字段一致为主。trace/hash 只用于标识输入 artifact 与定位差异；完成结论来自 raw Database closure、resolver、cumulative semantic trace、host CSR、native timing 与 CSR full result 的 exact equality，以及多个 fresh process/session 的累计 prefix 重放。

## 2. 已交付功能

### 2.1 Stable typed contract

- `StableNodeRef`、`StableNetRef`、`StableArcRef` 与 Stage 3 creation token，不持久化 dense ID、native rank、pointer 或 Database reference；
- `DesignEditPlan -> normalized forward/reverse delta -> PreparedBatch`，reverse 对每个 moved sink 保持一删一增且 append-only slot 不复用；
- move-only `PreparedBatch`，只有 coordinator verify 后可 friend-only seal，未 seal batch 不能 publish；
- closed-world `timing-edit-trace/1.0.0` JSON/schema，拒绝 duplicate key、unknown field/version、非 finite 数值与未知 policy disposition；
- exact canonical pre/post identity、六 component fingerprints 与 trace baseline identity。

### 2.2 Native candidate 与 deterministic graph rebuild

- raw clone只复制 design/library/constraint/parasitic inputs，并统一清空 Arc、adjacency、order、level、timing point与其他 derived state；
- translator只修改 raw Instance/Pin/Net membership，完整 cell/net arc由生产 GraphBuilder重建；
- exact buffer closure要求一个 data input、一个 output、恒等 Boolean function及 positive-unate graph timing arc；
- moved sinks/source net均受 data-only、single-driver、clock/sequential和active-cycle边界约束；
- `GraphBuilder::makeNetDriverLoad()` 对派生 driver/load cache按 full semantic name排序，raw `Net.pin_name_list` 顺序保持不变，使 input permutation不改变 native arc/FIFO/CSR正式字段；
- trace closure用同一规范序从 raw membership派生并 exact compare，non-lexical raw net不会被误拒。

### 2.3 Transaction、proof 与 failure atomicity

- `TimingEditCoordinator` 固定 prepare→stage→execute→verify→seal→publish/rollback 状态机；
- `NativeExecutionAuthority` 绑定 session token、owner thread与 single OperationGuard，copy/move/跨线程/guard外使用均 fail closed并 poison session；
- candidate install与 canonical Database交换由唯一 rollback owner持有，precommit任一错误精确恢复 generation g；
- `CsrFullExactReceipt` 是 opaque move-only full-result proof，绑定 active token、target generation、canonical reference bytes 与完整 `CsrTimingResult`；
- publish/recovery重新从 active Database构建 host snapshot、运行完整 CSR CPU/full并消费 proof；空、moved-from、旧 context或错误 generation receipt在首写前拒绝；
- commit boundary后的 no-throw latches必须完成整个 g+1安装再 poison，observer永不看到混合 generation。

### 2.4 Fresh oracle 与 recovery

- production lane使用真实 artifact loader、single guard、Stage 3 translator/candidate/coordinator；
- independent lane只共享 trace schema/types与 Stage 2 comparison，自行解析 token并直接修改 raw Instance/Pin/Net，不调用 production resolver/translator/native transaction；
- 每个 cumulative prefix在新进程从 baseline artifact重新初始化，production/independent逐字段比较 raw topology、adjacency/order/level、electrical load、delay/slew、arrival/required/slack/path state；
- deliberate wrong-sink self-test由独立 oracle稳定发现；derived timing tamper在 prepublish full-exact gate拒绝并精确回滚 g0；
- poison后的 fresh recovery关闭旧 session，从独立 g0基线重放 durable trace并安装 exact recovered Database/host CSR/resolver/identity。

## 3. 关键实现边界

新增生产 target：

```text
ista_timing_edit_contract
  Database-free semantic types / validation / canonical trace

ista_timing_edit_native
  raw candidate / resolver / translator / native full execution / trace closure

ista_timing_edit_transaction
  coordinator / transaction state / opaque full-exact receipt
```

`ista_timing_edit_transaction` 的 direct link inventory只包含 contract、native与CSR graph adapter；transaction source scan明确禁止 `STAInterface.hpp`、`IncrementalStaSession.hpp`、IDM、iZH 与 CUDA。native复用既有 DataManager/full-timing stack，其 legacy transitive closure会带入 `ista_interface/ista_source`；这是已记录的既有依赖，不冒充新增 direct dependency。transitive gate仍拒绝 `py_ista`、`idm`、iZH和CUDA。

生产 API没有新增公开 batch入口。真实测试只通过 test-only `StaTimingEditSessionProbeAccess` 在既有 `IncrementalStaSession` 的一个 OperationGuard callback内运行完整事务；authority、Database reference、session context和receipt borrow均不得逃逸。

阶段 2 core/snapshot/adapter的 source inventories与 frozen schema未增加 Stage 3 production source。唯一跨阶段生产行为调整是 GraphBuilder派生 net cache确定性排序；raw membership、API和schema不变。

## 4. 审查与修正

Stage 3详细计划经过独立审查并获 `APPROVE`。实现复审先后发现并关闭：receipt必须绑定完整 CSR timing result；跨线程authority逃逸；fresh recovery不能复用伪 snapshot；receipt负例必须真正越过前置 gate；DAG input permutation导致的GraphBuilder load-order nondeterminism；以及排序后trace closure的同步规范化。

最终独立复审结论为无 blocker。复审确认 receipt mismatch、fault/poison、fresh recovery、property、exact CMake inventory与 formal target source/link均闭合；GraphBuilder修复后再次执行 Stage 2 projection/scatter/real differential/full baseline兼容审查，无功能回归。

Stage 4计划另经独立阻断审查，修正为 callback-scoped stack-only replay context、五件 distinct source artifacts与one-shot fresh process，最终结论 `APPROVE`。Stage 4不得修改本阶段 core、receipt、probe或loader权限边界。

## 5. 正确性结果

最终 Stage 3 CTest：

| 门禁 | 结果 |
|---|---|
| `^ista_timing_edit_` | 16/16 PASS |
| unit/contract/resolver/native/transaction/guard | PASS |
| receipt mismatch、unknown failpoint、rollback poison | PASS |
| fresh recovery | PASS |
| fixed-seed DAG/prepare property | PASS |
| source/oracle isolation inventories | PASS |
| independent wrong-sink self-test | PASS |
| fresh production↔independent oracle | PASS |
| production derived-tamper rollback | PASS |

DAG property覆盖 singleton、chain、diamond、multi-root、parallel、disabled、loop-disabled × seeds `1,7,42,20260831,0xdeadbeef`，并覆盖 active cycle与malformed adjacency typed reject。non-lexical diamond额外证明 raw membership不变、派生cache规范化且exact trace closure可接受。

Stage 2最小真实兼容路径 33/33 PASS，覆盖 graph export/encoding、CPU reference、reference input、scatter、projection fresh、real differential fresh与full baseline。共享 build目录的完整79项复跑中，补齐 matching `PYTHONHOME` 并登记两个Stage 3合法新增调用点后74项功能/真实流程通过；余下5项中4项是共享Ninja依赖数据库记录缺失，1项是旧的全局测试数量冻结，未出现 topology/timing/scatter/fresh differential功能失败。按总体验收原则，这些构建/静态门问题单独修复或记录，不以旧SHA/数量常量否定已重复证明的功能结果。

parent 12个冻结STA定向 pytest 为227/227 PASS；non-PDK全量为1665 passed、8 skipped、4 deselected、13 xfailed、2 warnings，无失败。与阶段2记录相比少2个pass、增加2个skip，属于当前环境的可选依赖跳过，功能用例无回归。

## 6. 已知限制

- 仅支持 buffer insertion；不支持任意 node deletion、general existing→existing edit或物理IDB提交；
- 每批仍执行native CPU/full与CSR full，不提供Dual-CSR、mixed levelization、CUDA或speedup；
- production batch API仍为test-only guarded seam，未来公开消费者需单独设计无环权限入口；
- native full-timing target仍继承 legacy `ista_interface/ista_source` transitive closure；
- shared Ninja build曾因并发构建产生dep database截断，功能二进制与fresh回归有效，strict depfile inventory需在干净/串行build复核；
- artifact SHA只用于身份辅助，不作为正确性结论。

## 7. Stage 4 gate

Stage 4只消费本阶段已冻结的 semantic edit、candidate、coordinator和full-exact proof能力。它必须：

1. 在独立one-shot probe进程中调用一次 production fresh loader；
2. 在同一 loader callback/OperationGuard内同步消费proof并publish；
3. synthetic生成distinct tech LEF、cell LEF、Liberty、Verilog、SDC五件artifact，real与synthetic共用同一loader；
4. 以CPU/full与CSR full逐字段一致、三个fresh进程重放一致及source EngineDB/IDB不变为完成条件；
5. 不修改Stage 3 core或放宽authority/context生命周期。
