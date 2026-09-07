# ECC IncreGPUSTA 阶段 6 详细实施计划

> 当前开发协议补充（开发检查分离）：mixed 的映射、indegree、容量和 cycle 分类始终运行，独立重建验证、详细访问计数与 full-levelizer 访问证明归 ON；按保存模式执行的恢复始终保留。 后续改动必读 [开发检查规范](development-guidelines.md)，双模式实测与历史验收的区别见 [本轮实施报告](debug-checks-implementation-report.md)。原阶段验收数字保留为历史记录。

> 状态：v1.0 已完成；设计复审与最终全diff实现审查均APPROVE；详见[阶段 6 报告](stage6-report.md)
> 前置与结果：Stage 5基线为`11ae6d767a4e7dc25b3504326fd7b383e1a711e5`；Stage 6 ecc-tools本地提交为`b8bfc3a79930b0be146ac26ca10dc0e99115f1fc`，未push
> 范围：CPU mixed incremental levelization reference；继续使用 Stage 5 targeted Dual-CSR 和 full CPU propagation
> 非范围：CUDA、affected-cone propagation、native/IDB commit、物理设计跨层事务、正式 speedup 结论
> 验收原则：功能正确性、语义一致性和可重复回归是主证据；hash、fingerprint、对象清单只作证据完整性辅助，不得演变为无上限的“哈希攻防”

## 1. 阶段目标与完成边界

阶段 6 将 `cpu/incremental` 从“targeted Dual-CSR + full levelization + full propagation”推进为“targeted Dual-CSR + mixed incremental levelization + full propagation”。本阶段只替换 levelization，propagation 仍遍历当前 generation 的完整 `BaseOut ∪ AuxOut` 与 `BaseIn`，以隔离论文 Algorithms 5–7 的正确性。

完成态必须同时具备：

- mixed graph builder 只读取 Stage 5 冻结的 generic `ActiveCsrEdgeView` 和上一 generation 的合法 levelization；
- corrected Kahn 以 indegree 为权威并明确报告 cycle/processed-count/view error；
- 成功域明确限制为保持旧 level 保守相对顺序的 mixed-order-compatible batch；actual graph 仍为 DAG 但必须重排旧层时返回 `kOldLevelOrderConflict`，不得冒充 actual cycle；
- reconstruction 生成当前所有 actual NodeId 的完整 level permutation 与 inverse map；
- full CPU propagation 直接消费 reconstructed levelization，不能暗中再次执行 full levelizer；
- Stage 4 frozen trace 每个 prefix 真实经过 targeted Dual-CSR 和 mixed path，且无 incremental-case fallback；
- 每批 graph/reference/timing 语义与独立 fresh CPU/full 等价；mixed level 可以比 fresh full 非最紧凑，但所有 eligible edge 必须严格跨层；
- 跨进程功能收据不比较具体 level 布局；targeted/fresh 的 levelization 各自在独立 typed receipt 中验证；
- Stage 2–5 相关回归、strict build、属性测试和 sanitizer 通过；
- 独立实现审查 `APPROVE`，阶段报告完成，child/parent 分别本地提交且不 push。

## 2. 证据来源与论文伪代码解释

### 2.1 Material Passport

- 来源：本地论文 `docs/incregpustaiccad-25.pdf`，不是网页转述；
- PDF 预检：9/9 页可枚举且 reader 可读，无 warning；
- SHA-256：`5eaf161a2cdfb8930f1e0a9f4e2d6b98f7f192570ee68d7f75b90df0a384d097`；
- 本阶段直接依据：论文第 5–6 页 Algorithms 5–7；
- 方法约束：确定性结构与 timing 结果要求精确/容差内复现；wall-clock timing 是环境敏感观察值，不作为功能完成门。

### 2.2 不照抄的疑似笔误

论文 Algorithm 6 的初始化条件写成 `outdeg[v] == 0`，后续却递减 indegree。CPU reference 固定纠正为：

1. 从 mixed precedence graph 计算每个 vertex 的 indegree；
2. 初始 frontier 只包含 indegree 为 0 的 vertex；
3. 处理 source 后递减其每个去重 successor 的 indegree；
4. indegree 变为 0 时进入下一可处理 frontier；
5. processed count 不等于 mixed vertex count 时返回 cycle，不输出部分成功结果。

论文 Algorithms 5–7 的 mixed/actual 转换方向存在易混淆写法。本实现不暴露裸整数互转，统一使用第 3 节的 tagged helpers，并以边界、往返和溢出测试冻结语义。

## 3. ID、generation 与 level 语义

### 3.1 本批边界

对 committed generation `g` 和已完成 targeted Dual-CSR update 的 staged generation `g+1`：

```text
n_last_nodes = committed(g).graph.nodeCount()
n_current_nodes = staged(g+1).graph.nodeCount()
n_new_nodes = n_current_nodes - n_last_nodes
n_old_levels = committed(g).timing.level_offsets.size() - 1
```

`n_last_nodes` 是每一批开始前的 node high-water，不是 session baseline 常量。上一批新增的 node 在下一批必须归入 old nodes。Stage 5 不支持 node deletion/reuse，所以 actual old range 精确为 `[0, n_last_nodes)`，new range精确为 `[n_last_nodes, n_current_nodes)`。

### 3.2 Mixed vertex domain

mixed graph 的 vertex 数量为 `n_old_levels + n_new_nodes`：

- `[0, n_old_levels)` 是 virtual old-level vertex；
- `[n_old_levels, n_old_levels + n_new_nodes)` 是 actual new-node vertex 的 mixed 表示。

转换固定为：

```text
mixed_index(new_actual) = n_old_levels + (new_actual - n_last_nodes)
new_actual(mixed_index) = n_last_nodes + (mixed_index - n_old_levels)
virtual_level(old_actual) = committed.node_to_level[old_actual] - 1
```

public types 至少区分 `VirtualOldLevel`、`NewActualNode`、`MixedVertexId`；禁止把三者作为可随意互换的 `uint64_t`。所有加减先检查范围和溢出；往返必须恒等。

### 3.3 Levelization 表示

对外继续复用 `csr::CsrFifoLevelization` 的格式：

- `level_offsets.front() == 0`，末项等于 node count；
- 每个 level 非空；空图唯一合法 offsets 为 `{0}`；
- `level_nodes` 是 `[0, nodeCount)` 的完整且无重复 permutation；
- `node_to_level` 使用既有 1-based level 编号；
- `node_to_level[level_nodes[p]]` 必须等于 `p` 所在 offsets 区间的 level + 1；
- `complete=true` 只有在全部验证通过后设置。
- 成功表示必须满足 `view_error == std::nullopt`；任何非空view error即使arrays与`complete=true`看似合法也必须拒绝。

合法但非最紧凑的 levelization 是预期结果，不得以 raw level equality 对 fresh full 判错。结构正确性的权威条件是完整 permutation、inverse map、每条当前 eligible arc 的 `level(source) < level(sink)` 与无 cycle。

## 4. 文件、target 与所有权

通用 caller-supplied level validator 归属于现有 DB-free CSR core：

```text
src/operation/iSTA/source/module/timing_csr/
  + CsrFifoLevelizationValidation.{hpp,cpp}
```

`validateCsrFifoLevelization(edges, levels)` 逐字段验证 `view_error == nullopt`、complete、offsets、permutation、inverse 和全部 eligible edge inequality。full CPU overload与external-level overload都只能依赖该向下层 validator，禁止让 CSR core 反向依赖 Stage 6 module，也禁止复制两份 validator。

新增纯算法 DB-free module：

```text
src/operation/iSTA/source/module/timing_incremental_levelization/
  CMakeLists.txt
  MixedLevelizationTypes.hpp
  MixedLevelizationGraphBuilder.{hpp,cpp}
  CorrectedMixedKahnLevelizer.{hpp,cpp}
  MixedLevelReconstructor.{hpp,cpp}
  MixedLevelizationValidation.{hpp,cpp}
  ActualDagCycleClassifier.{hpp,cpp}
  CpuIncrementalLevelizationPipeline.{hpp,cpp}
  MixedLevelizationTelemetry.hpp
```

target 分层冻结为：

```text
ista_timing_incremental_levelization
  public links = ista_timing_csr_core
  forbidden closure = Database, STAInterface, ista_interface, IDM,
                      iZH, pybind, CUDA, buffer-trace test seam,
                      FunctionalProjection, fresh oracle

ista_timing_dual_csr_transaction
  additional links = ista_timing_incremental_levelization,
                     Stage 5 structured/native adapter targets
  owns = capability integration, aggregate publish, recovery,
         Stage 6 batch trace/receipt observation
```

`runCpuIncrementalLevelization()`（定义于 `CpuIncrementalLevelizationPipeline.{hpp,cpp}`）只负责 pure mixed build/Kahn/reconstruction，不拥有 native candidate、transaction或publish。Stage 6 为 CPU backend 新增一个 public overload，使它消费 caller-supplied `CsrFifoLevelization`；该 overload 必须调用 CSR core 的通用 validator 后才 propagation，并明确不调用 `replayFifoLevelization()`。现有 full overload保持不变，继续作为独立 oracle。

真实 full-levelizer 计数器同样由 `ista_timing_csr_core` 所有：thread-local operation guard在 generic `replayFifoLevelization(edges, payloads, telemetry)` 函数体真实入口递增一次，flat-input overload只转调generic入口而不得双计数。guard产生的move-only delta由私有构造冻结，Stage 6 factory内部读取并写入不可由调用者填值的batch trace。必须有full backend正控delta恰为1、external-level backend delta恰为0、malformed external levels失败仍为0；不得用默认初始化为0的telemetry字段自证。

benchmark/runtime 与测试新增：

```text
src/operation/iSTA/benchmark/dual_csr/
  + CpuIncrementalLevelizationRunner.{hpp,cpp}

src/operation/iSTA/test/timing_incremental_levelization/
  MixedIdMappingTest.cpp
  MixedGraphBuilderTest.cpp
  CorrectedMixedKahnTest.cpp
  MixedReconstructionTest.cpp
  IncrementalLevelizationPipelineTest.cpp
  IncrementalLevelizationPropertyTest.cpp
  IncrementalLevelizationTraceProductionFreshProbe.cpp
  incremental_levelization_controller.py
```

测试 adapter 负责 fixture、fresh process、receipt 序列化和故障注入；production module 不读取 JSON、native singleton、hash manifest 或 oracle 输出。

## 5. Mixed graph builder

### 5.1 输入前置

builder 只接收：

```text
ActiveCsrEdgeView(current staged graph)
previous complete CsrFifoLevelization
n_last_nodes
current committed/staged generation binding
```

必须先验证 previous levelization 精确覆盖 `[0, n_last_nodes)`；当前 `nodeCount >= n_last_nodes`；generation 连续；view 中所有 active arc payload 的 endpoints 有效。不得读取 Dual updater 内部 vectors、physical Base slot、Aux mapping、pending descriptor、native DB 或 decoded flat CSR。

### 5.2 Virtual chain

为每个 old level 建一个 virtual vertex，并添加：

```text
virtual(0) -> virtual(1) -> ... -> virtual(n_old_levels - 1)
```

该 chain 保留上一 generation 的保守拓扑序。removed old→old edge 不需要显式加入 mixed graph；即使 fresh full 能压缩 level，旧 chain 仍可产生合法非最紧凑结果。

本阶段成功域明确为 **mixed-order-compatible**：当前 actual eligible graph 必须是 DAG，且把old actual node按previous level压缩为virtual vertex、再加入上述chain后，mixed precedence graph仍是DAG。actual graph虽为DAG、但新增约束要求某些old level跨越或逆转previous相对顺序时，本算法不能正确增量化；必须返回typed `kOldLevelOrderConflict`/`kUnsupportedReorder`，不得报告`kActualCycle`，也不得fallback为full levelizer后冒充incremental成功。

为了准确分类，pure pipeline只在old→old equal/backward约束或mixed Kahn失败时运行一次只读 `ActualDagCycleClassifier`：它对当前eligible actual view执行独立indegree Kahn，仅回答“actual DAG/cycle”，不生成levels、不进入full backend、不能授权成功。actual cyclic返回`kActualCycle`；actual DAG而mixed失败返回`kOldLevelOrderConflict`；classifier自身view error原样返回。该诊断遍历单独计数，不改变full-levelizer entry delta。

### 5.3 当前 eligible arc 映射

builder 通过 `forEachActiveArc()` 精确访问当前 active arcs，仅当 `payload.eligibility.levelization` 为真时形成 precedence：

| Actual edge | Mixed precedence |
|---|---|
| old → old | 不新增 edge；验证 previous old level 严格递增 |
| old → new | `virtual(old_level) → mixed(new)` |
| new → old | `mixed(new) → virtual(old_level)` |
| new → new | `mixed(source) → mixed(sink)` |

disabled、loop-disabled、non-propagating 由 payload eligibility 决定，不能根据 storage kind 或 arc kind 猜测。BaseOut 与 AuxOut 在同一 generic traversal 中处理；Aux 不得被假定为空。

对需要形成mixed edge的old→new/new→old/new→new，先按actual `(source,sink)` 折叠真正parallel arcs，再把unique actual endpoint pairs映射到mixed pairs；不同actual pairs因共享virtual proxy而alias时进行第二级去重。最终每个mixed pair只保留一条precedence edge，避免indegree重复递减；telemetry按第11节分别记录actual parallel与proxy alias。任何mixed self-loop均进入第5.2节的actual-DAG分类，不用含混的cycle/precondition code。

### 5.4 Builder 不变量

输出必须满足：

- vertex domain 连续且分类互斥；
- adjacency offsets 合法，successor 有序、无重复、无越界；
- indegree 与去重 adjacency 精确匹配；
- old-level chain edge 数精确为 `max(n_old_levels - 1, 0)`；
- old→old backward/equal edge 被拒绝，不用 chain 掩盖非法 committed order；
- view callback error 原样映射为 typed build failure；
- 任何失败不返回可继续进入 Kahn 的半成品。

其中old→old backward/equal edge不是笼统的malformed input：pipeline必须按第5.2节先区分`kActualCycle`与`kOldLevelOrderConflict`。

## 6. Corrected Kahn levelizer

Kahn 输入只接受验证通过的 immutable mixed graph。确定性规则固定为：

1. 拷贝 builder 已核对的 indegree；
2. 当前 frontier 按 `MixedVertexId` 升序；
3. 同一 frontier 构成一个 mixed output level；
4. 处理本层全部 vertex 后再形成下一 frontier；
5. 每条 deduplicated successor edge 恰好递减一次；
6. indegree 下溢、重复入队、重复处理、越界均为 invariant failure；
7. `processed_count != vertex_count` 返回内部 `kMixedCycle`，同时报告 remaining vertex count，不生成成功 levels。

结果除 level offsets/nodes/inverse 外还记录 `processed_count` 和最大 frontier。Kahn 不访问 native DB、actual CSR storage 或 timing payload。pipeline拿到`kMixedCycle`后必须按第5.2节用current actual view分类，对外只暴露准确的`kActualCycle`或`kOldLevelOrderConflict`，不暴露含混的成功/失败解释。

## 7. Reconstruction

按 mixed output level 顺序构造 actual levels：

- 遇到 virtual old-level vertex，复制 previous level 对应的全部 actual old NodeId；
- 遇到 new-node mixed vertex，按第 3.2 节公式转换并追加 actual NodeId；
- 同一 mixed output level 内 deterministic order 固定为 virtual expansion 按 virtual id、new nodes 按 actual NodeId；
- virtual chain 理论上保证每个 mixed output level至多一个 virtual vertex，reconstructor仍必须显式验证；
- 每个 old/new actual node 必须恰好出现一次；
- 从输出重新构造 `node_to_level`，禁止复制未经验证的 inverse；
- 输出后再次遍历当前 eligible arcs，验证严格 level inequality。

reconstruction 不做 H2D/D2D；论文 Algorithm 7 的 device copy 语义留到 Stage 9。本阶段 CPU oracle 只证明同构的 level mapping 与顺序。

## 8. CPU incremental pipeline 与事务

Stage 6唯一production staging工厂及其不可擦除的typed失败边界冻结为：

```text
DualCsrStageFailureOrigin = kExactBefore | kCapability | kIndexDelta |
                            kUpdater | kStateValidation | kTimingIntrinsic
DualCsrStageFailure { origin, exact DualCsrViolations }

MixedStageFailureCode = kActualCycle | kOldLevelOrderConflict | kViewError |
                        kMalformedPreviousLevels | kMappingOverflow | kInvariantFailure
MixedFailureOrigin = kBuilderOldOld | kMixedKahnQuotient | kActualClassifier |
                     kViewTraversal | kExternalLevelValidation | kPropagation
MixedLevelizationFailure { code, origin, optional view_error, generation, detail }
MixedDualCsrStageAttempt = variant<DualCsrVerifiedStage,
                                   DualCsrStageFailure, MixedLevelizationFailure>

makeMixedLevelizedDualCsrAnalysisState(
    const CommittedDualCsrAnalysisState& exact_committed_before,
    VerifiedStructuredBatch&& verified_batch)
  -> MixedDualCsrStageAttempt
```

它是唯一能私有构造既有move-only `DualCsrVerifiedStage` 的Stage 6路径。工厂在updater前逐字段重验capability绑定的exact-before graph/resolver/`DualCsrArcGroupIndex`/identity、batch generation、descriptor `ArcGroupIndexDelta`相对before index及完整aggregate；任一Stage 5阶段失败原样携`DualCsrViolations`和origin，不得擦成mixed failure。之后才完成updater、mixed pipeline、external-level propagation和intrinsic validators；builder/Kahn/classifier/runner共享同一mixed typed failure。公开接口禁止调用者提供timing/levels/descriptor/resolver/telemetry/post identity。Stage 5安全full工厂同样必须验证exact-before index与delta并保留用于回归；只删除raw staging入口。publish仍以verified stage捕获的完整exact-before逐字段重验。

每批顺序固定为：

```text
Stage 5 VerifiedStructuredBatch&&
  -> targeted DualCsrUpdater stage(g -> g+1)
  -> validate staged DualCsrState/direct view
  -> build mixed graph(previous committed levels, n_last_nodes, staged view)
  -> corrected Kahn
  -> reconstruct actual CsrFifoLevelization
  -> validate permutation/inverse/all eligible edge inequalities
  -> full CPU arc initialization + forward + required propagation
     using supplied reconstructed levels
  -> validate complete DualCsrTimingResult
  -> mint Stage 6 verified stage
  -> one noexcept aggregate swap
```

aggregate publish仍必须同时覆盖graph、timing、resolver、committed arc-group index、identity、generation、descriptor/semantic traces、deterministic traversal counters与逐批判别式 `LevelizationExecutionTrace`。每个descriptor恰好对应一个连续generation record：`kFullStage5`只由Stage 5安全full工厂追加真实full-entry delta与validation，`kMixedStage6`只由mixed工厂追加输入边界、typed分类计数、输出验证与真实entry delta；两种mode不得伪造。execution trace和committed telemetry只含确定性mode/结构/计数，不含wall-clock样本。
aggregate validator要求execution/descriptor/semantic traces等长并逐generation一一对应，mode字段、levels、timing一致；transaction prefix、exact-before、recovery deterministic match及同一次swap包含graph/timing/resolver/index/identity/generation/traces/counters。上一generation levels来自committed timing，staged levels只存在detached aggregate；任何mixed失败均在swap前且committed逐字段不变。

production publish 不依赖 fresh oracle。publish后生成 functional/structural/levelization/transaction observations；fresh 与 targeted 均完成并封口后，外部 controller 才产生 differential verdict。receipt 序列化失败令 run terminal，不回滚已完整 publish 的 aggregate。

本阶段 correctness case 禁止 fallback；所有列举错误均显式失败。recovery在新one-shot session从generation 0按descriptor/semantic batch和持久mode依次重放同一full/mixed pipeline，mixed批使用上一已恢复levels，精确复现非紧凑levels、timing values、mode、确定性计数及结构trace。比较前必须通过唯一typed `rebindRecoveredAggregateSession(old_token,new_token)` 一致换绑graph/timing source identity、resolver、index、descriptor/transaction session字段；拒绝部分换绑，断言token确已改变，再比较其余确定性字段。wall-clock只在run/sample envelope重新测量且排除于aggregate/exact match，禁止复制旧耗时冒充重放。恢复重放单列计数且不算incremental成功；禁止compact full替代mode重放。

## 9. Functional differential 语义

Stage 6 不复用现有 `FunctionalSemanticReceipt::operator==` 做跨进程判定，因为其中的 `level_offsets`、`level_nodes`、`node_to_level`、`timing_order` 会把合法非紧凑结果误判。新增边界冻结为：

- `Stage6FunctionalReceipt = graph/reference semantic projection + TimingValueSemanticProjection`；后者含全部node/clock/data/path/arc数值与presence、key-remapped predecessor/start/crpr，但类型上不含上述四个level字段；
- `LevelizationReceipt` 单独保存按NodeKey重映射的levels、inverse与timing order。targeted/fresh分别结合各自同一份graph receipt重新验证complete、permutation、inverse与每条eligible ArcKey的严格edge inequality；两侧level assignment不互比；
- `DualCsrStructuralReceipt` 与run-final `TransactionReceipt` 继续各自验证，不参与fresh功能相等。

外部 controller 分开执行：

1. graph/reference：按 NodeKey/ArcKey 与完整 typed payload 精确比较；
2. targeted `LevelizationReceipt`：完整 permutation、inverse、eligible edge inequality、cycle-free、generation binding；
3. fresh `LevelizationReceipt`：由 Stage 2 full reference 输出后按同一结构契约独立验证；
4. timing：node/clock/data/path/arc SoA 的 presence 与 numeric value 按 Stage 2 tolerance 比较；
5. predecessor/start/crpr 中所有 NodeId/ArcId 先转 NodeKey/ArcKey；equal-cost predecessor只接受规范等价 winner 集合；
6. structural/transaction telemetry 各自验证，不与 fresh compact ID 或 physical layout 比较。

不能用 hash、raw dense ID、stable ArcId、physical slot、level count相等或对象数量相等替代上述逐字段功能比较。fingerprint只可绑定同一 rank-free typed receipt并用于诊断。

receipt/comparator canary必须覆盖：同一graph/reference与timing values、两份不同但都合法的levelization必须通过；任一侧若缺node、inverse不一致、timing order越界或违反eligible edge inequality必须失败。Stage 5原receipt仍服务Stage 5自身回归，但Stage 6 controller不得偷偷调用其整体相等运算符。

## 10. 冻结测试矩阵

### 10.1 ID 与算法 microcases

至少覆盖：

- old=0/new>0、old>0/new=0、单 old level、多 old levels；
- mapping 两端边界、往返恒等、加减溢出和非法 tag；
- old→old、old→new、new→old、new→new 四类；
- parallel arc dedup 与连续 ordinal；
- removed old→old 导致合法非紧凑 levels；
- early old→old conflict与Kahn后quotient conflict分别保留origin且都返回`kOldLevelOrderConflict`；真实actual cycle返回`kActualCycle`，view traversal error返回`kViewError`；
- disabled/loop-disabled/non-propagating arc 不进入 mixed precedence；
- partial parallel-group deactivation：剩余active ArcId重编号为ordinal 0、inactive historical key也可为ordinal 0；mixed builder只读取active `payload.key`，Stage6功能收据与fresh一致，遗漏同-base peer的capability被Stage 5/6边界拒绝；
- Base 与 Aux 的四类映射，至少一个 Aux arc进入 mixed builder；
- mixed self-loop分类、indegree下溢 canary、processed-count mismatch；
- malformed previous offsets/permutation/inverse；以及`complete=true`、arrays合法但`view_error!=nullopt`仍拒绝且full-levelizer entry delta为0；
- 同一 mixed level 多 virtual marker rejection canary；
- multi-batch：上一批 new node 在下一批作为 old node/virtual level参与；
- 合法非紧凑publish → post-swap poison → 新session typed rebind + exact replay recovery → 下一批mixed成功；token必须改变，换绑后一致且不得复制旧wall-clock；
- `g1=kFullStage5 → g2=kMixedStage6 → poison → mode-dispatched recovery`：每descriptor恰一条真实record，full delta=1、mixed delta=0，恢复后继续下一批；
- public factory分别注入stale exact-before、错误index delta、updater conflict、intrinsic timing failure，均返回保留exact `DualCsrViolations`的`DualCsrStageFailure`。

### 10.2 Property tests

固定seeds `1, 7, 42, 20260901, 0xdeadbeef`，每seed至少24 samples。生成器必须成对生成committed(g)与staged(g+1)，不得把任意DAG加随机old/new分界都视为成功：成功样本先构造合法previous levels，再只加入mixed-order-compatible变更；负例独立生成“actual仍为DAG但mixed-order conflict”和“actual真实cycle”，并验证两类typed code不同。另覆盖parallel arcs、eligible mask、malformed previous/mapping变体，独立oracle只检查actual graph和显式quotient约束，不复用mixed builder。每个失败验证输入与committed aggregate原子不变，并输出seed、sample、actual/mixed graph摘要，不以hash作为oracle。

### 10.3 Frozen trace 与 fresh process

对 Stage 4 `synthetic_two_batch`、`real_buffer_fanout` 的每个 prefix 运行相互隔离的：

- `targeted-under-test`：Stage 5 structured path + Dual update + mixed levelization + full propagation；
- `fresh-oracle`：从原始设计累计重放 prefix + native CPU/full；
- `controller-comparator`：只读双方 sealed typed receipts。

targeted receipt必须证明当前batch的execution mode=`kMixedStage6`、`n_new_nodes > 0`、mixed builder/Kahn/reconstruction均执行、processed count完整、fallback=0、full levelizer actual-entry=0；Stage 5回归则逐batch要求mode=`kFullStage5`且真实full entry/validation成立。每个frozen buffer-insertion batch还必须分别断言`old_new > 0`、`new_old > 0`、`new_new > 0`，以semantic NodeKey列出至少一条对应active ArcKey，不能只靠总数。`synthetic_two_batch`的batch 2必须额外证明batch 1新增buffer nodes在`n_last_nodes`边界内并按old/virtual分类，同时batch 2新增nodes按new/mixed分类。

同一测试组必须先运行full backend正控并观察真实entry delta=1，再运行targeted external-level路径delta=0；malformed supplied levels应在传播前失败且delta仍为0。receipt只能携带factory从operation guard封口的delta，测试/调用者无公开setter。

### 10.4 回归与 sanitizer

运行顺序：Stage 6 focused unit/property → Stage 5 Dual/Aux/transaction/capture → Stage 2 generic/full backend → Stage 3 timing edit → Stage 4 buffer trace → Stage 6 production/fresh controller。对 mixed builder/Kahn/reconstruction、Aux microcase和property运行 ASan+UBSan；所有 production C++ 使用 `-Wall -Wextra -Werror -pedantic -ffp-contract=off`。

## 11. Telemetry 与报告

2026-09-05 第二轮清理：`MixedLevelizationDeterministicTrace` 归属 DB-free mixed 模块，在 `MixedLevelizationTelemetry.hpp` 定义。运行遥测继承这份确定性计数，再增加耗时与 `legal_noncompact`；transaction 的 `projectDeterministicMixedTrace()` 只复制确定性基类。计数恒等式统一使用 `validateMixedTelemetryIdentities()`，transaction 另验 processed count、frontier、重建完成度和 classifier/fallback 约束。JSON 字段与恢复等价语义保持不变。

每批至少记录：

```text
n_last_nodes / n_current_nodes / n_new_nodes
n_old_levels / mixed_vertex_count
actual_eligible_arc_visits
old_old / old_new / new_old / new_new arc visits
mapped_actual_arc_candidates / unique_actual_endpoint_pairs
actual_parallel_duplicates_collapsed / proxy_alias_duplicates_collapsed
unique_precedence_edges
virtual_chain_edges
base_out / aux_out visits
kahn_processed_count / max_frontier / reconstructed_level_count
actual_cycle_classifier_runs / actual_cycle_classifier_arc_visits
legal_noncompact=true|false（与fresh比较，仅报告）
mixed_build_ms / mixed_kahn_ms / reconstruct_ms
full_propagation_ms / fresh_oracle_ms(correctness-only)
full_levelizer_entry_delta / fallback_count
```

所有计数用checked arithmetic并逐批验证：`actual_eligible_arc_visits = old_old + old_new + new_old + new_new = base_out + aux_out`；`mapped_actual_arc_candidates = old_new + new_old + new_new`；`unique_actual_endpoint_pairs = mapped_actual_arc_candidates - actual_parallel_duplicates_collapsed`；`unique_mapped_precedence_edges = unique_actual_endpoint_pairs - proxy_alias_duplicates_collapsed`；`unique_precedence_edges = virtual_chain_edges + unique_mapped_precedence_edges`。old→old只验证previous order，不进入mapped candidates；不得把多个old node共享virtual level产生的alias误报为actual parallel arc。

时间只作run/sample envelope中的smoke与阶段观察，绝不进入committed aggregate、execution trace或exact recovery equality。报告必须给出编译器、flags、CPU、线程数、build type、fixture/prefix、warmup/sample方法，并明确fresh oracle时间不进入incremental样本。

## 12. 实施与独立审查顺序

1. 本详细计划由未参与起草的 subagent 审查 Algorithms 5–7解释、ID映射、非紧凑合法性、事务边界与测试充分性；blocker/major/minor闭合并 `APPROVE`；
2. 实现 external-level CPU backend overload与独立 level validator，先证明给定 full levels 时不改变 timing；
3. 实现 tagged ID helpers、mixed builder、Kahn、reconstruction与 focused tests；
4. 实现 Stage 6 pipeline/capability/transaction接线和真实 full-levelizer entry counter；
5. 接 Stage 4 frozen traces、fresh controller与属性测试；
6. strict build、相关回归、ASan+UBSan；
7. 未参与实现的 subagent 按 `docs/review-guidelines.md` 独立检查；修正后复审至 `APPROVE`；
8. 写 Stage 6 报告，更新总体计划，先 child 后 parent 本地提交，不 push且不夹带用户已有修改。

## 13. 成功标准与停止条件

以下全部成立才能宣告 Stage 6 完成：

- Stage 5 已完整完成并提交；
- mixed builder不依赖 native/flat decode/updater internals；
- mixed-order-compatible成功域及early/quotient conflict、actual cycle、view error的typed code/origin全部通过；
- corrected indegree Kahn、reconstruction及通用external-level validator所有不变量通过；
- fixed traces真实执行old→new/new→old/new→new mixed path且full-levelizer真实entry delta=0，full正控delta=1；
- 每批 timing 与 fresh CPU/full按语义字段等价；
- Stage 6 functional comparator接受不同但合法的levelization，`LevelizationReceipt`拒绝所有结构/edge inequality canary；
- 合法非紧凑levels被接受；post-swap poison后新session完成全字段typed rebind与按mode重放，确定性状态精确复现并继续下一批，wall-clock明确排除；
- Stage 5 full与Stage 6 mixed每个descriptor恰有一个真实mode-specific execution record，均参与exact-before/recovery/swap；
- correctness cases fallback=0；
- Stage 2–5相关功能回归与Stage 6 focused/property/production-fresh controller全部通过；
- production C++ strict flags通过，mixed/Aux/property在ASan+UBSan下通过；
- 所有新增或修改的production/test/report文件均不超过700物理行，`git diff --check`通过；
- 未参与实现的独立审查者给出`APPROVE`，所有blocker/major/minor闭合；
- Stage 6报告和总体计划已更新；
- child先提交、parent后提交，均为本地commit，不push且不夹带`CLAUDE.md`、Stage 1–2会议报告等用户已有修改。

## 14. As-built 完成记录

Stage 6按本计划完成，未改变成功域和非范围：production路径为targeted Dual-CSR + mixed incremental levelization + caller-supplied levels上的full CPU propagation；没有affected-cone、CUDA、native/IDB commit或性能结论。

实现闭合如下：

- 新增DB-free mixed builder、typed ID、corrected indegree Kahn、actual-DAG classifier、reconstruction、validation和pipeline；old-level chain、四类actual edge、parallel/proxy去重、Base/Aux traversal和typed conflict/cycle/view failure均进入属性与microcase覆盖。
- CSR core新增caller-supplied levelization validator/backend；真实full-levelizer入口guard证明full正控delta=1、external/mixed与malformed external均为0。
- 公开Stage factory只接收冻结capability与previous levels，内部完成exact-before/index delta/updater/mixed/external propagation/intrinsic validation；failure matrix保留stale、index、updater与timing intrinsic的typed origin/code/field/message。
- `LevelizationExecutionTrace`为sealed immutable typed object，绑定generation、mode、levels、traversal、真实entry delta、fallback、validation和mixed telemetry；transaction publish与recovery按mode逐descriptor保留唯一真实execution record。
- controller以baseline `{id,key}` 和逐代node appends重建dense NodeId映射；level按offset、NodeKey→level inverse和逐层精确NodeKey集合绑定，允许合法同层顺序差异，拒绝跨层、traversal与semantic trace篡改。
- functional receipt只比较rank-free graph/reference/timing语义；两侧levelization分别验证。equal-cost predecessor由证据推导合法winner集合，legal noncompact只报告。
- frozen synthetic两批与real一批均真实执行mixed path、fallback=0、full entry delta=0，并与独立fresh CPU/full功能等价。
- active-payload microcase使用合法parallel cell-arc group，真实覆盖same-base peer omission的`kArcMultiplicityMismatch`、aggregate不变、active/inactive ordinal 0 key collision、inactive poison隔离，以及mixed与独立public full功能等价。
- mode recovery覆盖`g1=full → g2=mixed → poison → 新token rebind/replay → 下一批`，确定性state/trace精确恢复，wall-clock不参与等价。

最终证据：

- GCC 14.3.0 strict Release统一标签14/14 PASS；Ninja Stage 5/6 source isolation 2/2 PASS。
- Stage 2–5相关广覆盖中148项功能/语义检查PASS；5项历史硬编码inventory继续作为辅助限制单列，不修改数量常量冒充功能修复。
- parent冻结STA 227/227 PASS；non-PDK为1665 passed、8 skipped、4 deselected、13 xfailed、2个第三方deprecation warning。
- ASan与UBSan各8/8 PASS，抽查二进制分别真实加载`libasan.so.8`与`libubsan.so.1`，无运行时诊断。
- 所有变更文件少于700物理行，`git diff --check`干净，无`pycache/pyc/orig/rej/patch/bak`。
- 最终独立全diff审查结论`APPROVE`，无remaining blocker/major/minor。

完成结论以逐字段功能正确性、typed failure、真实execution path、fresh replay、rollback与source isolation为依据；hash/object/count inventory未被用作核心证明。详细命令、边界和辅助限制见[阶段 6 报告](stage6-report.md)。
