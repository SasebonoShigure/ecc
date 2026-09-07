# ECC IncreGPUSTA 阶段 3 详细实施计划

> 当前开发协议补充（开发检查分离）：CsrExecutionAuthorization 将受控提交授权与 full-exact 证明分开，OFF 无完整证明；generation、身份和原子提交/真实回滚始终检查。 后续改动必读 [开发检查规范](development-guidelines.md)，双模式实测与历史验收的区别见 [本轮实施报告](debug-checks-implementation-report.md)。原阶段验收数字保留为历史记录。

> 状态：v1.0 as-built；独立计划审查与代码复审均通过，功能实现和 Stage 3 定向验收完成
> 基线：parent `49f1bc99ed8a4126a6f4da2bfd3236cdb04df4e9`，ecc-tools `5609a3c932e7bcb6cfb2a2ee765f472e0615e395`
> 分支：parent 与 ecc-tools 均为 `IncreGPUSTA`
> 范围：三层 typed edit contract、native shadow Database、事务 coordinator、fresh CPU/full oracle、四模式 harness 骨架；不实现 Dual-CSR、CUDA 或物理 IDB 提交
> 验收原则：以可重复的功能正确性和回归一致性为主；哈希只用于 trace/基线身份与证据完整性，不以哈希攻防替代结构、电气和 timing 的逐字段比较

## 1. 阶段目标

阶段 3 在阶段 2 已冻结的 native↔CSR/full-reference 边界之上，建立真正可执行的结构编辑事务。输入是跨 session 稳定的语义编辑，输出是当前 session 可执行、可逆、generation-bound 的 prepared batch。每个 batch 必须在隔离候选 Database 中完成原生图重建、全量 timing 执行、CSR full reference 和 fresh-session 累计重放核验，验证通过后才允许以单一 no-throw ownership exchange 发布。

本阶段证明的是编辑语义、原生图一致性和失败原子性，不证明增量性能。所有候选执行仍是 full recompute；未实现的 `cpu/incremental`、`gpu/full`、`gpu/incremental` 必须返回 typed unsupported，不得静默回退或冒充完成。

## 2. 非目标与禁止事项

- 不修改 EngineDB、IDB、placement、DEF、SPEF 文件或 iZH 物理对象；
- 不调用或链接 iZH `FanoutFixer`；
- 不实现论文 Dual-CSR、affected cone、局部 levelization、GPU kernel 或 device allocator；
- 不放宽阶段 2 `CsrSnapshotIdentity.graph_generation == 0` 的 committed snapshot 合同；
- 不把 dense `NodeId`、`ArcId`、native vector rank 或裸指针写入持久 trace；
- 不默认复制带派生 Arc 的 Database 后继续使用复制来的 `Arc::_timing_cell_arc`；
- 不直接在 canonical Database 上分散修改 Instance/Pin/Net/Arc/adjacency；
- 不把 `CsrSnapshotObservation` 当 rollback/checkpoint；
- 不修改阶段 2 已冻结 core/snapshot/adapter/interface source inventory；
- 不用 graph hash、trace hash 或构建树哈希代替功能 equality；
- 不向超过约 700 行的既有大文件继续堆事务逻辑。

## 3. 已核验现状与关键约束

### 3.1 可复用边界

- 阶段 2 `NodeKey`、`ArcKey`、canonical encoder、六 component fingerprint、CSR full backend 与 scatter 原子发布范式继续作为唯一语义编码和 full reference；
- `exportCsrReferenceInputCandidate(const Database&)` 保持只读；
- `real_differential` 的 fresh-process 双 lane 组织方式可复用，但阶段 3 新建独立 manifest/controller，不修改冻结 fixture；
- `STAInterface` 已有 owner lease 与 operation mutex；真实 probe 必须在该 guard 内执行整个 candidate transaction；
- `GraphBuilder` 与 delay/propagator/analyzer 通过 `STADM.getDatabase()` 读取 active Database，因此 detached value-model 不能替代真实 native 执行。

### 3.2 必须闭合的问题

- `Database` 当前按值持有；阶段 3 需要受限、noexcept 的 `unique_ptr<Database>` ownership exchange；
- `GraphBuilder::build()` 假设派生容器为空，mutation rebuild 前必须清空 arc、adjacency、timing point、start/end、order、path/report/power 派生状态；
- `Arc::_timing_cell_arc` 指向当前 Database 的 TimingLibrary vector 成员，candidate 必须复制 raw inputs 后从空派生图重新 build，让指针绑定到 candidate 自身 library；
- singleton 审计确认 GraphBuilder、ClockPropagator、TimingPropagator、TimingAnalyzer 不持久缓存 Database 地址；`DelayCalculator` 同时持有跨调用寄生 cache 和 `TimingArc* _timing_arc`，其 runtime `destroy()` 不会清空裸指针，因此每次换库前、回滚前和释放任一 Database 前必须 `DelayCalculator::destroyInst()`，换库完成后再 `initInst()`；
- candidate pipeline 必须是 operation guard 内部入口；不能递归调用 `STAInterface` 公开操作，也不能复用包含 power/report/SDF 外部输出的完整 `runFullStaPipeline()`；
- 当前 `ArcKey.parallel_ordinal` 在删除后会重排，只能表示单个 snapshot 的 key，不能作为跨 generation 生命周期 identity。

## 4. 模块与依赖边界

新增独立目录与 target，不把源文件追加到阶段 2 冻结 target：

```text
source/module/timing_edit_contract/
  TimingEditTypes.hpp
  TimingEditValidation.{hpp,cpp}
  TimingEditCanonicalEncoding.{hpp,cpp}
  TimingEditTrace.{hpp,cpp}
  CMakeLists.txt

source/data_manager/adapter/timing_edit/
  TimingEditResolver.{hpp,cpp}
  NativeDesignEditTranslator.{hpp,cpp}
  NativeDatabaseCandidate.{hpp,cpp}
  CMakeLists.txt

source/module/timing_edit_transaction/
  TimingEditCoordinator.{hpp,cpp}
  TimingEditOracle.{hpp,cpp}
  TimingEditRecovery.{hpp,cpp}
  CMakeLists.txt

test/timing_edit/oracle/
  IndependentFreshBaselineLoader.{hpp,cpp}
  IndependentSemanticReplayer.{hpp,cpp}
  IndependentFreshOracleProbe.cpp
test/TimingEditTests.cmake
benchmark/schema/timing_edit_trace_v1.schema.json
benchmark/schema/validate_timing_edit_trace.py
```

Target关系：

```text
ista_timing_edit_contract
  PUBLIC -> ista_timing_csr_core
  Database-free

ista_timing_edit_native
  -> ista_timing_edit_contract
     ista_timing_graph_csr_adapter
     ista_timing_database_headers
     ista_data_manager                 # direct，承载受限 exchange friend

ista_timing_edit_transaction
  -> ista_timing_edit_contract
     ista_timing_edit_native

ista_timing_edit_independent_oracle   # test-only
  -> ista_timing_edit_contract
     ista_timing_graph_csr_adapter
     ista_timing_database_headers
     graph/delay/clock/timing/analyzer targets
     ista_interface
     ista_source
     idm
  禁止 -> ista_timing_edit_native / ista_timing_edit_transaction
```

`IndependentFreshBaselineLoader` 是上述 oracle target 内唯一允许使用 interface/source/IDM/CSR-adapter 依赖的窄层，只负责从真实 baseline artifacts 创建 fresh Database/session并完成原生基线分析，不解释或应用任何 semantic edit。其输出交给同 target 内的 `IndependentSemanticReplayer`；后者必须自行翻译 typed trace并直接修改 raw Instance/Pin/Net，不能调用 production resolver/translator。CMake source/link inventory 要冻结 oracle 的完整 transitive closure，明确禁止 `ista_timing_edit_native`、`ista_timing_edit_transaction` 及其 resolver/translator 源文件；真实 artifacts fresh-baseline 启动测试同时证明 loader 路径可用且 production edit target 未被带入。

Stage 3不新增公开 batch API。真实probe通过新增的 test-only `StaTimingEditSessionProbeAccess` friend seam，一次调用 private `acquireUse()`取得session owner `OperationGuard`，同一个callback覆盖prepare→install→execute→verify→publish或rollback；callback内不得递归调用公开STA操作。`IncrementalStaSession`只向该friend提供当前token/context，不把Database引用带出guard。并发操作阻塞在operation mutex，无法观察candidate。

`ista_timing_edit_transaction`不直接链接`ista_interface`/`ista_source`，由测试probe在已取得guard后调用；其 exact direct-link inventory 与全部 transaction source scan 是本阶段的隔离门禁。`ista_timing_edit_native`复用既有 DataManager 与 full-timing stages，当前 legacy transitive closure 会经 `ista_toolkit` 带入 `ista_interface`/`ista_source`；本阶段如实记录该限制，不把它误报成新增直接依赖，也不为消除名字而拆散既有 timing 栈。transitive closure 仍禁止 `py_ista`、`idm`、iZH 与 CUDA。未来生产batch API必须另行设计无环依赖并重新审查。本阶段对既有生产文件的最小修改限于：DataManager改为`unique_ptr<Database>`并向`NativeDatabaseCandidate`提供private noexcept exchange；GraphBuilder候选重建清理；必要的test-only friend seam。阶段2 core/snapshot/adapter/interface source inventory不追加源文件。

## 5. 三层 typed contract

### 5.1 DesignEditPlan

首版唯一supported semantic edit是组合逻辑buffer insertion；其他编辑显式`error`或`full_with_record`。

```cpp
struct CreationToken {
  std::uint32_t schema_version{1};
  std::string case_id;
  std::string profile_id;
  std::uint64_t seed;
  std::uint64_t batch_ordinal;
  std::uint64_t accepted_ordinal;
};

struct BufferInsertionMutation {
  StableNetRef original_net;
  std::vector<StableNodeRef> moved_sinks;
  LibraryCellRef library_cell;
  PlacementInputs placement_inputs;
  RcInputs rc_inputs;
  CreationToken creation_token;
};

struct DesignEditPlan {
  std::string schema_version;
  BaselineSemanticIdentity baseline;
  TransactionGeneration expected_generation;
  std::vector<BufferInsertionMutation> edits;
};
```

`BaselineSemanticIdentity`永久描述batch 0原始设计；trace只存semantic refs/token，不存session token、dense ID、native rank或pointer。

### 5.2 TimingGraphDelta

每个buffer insertion精确展开为`AddInstance`、input/output `AddTimingPoint`、全部Liberty graph `AddCellArc`、original driver→buffer input `AddNetArc`，以及每个moved sink的一对`RemoveNetArc`/new driver `AddNetArc`、`ReconnectSink`、`InvalidateLoad/Parasitic/ArcDelay`。delta是normalize前语义操作，不保存Database pointer；input排列不得改变canonical delta。

### 5.3 Evolving identity 与 PreparedBatch

```cpp
struct CommittedEditIdentity {
  TransactionGeneration generation;
  ComponentFingerprints current_fingerprints;
  CanonicalPreStateEvidence canonical_pre_state;
};
```

`BaselineSemanticIdentity`与`CommittedEditIdentity`严格分离。每次prepare在任何写入前重新export active Database并逐字段核对current identity，既检测stale generation，也检测generation不变的外部篡改。Stage2 `CsrSnapshotIdentity.graph_generation`继续固定0；transaction generation是sidecar strong type。

`PreparedBatch` move-only、外部只读，包含nonzero session token、expected/target generation、永久baseline identity、`expected_pre_committed_identity`、normalized forward/reverse、stable ref→append-only slot、high-water ranges、token materialization、invalidation closure和policy receipt。coordinator在verify阶段以friend-only `seal()`预计算并安装`target_post_committed_identity`；未seal batch不能publish。所有canonical strings/receipts在publish前分配。

transaction层另持有`VerifiedPublishBundle`：active candidate Database、候选`CsrCommittedSessionSnapshot`、sealed PreparedBatch、累计trace（含当前batch）、resolver/current identity和device state。它不是pure contract的一部分。PreparedBatch一次性、session/generation-bound；跨session、重放、乱序、baseline/current mismatch均首写前拒绝。

## 6. Stable identity 与 append-only ID

### 6.1 对象引用

```text
StableNodeRef = ExistingNodeRef{baseline NodeKey}
              | CreatedNodeRef{CreationToken, role=input|output}

StableNetRef  = ExistingNetRef{baseline net name}
              | CreatedNetRef{CreationToken, role=output_net}

StableArcRef  = ExistingArcRef{baseline ArcKey}
              | CreatedCellArcRef{token, library source/sink ports,
                                  ordered LibraryArcSignature set,
                                  stable equivalence ordinal}
              | CreatedOldNetArcRef{net ref, driver ref, sink ref, stable ordinal}
              | CreatedNewNetArcRef{token, driver ref, sink ref, stable ordinal}
```

所有baseline `ExistingArcRef`在session建立时一次性解析并绑定slot；后续generation绝不以已重排的current `parallel_ordinal`重新解释它。CreatedCellArcRef的equivalence ordinal来自原始Library cell arc canonical order，不用native rank；相同端点、相同signature的parallel cell arcs仍唯一。Created net arc按token/net/端点/稳定ordinal区分。删除形成tombstone，slot不复用；新对象只追加。

### 6.2 Creation token materialization

token是结构化tuple，不用随机串、pointer或process static counter。默认materialized names为`__ista_buf_b<batch>_e<accepted>`、`__ista_net_b<batch>_e<accepted>`与`<instance>:<liberty-port>`；name只用于当前Database，跨session identity仍是token。prepare预检token/name collision、前向引用、同批冲突、existing歧义和capacity overflow。

## 7. Native candidate 与原生重建

### 7.1 Raw-input clone

`NativeDatabaseCandidate::create()` 从 canonical Database 复制 raw design inputs：design name、Instance、Pin、Net、TimingLibrary、TimingConstraint、ParasiticLibrary 以及 full run 必需配置数据；随后由唯一 `resetDerivedState()` 显式清空：

- `arc_list`、outgoing/incoming adjacency；
- `timing_point_map`、start/end/order；
- `timing_path_group_list`；
- timing analyzer summary（至少 `ta_summary`）以及本阶段不保留的 report/power derived state。

任何复制来的 Arc 和 raw `TimingCellArc*` 在 build 前销毁。GraphBuilder/full timing 完成后、verify 之前必须检查：

- 每个 cell Arc 的 `TimingCellArc*` 都落在 candidate 自身对应 TimingLibrary cell 的成员地址集合中；
- 每个 net Arc 的 `TimingCellArc* == nullptr`；
- outgoing/incoming 的全部 arc index、TimingPoint predecessor index和全部 TimingPathState predecessor index均在 candidate arc vector 范围内或为规定的 absent sentinel；
- timing point key集合与 Pin key集合 exact相等，旧 endpoint/path group/summary没有残留。

Translator 只修改 candidate 的 Instance/Pin/Net raw inputs，不直接构造最终 Arc/adjacency/timing order。它完成：

- 校验 combinational library cell，唯一 input/output port 或显式合法 port pair；
- 新 instance 与 pins 建立双向 membership；
- original net 移除 moved sinks、加入 buffer input；
- 新 net 以 buffer output 为 driver并接入 moved sinks；
- 每个 Pin.net、Net.pin list 和语义 token map 一致更新；
- parasitic 存在而当前 mutation 无法可靠 split 时按 policy `error` 或 `full_with_record`，不伪造 RC。

### 7.2 Candidate execution

在持有 `STAInterface` operation guard 时：

1. 在旁路创建 candidate并执行 `resetDerivedState()`，不让任何 `Database&`、内部 pointer、iterator或 vector index逃出 operation作用域；
2. 幂等销毁 transient singleton：TimingAnalyzer → TimingPropagator → ClockPropagator → GraphBuilder；
3. 对当前库执行 `STADC.destroy()`，随后 `DelayCalculator::destroyInst()`，保证没有 cache/`_timing_arc` 指向即将换出的库；
4. DataManager 以 noexcept `unique_ptr` exchange 临时安装 candidate；旧 canonical Database 由 rollback owner持有；
5. `DelayCalculator::initInst()`、`STADC.init()`，再以逐阶段 RAII 守卫依次运行 GraphBuilder → ClockPropagator → TimingPropagator → TimingAnalyzer；每一阶段都严格 init/work/destroy；
6. GraphBuilder从 raw inputs重建 timing points、cell/net arcs、双向 adjacency、start/end、loop policy、order和level；后三阶段从 library/constraint/RC重新计算 load、delay、slew、arrival、required与slack；
7. verify完成后，先逆序销毁 transient singleton，再执行 `STADC.destroy()` 与 `DelayCalculator::destroyInst()`；
8. 任一 publish前失败均在 candidate仍存活时完成上述 cleanup，再 noexcept exchange回旧 Database；成功则保留candidate；只有换库结束后才能释放未采用的 Database；
9. 无论成功或回滚，最后 `DelayCalculator::initInst()` 恢复 production session的持久单例；下一次 timing pipeline自行调用 `STADC.init()`；
10. verify成功且 cleanup/exchange lifecycle完整后才进入publish。

该顺序是编码合同。内部 candidate executor只运行 timing所需四阶段，不运行 power、reporter或SDF，不递归调用已持锁的公开 `STAInterface` 操作。对 singleton init/work/destroy、DelayCalculator完整销毁、candidate install和rollback逐点注入异常，均必须证明 cleanup完成且没有悬空引用。

## 8. 事务状态机、三侧发布与恢复

下图的 `Idle/Prepared/.../Poisoned` 是 `TimingEditCoordinator` 状态；真实 `IncrementalStaSession::_state` 继续只使用既有 `StaSessionState::{kCreated,kInitialized,kBaselineExecuted,kPoisoned,kClosed}`。`g` 不属于 session enum，而只由 `CommittedEditIdentity.generation` 与 commit marker 表示。

```text
Idle(g) -> Prepared -> Staged -> Executing -> Verified
Verified -> precommit checks -> noexcept commit boundary -> complete Published(g+1) -> Idle(g+1) | Poisoned(g+1)
publish前失败 -> rollback Database/host state -> Idle(g)
commit boundary后故障latch -> 完整安装g+1后Poisoned(g+1) -> close old session -> fresh recover(g+1)
```

### 8.1 Host/device ownership

coordinator独占mutation generations的current host full-CSR snapshot。首次mutation前，旧`StaCsrSessionContext` snapshot必须显式invalidate/release，禁止把mutation前snapshot继续标为ready；之后每个candidate verify都调用Stage2 snapshot builder生成新的`CsrCommittedSessionSnapshot`。device CSR在Stage3固定为typed `not_materialized(stage_not_implemented)`并带target transaction generation；publish不得遗留旧device generation或伪造device buffer。

### 8.2 唯一 publish point

`VerifiedPublishBundle`在commit前已经持有：active且验证通过的candidate Database、完整host snapshot、sealed post identity、resolver high-water状态、累计trace（已含当前batch）、device-not-materialized descriptor、全部receipts以及预分配的commit marker/fault latch。所有可能抛异常、分配内存或执行可重入回调的工作必须在commit boundary前完成；`publish-before-commit` 是最后一个可中断failpoint，命中时仍按g回滚。

唯一commit boundary位于下列step 1之前。跨过它以后，同一OperationGuard内只能执行经static/noexcept检查的move/swap/state primitive；不得抛异常、分配、调用用户callback或提前return，并且必须无条件走完全部步骤：

1. dismiss旧Database rollback ownership，使candidate成为canonical；
2. swap current host snapshot；
3. install transaction generation/trace/resolver/post identity；
4. install同generation的device-not-materialized状态；
5. 设置预分配的 `commit_marker=complete(g+1)`；
6. 若commit fault latch为空，将 `TimingEditCoordinator` 设为`Idle`、保留实际 `IncrementalStaSession::_state=kBaselineExecuted`，且g+1来自刚安装的 committed identity/marker；若latch命中，则在guard释放前将coordinator设为`Poisoned`并把实际session原子设为`StaSessionState::kPoisoned`，其committed identity/marker仍明确是完整g+1。

四个“commit sidecar hook”不是可执行callback，而是预配置ordinal上的 `noexcept` latch check；每个check即使命中也只记录故障位，不能中断后续step。Database、host snapshot、identity/trace/resolver和device marker必须先形成完整一致的g+1，再设置commit marker与最终session state。Database、host snapshot和sidecars只在guard释放后同时可见；任何observer只能看到exact g，或带`Idle/Poisoned`状态的完整g+1，绝不解锁混合generation。publish前任一故障先在candidate仍存活时清理singleton，再换回g Database并保留g host snapshot/identity/generation；外部0 writes visible。旧Database owner只属于g，只能用于commit boundary前rollback；step 1开始后即使fault latch命中也不得恢复它。

### 8.3 Post-publish poison 与 g+1恢复

commit前必须预备g+1 recovery material：baseline artifacts加“包含当前batch”的累计committed trace，或独立g+1 raw-input snapshot。commit sidecar latch或publish-after-commit故障只能形成“coordinator=`Poisoned`、session `_state=kPoisoned`、committed generation=`g+1`”；两者都不得用旧g owner静默退回。恢复流程固定为：旧session `_state=kPoisoned→kClosed`，创建新token/session，从baseline+累计trace独立full replay到g+1，重建host snapshot/device marker/current identity，再使coordinator=`Idle`且新session `_state=kBaselineExecuted`。恢复验收要求generation、trace、Database、host CSR都包含刚提交batch。

故障注入覆盖prepare、current-identity validation、stage、candidate install、四个native stage、host snapshot build、verify、publish-before-commit、四项commit sidecar latch与publish-after-commit。commit boundary逐点测试在并发observer与guard释放后都只能观察exact g或完整g+1，并断言四个sidecar latch不会中断step 1–6、命中后实际session state为`kPoisoned`。测试还证明guard只获取一次、公开递归操作被拒绝、并发线程不能观察candidate。

## 9. Normalize、validate 与 fallback policy

固定validate顺序：

1. schema/workload/session/baseline identity；
2. 重新export active Database，核对`expected_pre_committed_identity`的generation、六fingerprints与canonical pre-state；
3. semantic ref/token唯一解析，baseline ExistingArcRef只用初始binding；
4. supported edit/library/port/net driver/moved sink membership；
5. duplicate、insert→remove、remove→insert和跨edit冲突normalize；
6. parallel existing/created arc唯一性与reverse一删一增；
7. active DAG/cycle、endpoint、sequential/clock/data-only边界；
8. electrical invalidation closure与append-only capacity；
9. candidate canonical/pointer/index structural validation；
10. native full、new host CSR snapshot、independent oracle verification；
11. seal target post committed identity和publish bundle。

| edit/输入 | policy |
|---|---|
| 组合逻辑、单driver、无active cycle的buffer insertion | supported |
| missing/ambiguous ref、token collision、重复sink、坏library port | error |
| parallel arc不唯一、reverse非一删一增 | error |
| sequential/clock/gating、node deletion、cell replacement、多driver | error |
| 真实parasitic无法可靠split | full_with_record；零发布 |
| synthetic raw-model fixed inputs | synthetic-only |
| real trace预制derived timing答案 | error |

`full_with_record`明确未发布并记录full-rebuild requirement；不得静默应用。

## 10. Oracle 与四模式 harness

### 10.1 独立 fresh CPU/full cumulative oracle

每个batch prefix在新进程从baseline artifacts初始化session，只消费typed semantic trace与canonical comparison types。test-only `IndependentSemanticReplayer`自行解析creation token并直接修改raw Instance/Pin/Net，再由GraphBuilder/native timing stages生成arcs与结果；它不得消费PreparedBatch、resolved slots、production materialization map、candidate、rollback或production post payload。

oracle target的source/link inventory明确禁止`ista_timing_edit_native`、`ista_timing_edit_transaction`及production resolver/translator。它可以共享trace schema/types和Stage2 canonical comparison，不共享语义翻译实现。controller逐字段比较Instance/Pin/Net、timing point/arcs/adjacency/order/level、load/delay/slew以及arrival/required/slack/path state；fingerprint只辅助定位。deliberate-wrong-sink self-test故意让production seam编辑错误sink，必须由独立oracle发现。

### 10.2 CSR full host lane

每个candidate verify都从candidate Database新建`CsrCommittedSessionSnapshot`并运行`CsrCpuReferenceBackend`；对supported fixture与native CPU/full逐字段比较。publish安装这个host snapshot，不复用mutation前的StaCsrSessionContext snapshot。Stage2 session token在每个fresh session独立且CSR graph_generation仍为0。

### 10.3 四模式骨架

```text
cpu/full         implemented，authoritative native fresh oracle
cpu/incremental  typed unsupported(stage_not_implemented)
gpu/full         typed unsupported(stage_not_implemented)
gpu/incremental  typed unsupported(stage_not_implemented)
```

四个execution mode共享design snapshot/trace但进程和mutable state隔离；未实现mode不mock、不报告equality/speedup。CSR full是CPU/full配对的correctness oracle，不是第五个mode。

## 11. Trace 与确定性 mutation generator

`timing-edit-trace/1.0.0` JSON envelope包含：schema、semantic workload kind、seed、profile、baseline semantic identity、source artifact identity、ordered batches、creation tokens、semantic edits、policy receipts、pre/post graph evidence和 replay command。未知字段、未知 version、dense ID/native rank、real-design timing answer 均拒绝。

确定性 DAG/mutation generator使用固定 xorshift seed，先生成有稳定 semantic names 的 active DAG，再生成只引用可解析单-driver data net 的 buffer insertions。失败输出 seed 与完整 trace；命令 `... --trace <file> --prefix <n>` 可单独重放。随机测试服务于功能覆盖，不把 seed/hash 搜索当验收主体。

## 12. 测试矩阵

### 12.1 Unit/contract

- `ista_timing_edit_contract_test`：全部primitive、normalize、strict schema；
- `ista_timing_edit_resolver_test`：existing/created node/net/arc、append-only/tombstone、baseline one-shot binding；
- parallel cell arcs具有相同端点/signature仍唯一，current ordinal重排不改变surviving slot；
- `ista_timing_edit_native_test`：raw clone、library pointer rebinding、双向membership/adjacency；
- `ista_timing_edit_transaction_test`：state、current identity、host/device三侧publish、fault/poison/recover；
- public headers与source/link/inventory隔离。

### 12.2 Property

固定seeds `1,7,42,20260831,0xdeadbeef`：input permutation、DAG mutation、reverse一删一增、append-only不复用、publish前exact unchanged、cycle/collision/overflow/numeric reject。增加batch>1、stale generation、同generation外部篡改三类current identity reject。

### 12.3 Guard/publish/recovery

- test-only friend seam只获取一次OperationGuard，递归公开STA操作拒绝；
- 并发observer在guard释放前不能读取candidate；
- 每个publish同时读取Database、host snapshot、transaction identity与device-not-materialized generation；
- publish前fault保留exact g；commit boundary后四个noexcept latch均完成整个g+1安装并在解锁前poison；observer永不看到混合generation；
- postcommit fault poison完整g+1；fresh recovery后generation/trace/Database/host CSR包含当前batch；
- 旧StaCsrSessionContext snapshot在mutation前release/invalidate，不能继续scatter。

### 12.4 Integration/fresh process

- synthetic singleton/chain/diamond/multi-root/parallel/disabled/loop-disabled与真实buffer insertion；
- 每batch native CPU/full、new host CSR和independent fresh oracle逐字段一致；
- independent loader从真实artifacts成功建立fresh analyzed baseline，随后semantic replayer独立应用trace；
- CMake/closure inventory证明oracle不链接production edit native/transaction/resolver/translator；wrong-sink self-test必须失败；
- 同一trace至少3个fresh session；失败seed/trace一条命令重放。

## 13. 构建、回归与提交门禁

新建 `build-ista-stage34`，不复用 Stage 2 正式证据目录。迭代顺序：

1. build 新 production/test/probe targets；
2. `ctest -R '^ista_timing_edit_' --output-on-failure`；
3. `ctest -R '^ista_csr_' --output-on-failure`，基线 79 项；
4. iSTA unit/property/integration/smoke labels；
5. fresh replay `--repeat until-pass:3`；
6. parent 12 个 STA 定向 pytest，基线 227 passed；
7. parent non-PDK 全量，当前基线 1667 passed。

新增/修改 `.hpp/.cpp/.py/.cmake/.json` 保持职责单一，原则上不超过 700 物理行；source inventory检查 pure core不含 Database/STAInterface/IDM/iZH/pybind/CUDA，native target不含 IDB/iZH/CUDA。同步更新 CI 已有 target 构建清单，避免 CTest 注册但 executable 未构建。

阶段 3 单独闭环：child 实现与测试提交；parent 只提交 gitlink、`stage3-detailed-plan.md`、`stage3-report.md` 和总体计划状态更新。排除用户的 `CLAUDE.md` 与 `stage1-stage2-meeting-report.md`，不 push。

## 14. 编码步骤与停止条件

1. 完成 singleton/cache 与 pointer-lifetime 审计；若不安全，停止 ownership exchange 方案并切换 fresh-process candidate设计；
2. 冻结 pure three-layer types、stable ref、normalize/fallback和 JSON schema；
3. 独立设计审查必须明确 `APPROVE`；
4. 实现 raw candidate、受限 DataManager exchange 与 derived reset；
5. 实现 translator/resolver/prepared batch；
6. 实现 coordinator/fault injection/recovery；
7. 实现 fresh CPU/full + CSR full controller与真实 fixture；
8. 完成定向、Stage 2、parent回归与独立代码审查；
9. 更新报告/总体计划并创建本地提交。

以下任一存在时禁止宣告阶段 3 完成：trace 含 dense ID；parallel lifecycle identity未闭合；candidate复用旧 Arc pointer；publish 前可见半更新；无 postpublish poison/recovery；oracle 与被测共享 mutable state；只比 hash；未实现 lane 被 mock；Stage 2 CSR 回归不通过；真实 edit未覆盖图和电气扩展。
