# ECC IncreGPUSTA 阶段 5 详细实施计划

> 当前开发协议补充（开发检查分离）：重复 aggregate/index/resolver 验证、narrow capture 审计和 execution trace 全量 payload 归 ON；局部 descriptor 适用性、必要 active-edge 数量及发布身份始终保留。 后续改动必读 [开发检查规范](development-guidelines.md)，双模式实测与历史验收的区别见 [本轮实施报告](debug-checks-implementation-report.md)。原阶段验收数字保留为历史记录。

> 状态：v1.0 as-built冻结；Stage 5功能实现、回归、报告与最终独立审查均已完成
> 基线：Stage 4 完成本地提交 parent `ace28d79e19647c6f4866a339cc6faa7dca61fa9`，ecc-tools `eff4706f77a882d84317341f78e567ef5262b6d1`
> 完成提交：ecc-tools child `11ae6d767a4e7dc25b3504326fd7b383e1a711e5`；parent由本计划、报告和submodule pointer所在的本地提交承载；均不push
> 范围：CPU targeted Dual-CSR 图更新、持久 BaseOut/BaseIn/AuxOut、descriptor/rollback、Base∪Aux 直接 full CPU levelization/propagation 与 fresh CPU/full differential；不实现 mixed levelization、CUDA、affected-cone propagation、物理 IDB 提交或 speedup 结论
> 验收原则：功能正确性是主证据，按 topology、payload、level、timing、generation、rollback 逐语义字段验收；hash、raw object/depfile及count inventory仅作辅助，单独失败不得否定已成立的功能正确性；真实 forbidden dependency或边界泄漏仍是独立架构阻断
> 审查结论：v0.15独立设计复审APPROVE；v0.16–v0.17冻结direct-view、candidate native FIFO、完整Base重写、gen0 typed anchor及独立phase计时；as-built最终全diff审查无保留APPROVE

## 1. 阶段目标、完成边界与硬前置

阶段 5 在 Stage 4 已冻结 semantic traces 上首次建立持久 CPU Dual-CSR：session 初始化时允许一次 native→CSR full export；正常 mutation batch 只能从 `PreparedBatch`、session-stable resolver 和受影响 native records 生成 compact descriptors，在 detached state 上 targeted update。更新后立即让 full CPU levelizer 与 full CPU propagation 直接读取 `BaseOut ∪ AuxOut` 和 `BaseIn`，再与独立 fresh CPU/full oracle 按语义字段比较。

本阶段只隔离“图结构与相关 timing input payload 的增量更新”。native candidate仍可作为 isolated semantic mutation与fresh oracle载体，但其 full GraphBuilder/timing成本不得混入 `dual_csr_update_ms`，也不得被描述为增量 propagation。阶段 6 才把 full levelization替换为 mixed incremental levelization；本阶段 propagation始终是 `full_graph`。

硬前置：

- Stage 2 CSR full backend、reference model、stable semantic keys与fresh differential保持可复用且其默认generation-0行为不回归；
- Stage 3 `PreparedBatch`、append-only resolver、candidate/rollback、coordinator publish与fresh recovery已通过；
- Stage 4 `synthetic_two_batch.json`、`real_buffer_fanout.json`与manifest保持冻结，不重录选择结果来迁就Dual-CSR实现；
- correctness case强制 `cpu/incremental/error`、非空batch、无fallback；
- 任何targeted path仍调用完整 `exportCsrReferenceInputCandidate()`、`buildCsrSessionSnapshot()`或native full CSR rebuild时，阶段 5不得完成。

## 2. 立项时实现缺口与不可伪装项

立项时 Stage 3/4 路径每批仍做三次full性质工作：`NativeTimingEditPreparer::prepare()`重新export current CSR；`BufferTraceReplayer`从candidate重建完整host snapshot；`TimingEditCoordinator::publish()`再次重建snapshot并运行CSR CPU/full proof。`CsrReferenceInputValidator`和coordinator另把host graph generation固定为0。上述路径是Stage 3正确的full oracle，但不能换名为targeted update。

`PreparedBatch::slotPlan()`已经提供session-stable append-only node/net/arc logical slots；baseline slot与Stage 2 `NodeId/ArcId`一致，created object只append，removed arc形成resolver tombstone。这些logical IDs可以复用。它尚未提供：

- BaseOut/BaseIn physical slot；
- remove/change/reverse-change/append descriptor；
- Aux row与source mapping；
- created/changed `NodeRecord/ArcRecord`及load/delay/library/cap payload；
- capacity plan、update telemetry或Dual-CSR rollback owner。

物理 Base slot和逻辑 `ArcId` 必须分离。复用一个Base physical tombstone只表示该位置改存新的append-only ArcId，绝不允许复活或复用已删除ArcId。

generation 0 由新增 `DualCsrBaselineFactory` 从唯一一次合法的 `CsrReferenceInput` 构造完整 `DualCsrState`、独立 `DualCsrTimingResult` 与 committed resolver。之后任何正常batch都不得再次调用该factory；baseline构造与每批structured preparer分别计数。

## 3. 精确文件与 target 计划

### 3.1 新增 DB-free core

```text
src/operation/iSTA/source/module/timing_dual_csr/
  CMakeLists.txt
  DualCsrTypes.hpp
  DualCsrBaselineFactory.{hpp,cpp}
  DualCsrDescriptors.hpp
  DualCsrDescriptorValidation.{hpp,cpp}
  DualCsrState.hpp
  DualCsrStateValidation.{hpp,cpp}
  DualCsrArcGroupIndex.{hpp,cpp}
  DualCsrArcGroupIndexValidation.{hpp,cpp}
  DualCsrUpdater.{hpp,cpp}
  DualCsrTimingResultValidator.{hpp,cpp}
  DualCsrUpdatePhases.cpp
  DualCsrEdgeViewImpl.{hpp,cpp}
  DualCsrTimingPayloadViewImpl.{hpp,cpp}
  DualCsrFunctionalProjection.{hpp,cpp}
  DualCsrTelemetry.hpp
```

Target固定为：

```text
ista_timing_dual_csr
  fixed sources = baseline factory, descriptor/state/index validation, arc-group index,
                  DualCsrTimingResultValidator, updater/update phases, Dual view implementations, functional projection
  public links = ista_timing_csr_core, ista_timing_edit_contract
  forbidden closure = Database, STAInterface, ista_interface, ista_source,
                      IDM, iZH, pybind, CUDA, Stage 3/4 test seam
```

该target只接收typed values，不读取native singleton、文件、JSON或hash manifest。它拥有descriptor/state/view/invariants，不拥有semantic selection、native mutation或fresh oracle。

### 3.2 Generic view contract归属

```text
src/operation/iSTA/source/module/timing_csr/
  ActiveCsrEdgeView.hpp
  TimingPayloadView.hpp
  FlatCsrEdgeView.{hpp,cpp}
  FlatTimingPayloadView.{hpp,cpp}
```

`ActiveCsrEdgeView`与`TimingPayloadView`是DB-free抽象contract，归 `ista_timing_csr_core`；flat与Dual分别实现。generic levelizer/backend只依赖这两个contract，`timing_csr`绝不include/link `timing_dual_csr`，从而消除 `timing_csr ↔ timing_dual_csr` 依赖环。现有flat API保留为薄wrapper，但它也必须经 `Flat*View` 进入同一四阶段visitor入口。
`ArcSemanticPayload`在 `ActiveCsrEdgeView.hpp` 唯一定义；它是flat/Dual共同消费的rank-free semantic payload，不得在任一实现中另设未归属alias或影子类型。`ExpectedRef`、`EdgeVisitor`、`CsrViewError`、`EdgeEntry`与Continue/Stop/Error返回类型也均在该header声明；flat/Dual实现不得复制aliases或形成ABI不同的error枚举。


### 3.3 新增 Stage 5-owned native adapter

```text
src/operation/iSTA/source/module/timing_dual_csr_native/
  CMakeLists.txt
  DualSemanticReadView.hpp
  AffectedCapturePlan.hpp
  NarrowTimingRecordReader.{hpp,cpp}
  NativeAffectedArcAdjacencyCollector.{hpp,cpp}
  DualCsrArcGroupResolverValidation.{hpp,cpp}

src/operation/iSTA/source/data_manager/adapter/csr/
  CanonicalTimingRecordProjector.{hpp,cpp}
  CanonicalTimingRecordProjectorInternal.hpp
  NativeDualCsrPayloadCapture.{hpp,cpp}
  TimingEditDualCsrDescriptorBuilder.{hpp,cpp}
  DualCsrStructuredBatchPreparer.{hpp,cpp}
```

Target固定为：

```text
ista_timing_dual_csr_native
  public links = ista_timing_dual_csr, ista_timing_edit_native
  private links = ista_timing_graph_csr_adapter,
                  ista_timing_database_headers, ista_data_manager
```

structured prepare固定拆成两级move-only能力。pre-candidate DB-free函数只接收 `semantic plan + committed resolver + keyed DualSemanticReadView + exact DualCsrState + exact rank-free identity + const DualCsrArcGroupIndex` 六类typed values，私有构造 `PendingStructuredBatch`；plan/resolver/view确定semantic edit seeds，index只允许扩展这些seed对应的完整same-base active peer group，graph/identity仅验证并复制exact-before，均不得扩张到无关selection。它整体持有validated但未seal的 `PreparedBatch`、staged resolver、`AffectedCapturePlan`和exact expected-before。Stage 5不得调用Stage3 native publish，也不借 `TimingEditCoordinator::sealVerified()`伪造尚未完成的post proof。`DualSemanticReadView`只暴露按NodeKey/ArcKey/net/library语义查询的committed graph/input事实，禁止用functional projection、timing或fresh oracle作为preparer输入。raw candidate checks仍由isolated apply权威验证。

post-candidate builder只能消费 `PendingStructuredBatch&&` 与candidate-bound typed capture，构造 `VerifiedStructuredBatch`；它从validated slot plan、staged resolver和capture双射生成descriptor内typed `ArcGroupIndexDelta`，后者覆盖每个append/deactivate/rekey ArcId的StableArcRef与expected/replacement active key。Verified capability整体持有unsealed batch、staged resolver、descriptor与exact-before。transaction staging只接收其rvalue；先由core updater同步stage graph/index并验index↔graph，再由native/transaction resolver validator验index delta↔staged resolver，全部通过后才私有构造`DualCsrVerifiedStage`。删除公开raw staging入口；exact typed before-state和move ownership就是授权边界，不增加hash或nonce。

`AffectedCapturePlan`必须绑定session、generation、before/after high-water、normalized edits、slot plan、materialization与invalidation closure；只能携带stable refs、exact current-before key、`ArcKeyBase`和 `expected_post_multiplicity`，不得预言post ordinal，也不得跨candidate GraphBuilder保存native pointer、iterator、arc slot或traversal rank。`StableArcRef`只通过resolver slot稳定标识logical `ArcId`；历史ordinal不是当前active `ArcKey`的权威来源。任何改变同一base active multiplicity的edit必须覆盖完整post active group。post-candidate capture在局部candidate native遍历顺序上调用与fresh exporter同一个 `csr::assignParallelOrdinals`；其返回值是post canonical key的唯一authority。builder再验证完整group、连续`0..N-1`、`StableArcRef↔ArcId↔candidate record/payload`逐项双射及plan multiplicity，禁止preparer按另一种排序先写 `expected_key`。logical deactivation没有post active key，仍以exact committed-before key/endpoints/payload验证before事实；inactive历史payload不得占用active keyed lookup。

narrow reader只在执行后的candidate局部受影响node/net邻接中重新解析canonical key：append/payload-change/present arc通常要求1，logical deactivation要求0；统一拒绝actual multiplicity不等于计划值，并拒绝active ordinal不连续、重复ID/key、遗漏peer或replay。DB-free committed `DualCsrArcGroupIndex`绑定session/generation/ArcId high-water，保存ArcId slot→StableArcRef/current active key及ArcKeyBase→active ArcId group。generation0由native adapter从完整baseline resolver一次生成typed bindings，core只对graph验证并构造index；正常batch由updater只按verified `ArcGroupIndexDelta`演化。core validator只验index↔DualCsrState及session/generation/high-water/key/group，不include resolver；`DualCsrArcGroupResolverValidation`归native/transaction，以已验证exact-before为归纳前提，仅核对delta slots、append range与staged resolver，baseline/recovery full check单列且不计入targeted。preparer只读index affected bases；candidate侧batch-local collector只读对应局部native adjacency。selection/capture不得全扫resolver或native E；DB-free state/index完整性遍历不伪装成narrow native capture。其余payload覆盖与NoParasitic policy不变。

`CanonicalTimingRecordProjector`从实际owner抽取逐字段函数：`TimingGraphCsrAdapter.cpp`的NodeRecord、`TimingGraphCsrArcExport.cpp`的ArcKey、`CsrClockSeedExport.cpp:419–443`的eligibility、`CsrLoadExport.cpp`的no-parasitic load、`CsrLibertyExport.cpp`的transfer/library，以及 `CsrReferenceInputAdapter.cpp`的reference delta。声明集中到 `CanonicalTimingRecordProjectorInternal.hpp`；full exporter与narrow reader共同调用同一projector。new node/instance/arc与reconnect `net_name`也走该路径，禁止复制匿名转换逻辑。`NativeDualCsrPayloadCapture`不得调用full graph/reference export；native pointer、iterator、volatile rank cache及oracle数据不得进入descriptor或DB-free target。

每个完整正常batch的 `native_full_reference_export_count == 0`、`host_snapshot_rebuild_count == 0`、`baseline_factory_count == 0`。最小真实机制是在 `exportCsrReferenceInputCandidate` 实际入口使用thread-local scoped operation counter；`buildCsrSessionSnapshot`必经该入口，因此无需另造hash/count协议。capture audit对node/instance/arc/deactivation/load/library/cap/role每类分别冻结 `requested/read/accepted`：`accepted`必须与plan key逐项双射，deactivation另以committed-before read逐项闭合；局部邻接raw `read`可为request的有界superset，但必须报告index group lookup、candidate neighbor reads及上界。partial-fanout canary证明未扫描全resolver或全E；禁止用默认0或强行相等计数自证。fresh oracle独立进程允许full export，但计数和耗时只存在oracle envelope。

### 3.4 新增 Stage 5-owned事务、trace与测试 adapter

```text
src/operation/iSTA/source/module/timing_dual_csr_transaction/
  CMakeLists.txt
  CommittedDualCsrAnalysisState.{hpp,cpp}
  DualCsrTransactionCoordinator.{hpp,cpp}
  DualCsrExactReceipt.{hpp,cpp}

src/operation/iSTA/benchmark/dual_csr/
  CMakeLists.txt
  DualCsrTraceReplayer.{hpp,cpp}
  DualCsrReplayTypes.hpp

src/operation/iSTA/test/
  DualCsrTests.cmake

src/operation/iSTA/test/timing_dual_csr/
  DualCsrDescriptorContractTest.cpp
  DualCsrUpdaterContractTest.cpp
  DualCsrStateInvariantTest.cpp
  DualCsrPropertyTest.cpp
  DualCsrRollbackTest.cpp
  DualCsrTimingGateTest.cpp
  DualCsrFunctionalProjectionTest.cpp
  DualCsrTraceProductionFreshProbe.cpp
  DualCsrTraceProductionFreshAdapter.{hpp,cpp}
  CheckDualCsrStage5Isolation.cmake
  dual_csr_trace_controller.py
  fixtures/paper_aux_overflow.{json,expected.json}
```

Targets固定为：

```text
ista_timing_dual_csr_transaction
  public links = ista_timing_dual_csr, ista_timing_dual_csr_native,
                 ista_timing_edit_contract
  private links = ista_timing_edit_transaction

ista_dual_csr_trace_runtime
  public links = ista_timing_dual_csr, ista_timing_dual_csr_native,
                 ista_timing_dual_csr_transaction, ista_buffer_trace_contract
  private links = ista_timing_edit_transaction, ista_timing_database_headers

ista_dual_csr_production_fresh_probe
  test-only exact-inventory executable；允许复编既有 guarded fresh loader/
  native oracle support，但这些test seam不得进入任一library
```

Stage 5不修改或重命名 `ista_buffer_trace_contract`、`ista_buffer_trace_runtime`及Stage 4 probe；新replayer消费同一 `ReplayProgram`，默认Stage 4 full lane继续原样存在。

### 3.5 精确修改文件与冻结边界

```text
src/operation/iSTA/CMakeLists.txt
  + benchmark/dual_csr subdirectory

src/operation/iSTA/source/module/CMakeLists.txt
src/operation/iSTA/source/data_manager/adapter/csr/
  CMakeLists.txt
  TimingGraphCsrAdapter.cpp
  TimingGraphCsrArcExport.cpp
  CsrClockSeedExport.cpp（抽取419–443的eligibility projector调用）
  CsrLoadExport.cpp
  CsrLibertyExport.cpp
  CsrReferenceInputAdapter.cpp
  TimingGraphCsrAdapterInternal.hpp
  CsrReferenceInputAdapterInternal.hpp
  CanonicalTimingRecordProjectorInternal.hpp
  + 从上述实际owner抽取CanonicalTimingRecordProjector；full exporter与narrow reader
    共用逐字段函数，不复制匿名实现

  + timing_dual_csr、timing_dual_csr_native、timing_dual_csr_transaction subdirectories；
    ista_module不公开链接这些实验targets

src/operation/iSTA/source/module/timing_csr/
  CMakeLists.txt
  CsrFifoLevelization.{hpp,cpp}
  CsrCpuReferenceBackend.{hpp,cpp}
  CsrCpuReferenceBackendInternal.hpp
  CsrCpuReferenceResultInitialization.cpp
  CsrCpuReferenceArcTransfer.cpp
  CsrCpuReferenceForwardPropagation.cpp
  CsrCpuReferenceRequiredPropagation.cpp
  + generic view入口与flat实现；现有 CsrReferenceInput API仅作flat wrapper

src/operation/iSTA/test/CMakeLists.txt
  + include(DualCsrTests.cmake)

```

冻结边界是硬约束：不得修改任何Stage 3/4 source、CMake或test，包括既有 `timing_edit_transaction`、adapter、`TimingEditTests.cmake`、buffer trace runtime/probe。Stage 5通过新targets组合既有公开contract。Stage 2 `timing_csr`的generic化只更新精确source/object/link事实；不得用glob、数量下限或hash绕过。

## 4. 所有权与公开边界

### 4.1 DB-free core拥有

- Dual-CSR committed/staged values；
- descriptor schema、排序、冲突检查与application phases；
- Base/Aux/transpose/capacity/tombstone invariants；
- `ActiveCsrEdgeView`/`TimingPayloadView`的Dual实现；
- field-level functional projection、telemetry及随descriptor增量演化的committed `DualCsrArcGroupIndex`。

### 4.2 Native adapter拥有

- 从candidate Database中按stable semantic ref定位受影响对象；
- 构造new node/instance/arc/library/cap/load/delay payload；
- 验证clock/library/corner/parasitic等不允许变化的上下文；
- 为prepared invalidation closure重新读取受影响payload。

adapter不拥有persistent Dual-CSR，不publish，不执行selector，不生成fresh答案。

### 4.3 Transaction coordinator拥有

Stage 5-owned `DualCsrTransactionCoordinator`只拥有并原子发布 `DualCsrState + DualCsrTimingResult + TimingEditResolverState + DualCsrArcGroupIndex + identity + generation + descriptor_trace + semantic_trace + traversal_telemetry`。preparer只读aggregate内resolver/index；这九项全部参加同一次staged `noexcept swap`，fresh recovery也必须重建、验证并一次交换完整aggregate。coordinator不拥有、不commit native Database；installed candidate只是累计prefix的隔离执行与窄capture载体，最终及任一失败路径都必须rollback到baseline。Stage 10才处理native/cross-layer publish。

### 4.4 Test adapter拥有

- one-shot production fresh loader；
- fresh CPU/full oracle进程；
- trace fixture/materialization、run envelope与JSON receipt；
- fault injection、full-export call counter与错误样本。

test adapter不能mint production publish capability。production publish只依赖candidate capture、descriptor/state/timing intrinsic validators；targeted与fresh分别输出sealed receipt，controller在进程外产生test-only `DifferentialVerdict`。verdict是阶段验收证据，不进入production transaction授权，也不携带native pointer或可重放timing答案。

## 5. State、descriptor与view类型

### 5.1 State

```cpp
struct BaseCsrState {
  std::vector<std::uint64_t> row_offsets;
  std::vector<std::optional<csr::ArcId>> physical_slots;
  csr::CsrBufferExtent offsets_extent;
  csr::CsrBufferExtent edge_extent;
};

struct AuxOutCsrState {
  std::vector<std::uint64_t> row_offsets;
  std::vector<csr::NodeId> row_sources;
  std::vector<csr::ArcId> arc_ids;
  std::vector<std::int64_t> source_to_aux_row;
  csr::CsrBufferExtent offsets_extent;
  csr::CsrBufferExtent edge_extent;
};


struct DualCsrArcSlot {
  csr::ArcSemanticPayload payload;
  bool active{false};
};

struct DualCsrTimingResult {
  csr::CsrTimingResult values;
  std::vector<std::uint8_t> active_arc_mask;
};

struct DualCsrState {
  timing_edit::TimingEditSessionToken session_token;
  timing_edit::TransactionGeneration generation;
  std::vector<csr::NodeRecord> nodes;
  std::vector<DualCsrArcSlot> arc_slots;
  BaseCsrState base_out;
  BaseCsrState base_in;
  AuxOutCsrState aux_out;
  DualCsrReferencePayload reference_payload;
  DualCsrTelemetry telemetry;
};
```

`row_offsets.back()`等于physical array size，不等于capacity。Base physical size包含tombstone；logical edge count只数active ArcId。baseline旧row的 `[begin,end)` 区间终身不扩张；global vector `capacity()`只表示allocator reserve，绝不是某row可占用空间。旧source在本row无tombstone时新增forward arc只能进入Aux；new node rows及其Base slots在所有旧row之后尾部append。Aux为packed rows，不保存reverse edge或tombstone。node deletion、ID reuse、Base compaction与general AuxIn均不在本阶段。

`DualCsrState`只保存graph与timing-input payload，不保存任何运行结果。arc slot直接保存generic contract唯一的 `csr::ArcSemanticPayload`；该类型不含 `id`或volatile `native_traversal_rank`，ArcId由stable slot给出。Dual层不得复制字段重叠的payload struct。new child node在append前的BaseOut/BaseIn row均为空，append arc后只有合法incoming slot。`DualCsrStateValidator`验证payload、active adjacency、transpose、child empty-row演化及high-water一致性。

`DualCsrReferencePayload`保存full backend需要、但不属于physical adjacency的analysis context、instances、constraints、library models、clock ownership、parasitics、start seeds、required、pin capacitance和unsupported reasons。node-indexed字段随append range增长；未声明字段必须保持逐值不变。

`DualCsrTimingResult`只在direct-view propagation完成后生成并独立验证。`values`复用现有 `csr::CsrTimingResult`，各node/path/clock/arc SoA按stable IDs展开；inactive arc的 `active_arc_mask[id]==0`，ArcResultSoa的 `delays/min_delays/max_delays/transition_delays/input_output_delays/graph_delays/transition_types`各OptionalSoa lane均为 `presence=0` 且写入该类型canonical default，`timing_arc_row_offsets[id] == timing_arc_row_offsets[id+1]`且无child index/delay/fallback entry；禁止写 `std::nullopt` 伪装SoA存储。

### 5.2 Descriptor

```cpp
struct NodeAppendRecord {
  csr::NodeId id;
  csr::NodeKey key;
  csr::NodeRecord payload;
};

struct ArcAppendRecord {
  csr::ArcId id;
  csr::ArcKey key;
  csr::NodeId source;
  csr::NodeId sink;
  csr::ArcSemanticPayload payload;
};

struct NodePayloadChange {
  csr::NodeId id;
  csr::NodeKey expected_key;
  std::string expected_net_name;
  std::string replacement_net_name;
};

struct ArcGroupIndexDelta {
  csr::ArcId id;
  timing_edit::StableArcRef ref;
  std::optional<csr::ArcKey> expected_active_key;
  std::optional<csr::ArcKey> replacement_active_key;
};

struct DualCsrBatchDescriptor {
  std::string schema{"ista-dual-csr-update/1.2.0"};
  TimingEditSessionToken session_token;
  TransactionGeneration expected_generation;
  TransactionGeneration target_generation;
  AppendOnlyHighWater before;
  AppendOnlyHighWater after;
  std::vector<NodeAppendRecord> node_appends;
  std::vector<ArcAppendRecord> arc_appends;
  std::vector<NodePayloadChange> node_payload_changes;
  std::vector<BaseOutRemoveDescriptor> removes;
  std::vector<BaseOutChangeDescriptor> changes;
  std::vector<BaseInChangeDescriptor> reverse_changes;
  std::vector<ArcPayloadChangeDescriptor> payload_changes;
  std::vector<LogicalArcDeactivate> logical_deactivations;
  std::vector<AuxOutRowDescriptor> aux_rows;
  std::vector<AppendedBaseOutRowDescriptor>
      appended_base_out_rows;
  std::vector<AffectedBaseOutRowDescriptor>
      affected_base_out_rows;
  std::vector<AffectedBaseInRowDescriptor>
      affected_base_in_rows;
  DualCsrReferencePayloadDelta reference_payload;
  std::vector<ArcGroupIndexDelta> arc_group_index_delta;
};
```

`node_appends`与`arc_appends`必须逐ID完整覆盖各自 `[before,after)`，每条携带semantic key、endpoints及完整payload；range只从首尾推导。`arc_group_index_delta`与所有append/deactivate/rekey ArcId逐项双射：append为null→post key，deactivate为before→null，rekey为before→post；StableArcRef必须等于verified slot plan/staged resolver binding，未变ArcId不得出现。`NodePayloadChange`只允许reconnect的net_name；load/cap/seed/eligibility进入typed reference或Arc payload delta。每个logical deactivate显式记录ArcId/key/endpoints/reason/expected active；未列字段严格不变。

- `remove`记录source row、physical slot和expected old ArcId，post slot为tombstone；
- `change`记录source row、physical slot、expected old/tombstone和replacement post-active ArcId；replacement可以是为FIFO完整重写而移动的survivor，也可以是本批append ArcId；
- `reverse_change`记录sink row、BaseIn physical slot、expected old和replacement ArcId；
- `append`精确覆盖 `[before, after)`，无洞、重复或乱序；
- `payload_change`保持ArcId、ArcKeyBase、source、sink与kind；delay/load/eligibility只允许声明字段变化。只有在同一base完整post active group已被capture/descriptor覆盖并证明时，replacement才可把parallel ordinal改为该组canonical `0..N-1`，其余ArcKey字段不得变化；
- `aux_rows`给出affected existing source的完整post-state overflow ArcId集合，不接收reverse entries；
- `appended_base_out_rows`逐new source记录candidate native outgoing FIFO；`affected_base_out_rows`逐existing source记录committed `BaseOut`非空physical slot后接`AuxOut`的完整expected行与candidate native完整replacement行；`affected_base_in_rows`逐sink记录committed `BaseIn` physical expected行（new sink必须为空）与candidate native replacement行；三者按NodeId唯一有序且ArcId双射覆盖对应active adjacency；
- updater对affected old source不保留旧survivor位置偏好：按固定Base physical slot顺序把replacement前`min(Base槽数, 行长)`条通过exact remove/change/move写回，剩余项进入Aux；BaseIn同样按完整replacement FIFO重写且本阶段不允许AuxIn。同一physical slot不能同时remove/change，同一reverse slot只能写一次。

reference delta必须声明字段语义、目标ID、expected-before、replacement与optional presence；禁止opaque blob、native pointer或由fresh oracle回填。core descriptor validator验证index delta内部唯一性、expected/replacement key与对应graph delta闭合、deactivate与physical delta一一闭合、append key/ID顺序、high-water和payload mask；resolver-side StableArcRef真实性只由native/transaction validator核对，避免core反向依赖resolver。

### 5.3 Direct edge/timing view

```cpp
enum class EdgeStorageKind { kBaseOut, kAuxOut, kBaseIn };
enum class EdgeVisitControl { kContinue, kStop, kError };

struct EdgeEntry {
  ArcId arc_id;
  EdgeStorageKind storage_kind;
};

struct EdgeVisitResult {
  EdgeVisitControl control;
  std::optional<CsrViewError> error;
};

class ActiveCsrEdgeView {
 public:
  std::size_t nodeCount() const;
  std::size_t arcSlotCount() const;
  std::size_t activeArcCount() const;
  bool isActive(ArcId) const;
  ExpectedRef<const ArcSemanticPayload, CsrViewError> arc(ArcId) const;
  EdgeVisitResult forEachActiveArc(EdgeVisitor) const;
  EdgeVisitResult forEachOutgoing(NodeId, EdgeVisitor) const;
  EdgeVisitResult forEachIncoming(NodeId, EdgeVisitor) const;
};
```

每次callback接收同时携带stable `ArcId`与 `EdgeStorageKind`的 `EdgeEntry`，返回Continue/Stop/Error；Error必须携typed `CsrViewError`。`arc(id)`对inactive/tombstoned/out-of-range ID返回typed precondition failure，禁止返回陈旧payload、optional空引用或触发未定义行为。

generic contract另有 `TimingPayloadView`，按stable NodeId/ArcId返回payload与optional timing lanes；`FlatCsr*View`和`DualCsr*ViewImpl`各自实现。Dual view不得持久化、导出或比较volatile `native_traversal_rank`，也不得在构造时把全图复制、排序或decode成另一份flat adjacency。

遍历序以被测存储的物理行序为准，而不是按 `ArcKey` 重新排序：`forEachOutgoing()`先按BaseOut物理slot顺序跳过tombstone，再按该source映射的AuxOut `arc_ids`顺序访问；`forEachIncoming()`按BaseIn物理slot顺序访问。generation-0 flat/fresh构造保留其native adjacency行序，targeted更新必须通过descriptor精确维护与fresh相同的行序。`ArcKey` canonicalization只用于stable语义身份、parallel ordinal及进程外字段比较，不得改变实际FIFO/propagation访问顺序。equal-cost predecessor允许不同dense winner，但映射到NodeKey/ArcKey后必须属于同一规范等价winner集合。

`forEachOutgoing()`必须在同一次访问中直接合并BaseOut与AuxOut；`forEachIncoming()`只直接读取BaseIn。任一callback Stop/Error立即短路，Base返回Stop时不得进入Aux；malformed row endpoint、source-to-Aux-row双向映射、inactive arc或越界必须返回typed failure。levelization根据payload eligibility过滤；disabled、loop-disabled和non-propagating语义来自payload，不由storage位置猜测。

Stage 5严禁先把Dual-CSR decode成flat adjacency再交给旧backend，也严禁在view构造时以全N/E预扫描或全边副本掩盖该decode。允许生成canonical projection用于诊断/fresh comparison，但四阶段 `levelization`、`arc_initialization`、`forward_propagation`、`required_propagation`必须各自通过generic view真实遍历。每阶段分别累计 `{base_out_visits, aux_out_visits, base_in_visits}`，测试要求符合该阶段方向且Aux arc在所有应访问阶段均有非零计数。

## 6. 首版算法解释与不变量

论文 Algorithms 1–4 的伪代码只作为输入，不照抄疑似笔误。首版顺序固定为：

1. validate descriptor envelope、generation、ranges、typed index delta与冲突；
2. clone/copy-on-write detached state并完成所需capacity grow；
3. deactivate removed logical ArcIds；
4. apply BaseOut change/remove；
5. apply BaseIn reverse replacement；
6. append node/arc records和new-node Base rows；
7. rebuild affected AuxOut rows及mapping；
8. apply node/arc payload、reference deltas与ArcGroupIndexDelta；
9. core验证graph/input/direct view/transpose/index，native/transaction验证index delta↔staged resolver；
10. 交给full levelization/propagation，生成并完成独立 `DualCsrTimingResult` intrinsic validation；
11. mint `DualCsrVerifiedStage`，noexcept publish Stage 5 aggregate；
12. 生成该批sealed functional/structural observation；publish成功后立即清空该批pending descriptor owner；
13. prefix/run结束后rollback installed candidate并完成transaction receipt；targeted/fresh均输出最终sealed receipts后，外部controller才生成 `DifferentialVerdict`。

必须冻结为命名回归：

- `ReplacementValueCapturedBeforePendingPop`：修复Algorithm 2先pop再读back；
- `ReversePairingIsByDestinationAndArcIdentity`：不按未证明等长的vector index配对；
- `AuxOffsetsArePerAuxRow`：Algorithm 3 offset按row，不按edge push；
- `AuxContainsForwardEdgesOnly`：不把`inserted_revedges`混入AuxOut；
- `ReverseChangeTargetsBaseIn`：Algorithm 4 reverse change写BaseIn；
- `PendingBuffersClearOnlyAfterCommit`：失败/rollback不丢persistent Aux edge。

每个committed state必须满足：

- BaseOut/BaseIn offsets均为`V+1`、首项0、单调、末项等于physical size；
- Aux offsets为`aux_rows+1`，mapping与row_sources严格互逆；
- active ArcId在`BaseOut∪AuxOut`恰好一次，在BaseIn恰好一次；
- active ArcKey全局唯一；每个active ArcKeyBase group必须在candidate局部native顺序上经共享 `csr::assignParallelOrdinals` 获得连续 `0..N-1`，fresh compact rebuild调用同一函数并得到同一组 `record/payload→key` 绑定；
- outgoing/incoming的ArcId、source、sink和完整payload严格转置；
- inactive ArcId不出现在任何active adjacency；
- inactive slot保留historical payload/key供rollback审计，其historical ordinal可以不连续，也可以与当前active key重复；`ActiveCsrEdgeView::arc`与`DualSemanticReadView::arcById`均拒绝inactive，历史只能经显式structural-state/`historicalArcById`审计API读取；按ArcKey查询只搜索active arcs；
- physical tombstone可复用，logical ArcId永不复用或复活；
- baseline旧row区间永不扩张，allocator reserve不改变row ownership；
- 无tombstone的旧source新增走Aux，new-node rows和Base slots只在全局尾部append；
- inactive timing result lane为presence=0+canonical default且child row empty；new child graph row演化可验证；
- Aux row内无reverse edge、重复ArcId或错误source；
- commit后pending buffers为空，先前persistent Aux edge除非有明确remove否则不丢失；
- clock/library/corner/parasitic exact typed context/value变化按policy error/full-with-record，本阶段correctness case不fallback；rank-free component fingerprint仅作诊断，只有解析出真实字段或ownership变化才阻断。

Capacity grow使用确定性策略，例如`max(required, max(1, 2*old_capacity))`。所有allocation在detached state完成；`std::vector::capacity()`不作为跨实现golden，只验`required <= declared capacity`、内容和telemetry。compaction/tombstone reclamation明确推迟。

## 7. 真实数据流与full-export隔离

```text
fresh process / operation guard
  -> generation-0 native CPU/full + one-time CsrReferenceInput export
  -> initialize DualCsrState(g=0)
  -> for each frozen semantic batch/prefix
       pre-candidate: semantic plan + committed resolver/keyed view/arc-group index + exact graph/identity
       -> PendingStructuredBatch(unsealed batch + staged resolver + capture plan + exact before)
       -> if committed generation == 0: NativeDatabaseCandidate::create(baseline)
       -> else: clone current installed cumulative raw candidate
                -> rollback installed current candidate to baseline
       -> apply/execute PreparedBatch on raw candidate, then install as isolated carrier
       -> post-candidate narrow reader按affected-base index局部读取，并以共享assignParallelOrdinals确定post key
       -> builder验证完整group与ref/id/record/payload双射，mint VerifiedStructuredBatch
       -> detached DualCsrUpdater::stage(g -> g+1)
       -> validate state + ActiveCsrEdgeView/Dual implementation
       -> full CPU levelization directly over BaseOut∪AuxOut/BaseIn
       -> full CPU forward/required propagation -> DualCsrTimingResult
       -> invariant validation -> independent verify -> mint DualCsrVerifiedStage
       -> atomic publish graph/timing/resolver/arc-group index/identity/generation/traces/telemetry
       -> seal per-batch functional/structural observation，累计transaction payload
       -> publish成功后清空该批pending descriptor owner
  -> final rollback installed cumulative candidate to baseline
  -> finalize transaction receipt and run envelope
  -> emit final sealed targeted receipts；外部controller等待targeted/fresh两侧完成后比较
```

每batch transaction `phase_trace` 固定为 `pre_candidate_prepare`、`candidate_apply_execute`、`post_candidate_capture`、`dual_csr_update`、`full_levelization`、`full_propagation`、`intrinsic_verify`、`publish`八阶段；phase timing则将校验拆成 `invariant_ms` 与 `verify_ms`，因此固定为九个独立计时字段。run-final cleanup trace另记一次 `native_final_rollback`，不得伪装成每batch phase。runtime counter断言targeted batch区间：

- native full CSR/reference export调用0次；
- full host snapshot rebuild调用0次；
- fallback 0次；
- `incremental_batch_executed=true`；
- `propagation_scope=full_graph`。

每个prefix固定三个独立进程角色：

1. `targeted-under-test`：从baseline artifact和semantic prefix运行structured preparer、Dual update及direct-view timing，输出typed receipt；
2. `fresh-oracle`：从原始设计累计重放prefix并执行native CPU/full，输出semantic receipt；
3. `controller-comparator`：只读取两份sealed functional receipt，逐字段比较并产生test-only `DifferentialVerdict`；另分别验证targeted structural/transaction receipt。

oracle的graph、dense IDs、timing、predecessor选择、payload或projection不得进入targeted进程的 `PreparedBatch`、descriptor、resolver或state。进程间只交换输入artifact identity、semantic prefix identity与最终sealed receipts。oracle时间单列，不计入任何incremental样本。

## 8. 事务、rollback、publish与recovery

Stage 5 committed aggregate精确为 `DualCsrState + DualCsrTimingResult + TimingEditResolverState + DualCsrArcGroupIndex + identity + generation + descriptor_trace + semantic_trace + traversal_telemetry`；唯一可见性动作是九项staged `noexcept swap(committed, staged)`，rollback/recovery不得遗漏index或任一其它字段。native Database、installed candidate和device marker不在aggregate，Stage 5不执行native commit。所有可能抛异常的prepare、candidate create/clone、apply/execute、capture、allocation、update/index update、intrinsic validation、四阶段timing、publish capability及可预计算receipt payload均在swap前完成；fresh oracle和外部differential不参与production swap授权。publish后的observation/序列化失败不能撤销完整aggregate，只令run terminal且不能产出成功验收证据。

Stage 5 identity以rank-free semantic projection为权威：exact `instances/nets/NodeKey/active ArcKey`记录和逐字段functional receipt是主证据；component fingerprints只对同一rank-free projection作辅助完整性绑定。不得把fresh dense ID、`native_traversal_rank`或raw CSR fingerprint相等设为功能验收门。generation 0可来自一次full export；后续generation由verified descriptor的post semantic state确定性投影，fresh process也先做相同semantic normalization再比较。Stage 5的move-only verified capability取代 `PreparedBatch::seal()`作为batch—capture—descriptor—staged state的生产授权；任何可公开拼装descriptor再直接staging的入口都必须删除。

实现顺序固定为：`PendingStructuredBatch` → isolated candidate apply/execute → typed narrow capture → `VerifiedStructuredBatch` → staged graph/direct-view timing/intrinsic validators → `DualCsrVerifiedStage` → single `noexcept swap` → sealed functional/structural observation → clear batch pending owner → run-final rollback → finalized transaction receipt/run envelope → targeted/fresh两侧sealed output → 外部fresh test verdict。因此post identity不要求也不允许在narrow capture前通过full native re-export获得。

多batch native载体协议不可省略：committed generation 0的首批从active baseline直接 `NativeDatabaseCandidate::create(baseline)`，此时没有installed candidate可clone/rollback；首批apply/execute/install后，后续批才clone current installed cumulative raw candidate，clone成功后rollback current installed到baseline，再在clone上apply下一 `PreparedBatch`、execute/install并按capture plan窄读。正常结束最终rollback到baseline。prepare/create/clone/rollback/apply/execute/install/capture任一步失败也必须rollback；rollback失败poison test session。candidate ownership不得进入Stage 5 aggregate，也不得调用Stage 3 native publish。

任一batch失败后先rollback到baseline，并把该targeted one-shot run置为terminal/recovery-required，禁止假定generation>0 cumulative carrier仍存在而继续或原地重试；只有从baseline + committed semantic trace显式重建cumulative carrier并通过验证后才能启动新的run。swap前失败丢弃staged aggregate，committed g逐字段不变；swap后failpoint只能留下完整g+1再poison。fresh recovery从baseline artifacts加累计semantic trace重建DualCSR/timing/resolver/identity/generation/trace，并以同一次noexcept swap发布；native仍只按上述隔离载体协议重放并最终rollback。恢复full rebuild单独计数，不计入targeted性能。Stage 10才定义native与cross-layer atomic publish。

## 9. 功能主验收门

### 9.1 Frozen trace gate

对Stage 4两个冻结artifact的每个prefix至少运行三个独立one-shot fresh process：

- `synthetic_two_batch`：2 batches、3 edits；
- `real_buffer_fanout`：1 batch、4 edits。

每批比较：

- instances/nets/nodes与semantic keys；
- active arcs、parallel ordinal、source/sink/kind；
-完整ArcRecord transfer、eligibility、delay和output load；
- constraints、library models、clock ownership、parasitics、start/required/cap payload；
- level membership、`node_to_level`与timing order；
- node/clock/data/path/arc SoA的presence与value；
- predecessor NodeId/ArcId先映射为NodeKey/ArcKey后比较；
- prefix generation；targeted/fresh各自内部session binding，不比较跨进程raw session token。

fresh full使用compact session-local IDs，DualCSR使用stable IDs/tombstones，因此禁止raw vector equality冒充语义比较。`FunctionalSemanticReceipt`（即 `DualCsrFunctionalProjection` 加timing投影）只含active nodes/arcs、reference payload及全部level/timing/path语义；所有ID-bearing字段按NodeKey/ArcKey canonical remap，类型中不含真实session/generation/stable high-water/raw fingerprint/physical tombstone。数值沿用Stage 2已冻结 tolerance，结构/枚举/presence严格相等。

`DualCsrStructuralReceipt`单独记录logical inactive ArcKey、stable ArcId/high-water、BaseOut/BaseIn/Aux physical slots、capacity与tombstone invariants，并由prior committed state、resolver、verified descriptor/semantic trace验证，不与fresh compact graph直接比较。schema `ista-dual-csr-exact-receipt/1.3.0` 的 `TransactionReceipt`记录真实session、generation、generation-0完整typed `CsrReferenceInput`锚点、rank-free identity、descriptor/semantic trace、batch phase、run-final cleanup、fallback与operation counters；controller从最终functional/reference按descriptor反向重放到首批expected后，必须与该full typed anchor逐字段相等，hash只作辅助。总envelope可聚合三者，但controller只跨fresh比较functional子receipt；structural/transaction分别做本进程内部的语义与事务验证。

swap前只预计算receipt payload；functional/structural observation在publish后封口，transaction receipt必须等run-final rollback后完成。任何receipt封口或序列化失败都不会回滚已完整publish的aggregate，而是令run terminal并禁止生成成功的 `DifferentialVerdict`。

### 9.2 Stage 4 frozen traces为何不产生Aux

每个 `BufferInsertionMutation` 对current driver row删除`k=|moved_sinks|>=1`条`driver→sink`，新增恰好1条`driver→buffer input`，净增`1-k<=0`；buffer output属于new NodeId，其outgoing随new Base row append。因此正确的same-batch slot replacement下，两个Stage 4 frozen traces的AuxOut均应为0。

不得通过放弃可用tombstone、调换phase、伪造capacity或把reverse edge塞入Aux来制造覆盖。Stage 4 trace gate证明真实buffer workload的targeted Base update、多batch、reverse replacement和timing等价；不谎称它覆盖Aux overflow。

### 9.3 独立 Stage 5-only Aux microcase

新增 `paper_aux_overflow` DB-free algorithm fixture：baseline为supported DAG，第一批append new node/arc，并从无可复用tombstone的existing source新增old→new forward edge；incoming落入new-node BaseIn row，forward必须进入AuxOut。第二批再append一个new source及其forward arc，以 `new_source→old_sink` 一对一替换原incoming BaseIn slot，同时显式logical-deactivate并清除第一批旧Aux arc；不使用本阶段未支持的pure remove。

它是Algorithms 1–4 storage microcase，不进入Stage 4 manifest、不声称是production buffer insertion或real physical design。功能门要求：

- first batch `aux_rows==1 && aux_edges==1`，mapping精确；
- Aux edge是唯一能使new endpoint可达并获得finite arrival/slack的路径；
- levelizer、arc initialization、forward和required propagation各自记录该ArcId的`kAuxOut` visit；
- 若test-only negative candidate省略该Aux edge，processed count或timing receipt按预期不同；
- second batch证明new-source Base row尾部append、旧incoming slot replacement、旧Aux logical deactivate；随后旧Aux row清空且mapping回`-1`；
- 两批均与独立canonical full oracle逐语义字段等价。

## 10. 测试矩阵

| 层 | 必测内容 | 建议标签 |
|---|---|---|
| descriptor unit | schema/generation/range/order、remove/change/reverse冲突、parallel ArcId、完整base-group重编号、遗漏peer拒绝；同base不同payload且candidate native-order变化时共享ordinal函数保持record/payload→key绑定与fresh一致 | `ista_unit;ista_dual_csr` |
| state unit | empty/singleton/chain/diamond、Base offsets、transpose、disabled/loop-disabled、tombstone reuse | `ista_unit;ista_dual_csr` |
| Aux unit | multi-source rows、mapping inverse、overflow/persist/clear、forward-only | `ista_unit;ista_dual_csr` |
| capacity unit | zero/exact/不足capacity、各buffer grow、allocation failure无写 | `ista_unit;ista_dual_csr` |
| property | randomized DAG/descriptors、多batch、parallel arcs、partial-group deactivate后active重编号、fresh canonical apply differential | `ista_unit;ista_property;ista_dual_csr` |
| rollback | pre/post-candidate各phase、累计candidate clone→rollback→apply/install、final/failure rollback、Dual aggregate swap/recovery | `ista_unit;ista_dual_csr` |
| direct timing | Base-only与Aux-only路径均被full levelizer/propagator真实读取 | `ista_unit;ista_dual_csr` |
| stable timing | inactive lane absent/default、historical key可与active current key重复、active/history API隔离、child empty row、shared native-order ArcKey、equal-cost等价winner | `ista_unit;ista_dual_csr` |
| frozen synthetic | 2 batches/3 edits，每prefix targeted/fresh逐字段等价 | `ista_integration;ista_cpu;ista_dual_csr` |
| frozen real | 1 batch/4 edits，targeted/fresh逐字段等价 | `ista_integration;ista_cpu;ista_dual_csr` |
| source isolation | core index↔state与native delta↔resolver分层、九项swap/recovery、无full-export、index+candidate局部scan、各record class exact audit、exact source/link/options/object/nm | `ista_unit;ista_dual_csr` |
| public headers | include order、standalone compile、move/noexcept traits | `ista_unit;ista_dual_csr` |

Property seeds固定至少 `1, 7, 42, 20260901, 0xdeadbeef`。每个失败输出seed、descriptor和最小semantic graph；不以hash作为唯一复现材料。

回归顺序：

1. `ctest -R '^ista_(timing_)?dual_csr_' -E '^ista_dual_csr_release_timing_smoke$' --output-on-failure -j1`；
2. timing单独运行`ctest -R '^ista_dual_csr_release_timing_smoke$' --output-on-failure -j1`，不得在功能复跑中重复采样；
3. Stage 4 `^ista_buffer_`；
4. Stage 3 `^ista_timing_edit_`；
5. Stage 2 `^ista_csr_`，历史静态inventory限制与功能结果分列；
6. iSTA unit/property/integration/smoke labels；
7. parent冻结STA pytest与non-PDK全量。

## 11. Telemetry、memory与性能 smoke

每batch至少记录：

```text
generation_before / generation_after
logical_edges_before / logical_edges_after
base_physical_edges / base_active_edges / base_tombstones
tombstone_ratio
aux_rows / aux_edges
tombstone_reuse_count / base_change_count / reverse_change_count
nodes_appended / arcs_appended / payload_changes
capacity_grow_events（buffer、old、required、new）
aux_rebuild_count / full_rebuild_count
pre_candidate_prepare_ms / candidate_apply_execute_ms / post_candidate_capture_ms
dual_csr_update_ms / invariant_ms
full_levelization_ms / full_propagation_ms / verify_ms / publish_ms
fresh_oracle_ms（correctness-only）
requested/executed strategy、fallback、propagation_scope
四阶段各自 base_out/aux_out/base_in visit counters
```

静态证据分级固定：hash、raw object列表、depfile文本和source/object count inventory只用于定位构建漂移；它们单独失败时记录为辅助门禁差异，不能覆盖已经通过的逐语义字段功能结果，也不能据此宣称功能回归。若证据解析出真实forbidden link/include、DB-free target依赖native/Database、test seam泄漏production closure或其它所有权边界破坏，则按独立架构阻断处理，必须修复后才能完成Stage 5。

Capacity是元素槽数而非bytes；同时报告各vector estimated host bytes，但不得把allocator capacity当跨平台golden。physical/logical edge count、tombstone ratio、Aux size、grow/rebuild/fallback必须进入Stage 5报告。

性能只做smoke：Release、固定trace、warm-up后采集至少6次prepare/capture各phase与 `dual_csr_update_ms`，保存raw样本、环境指纹和phase trace。此数据只证明计时可运行、candidate最终rollback且targeted region无full export，不报告speedup、break-even或论文可比性；full vs incremental性能结论留到Stage 10。

## 12. 文件规模、构建与审查门

所有本阶段新增源/测试/脚本/文档严格少于700物理行。现有接近上限文件不得继续堆代码：`TimingEditValidation.cpp`为700行，`BufferTraceProductionFreshAdapter.cpp`、`BufferTraceContractTest.cpp`为699行，Stage 4 JSON/canonical实现为691/695行。coordinator若修改后接近上限，应把DualCSR receipt/bundle validation拆入新文件，不扩张单体。

所有C++ target使用 `-Wall -Wextra -Werror -pedantic -ffp-contract=off`。CMake冻结exact sources、direct links、compile options与DB-free closure；禁止glob和“至少N个对象”弱门禁。Python只用stdlib并设置`PYTHONDONTWRITEBYTECODE=1`，不改flake/lock/第三方依赖。

设计审查至少覆盖：

1. Algorithms 1–4解释、Aux microcase诚实性与descriptor schema；
2. DB-free/native/test ownership、direct-view backend与full-export隔离；
3. transaction/rollback/capacity/telemetry；
4. stable ArcId与active canonical ArcKey分离、parallel group完整重编号及inactive历史key语义；
5. functional differential和Stage 6 handoff。

设计审查未给出 `APPROVE` 前不编码。实现完成后另由未参与实现的subagent检查diff、运行tests并逐项核对本计划；blocker/major/minor全部闭合后才写Stage 5报告与commit。

## 13. 成功标准与停止条件
- 历轮findings均已逐项闭合：resolver同swap/recovery、generation-0 candidate create特例、projector实际owners、独立timing validator与view aliases归属。

全部满足才称阶段 5完成：

- generation 0只full export一次，正常batch targeted region full export/rebuild为0；
- immutable descriptors逐ID覆盖Node/Arc append、受限Node/Arc payload、logical deactivate、physical/reverse change、Aux row与typed reference delta；
- Base/Aux/tombstone/capacity/pending invariants全部通过；
- Stage 4两条frozen trace每batch的DualCSR state等于fresh canonical graph；
- full levelizer和full propagation直接遍历Base∪Aux/BaseIn，不走decode-flat被测路径；
- 每batch所有timing字段按semantic key与fresh CPU/full等价；
- Stage 5-only add-only microcase真实访问Aux并完成overflow/persist/clear；
- Stage 5 aggregate swap前故障0 writes visible，swap后故障留下完整g+1；native累计载体正常/失败均rollback baseline；
- correctness case无fallback，phase trace与telemetry完整；
- Stage 2–4及parent回归无功能退化；
- 独立代码审查 `APPROVE`，报告如实记录无speedup结论；
- child/parent按阶段边界本地提交，不push且不夹带用户已有修改。
- 每prefix三进程隔离成立，oracle数据未进入descriptor；正常batch full-export/full-rebuild计数均为0；

以下任一存在即停止并不得宣告完成：以Stage 4 buffer trace伪造Aux；targeted path仍full export；FunctionalProjection/oracle进入preparer；Stage 5 commit native；candidate未最终rollback；把physical slot当ArcId复用；Aux含reverse edge；只验证decoded graph不验证timing访问；只比较hash或raw dense IDs；忽略payload/optional presence/predecessor；silent fallback；aggregate部分发布；容量不足后部分写；用CPU mock替代真实Base∪Aux traversal。

## 14. 已闭合 blocker与Stage 6 handoff

设计复审findings已按最终冻结contract闭合；candidate clone→rollback→apply/install协议已由既有公开Stage 3 seam实现，冻结Stage 4源码无漂移。Aux路径由第9.3节合法add-only两批Stage 5 microcase实际覆盖，不修改Stage 4 frozen artifacts；最终全diff审查无remaining finding。

原实现风险均已按第3–8节闭合：generation-0 typed anchor保留flat authority，generic views解除backend对flat offsets的硬绑定，committed aggregate一次publish，affected payload经narrow native capture与verified descriptor进入production路径；test oracle未进入preparer或descriptor。

交给Stage 6的冻结API是generic `ActiveCsrEdgeView`/`TimingPayloadView`及Dual实现、append-only node high-water、active ArcId/payload访问、generation和telemetry，不暴露updater内部vectors或pending lists。Stage 6 mixed builder只能依赖：

```text
nodeCount / n_last_nodes
active arc source/sink/eligibility
forEachOutgoing(Base∪Aux) / forEachIncoming(BaseIn)
stable NodeId/ArcId
committed generation
```

Stage 6不得重新decode flat CSR、重建full native CSR或假定Aux为空。它在上述view之上构建actual/mixed ID和virtual level graph；Stage 5继续保留full levelization direct-view path作为独立correctness oracle。

Stage 10仍负责cross-layer IDB/physical integration、CUDA与正式性能结论；Stage 5不得为闭合native payload窄读而提前引入物理提交或跨层生命周期。
