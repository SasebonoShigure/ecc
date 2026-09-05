# ECC IncreGPUSTA 阶段 2 Step 7 详细实施计划

> 状态：v0.3 冻结候选；本文件 SHA 经原三路独立审查全部 APPROVE 后即原样冻结，审查期间不再编辑，尚未编码
> 基线：Stage 2 总计划 v0.10；Steps 1–6 已本地完成，Step 6 最终门禁与双路代码复审均通过
> 范围：真实 session token、Database-exclusive authority、generation-0 one-shot capture、ready/released observation、binding、parent transport、全 corner preflight 与隔离 sink
> 非范围：真实 backend/native 数值 differential（Step 8）、generation>0 mutation、Python reference/scatter API、CUDA/DualCSR、性能加速声明、push

## 1. 进入条件与不可回退原则

- Step 7 先修复第 2 节的跨 Step 3/6 合同冲突，再接 session；不得让不合法 rejection 进入 observation。
- binding factory 只创建 tokenless `created` handle；raw context、Stage 1 request resolution、token allocation、owner lease 和 DataManager 初始化严格分层。
- cpu/incremental 的 Stage 1 record 只有在 full pipeline 与 capture 全部成功并完成 observation commit 后才可逃逸。
- 任何触碰 live Database、mutable session context 或 active observation 的 operation/read 都由 `STAInterface` 唯一非递归 exclusive authority 串行化；不得让内部 pointer/reference 跨 guard。close 后只读取 session-owned detached immutable cache。
- scatter 的 Database allow-list 写入与 observation 变化属于同一 no-fail publish；不得先写 Database 再运行可能分配的 reducer。
- close 在销毁 DataManager 前 revoke snapshot；cleanup 失败也不恢复 ready/invalidated；同线程 operation→close 必须在写 `close-pending` 前 typed 拒绝。
- parent 在 capability resolution、`EccSubFlow`、engine、artifact discard、factory 前完成 raw argument/context/SPEF 与全部 signoff corner 的纯只读预检；随后 capability resolution 仍在任何副作用前完成。
- Stage 1 execution record 仍为 exact 10 字段；不扩 `StaSessionStatusCode`、capability reason 或 fallback reason。

## 2. 编码前合同勘误

### 2.1 Malformed result identity 的唯一分类

现有 `validateSnapshotIdentityClassified()` 把 token 0 分为 session、坏 fingerprint 分为 source identity；但 observation schema 又要求非-schema rejection 的 `source` 必须通过完整 identity syntax。二者无法同时成立。

Step 7 前置勘误冻结为：

1. result identity 的 fingerprint schema version 错、session token 为 0、任一 fingerprint 非 64 位小写 SHA-256，全部分类为 `kSchema`；
2. `kSchemaMismatch` observation action 的 `source=null`；
3. 只有完整 syntax-valid identity 才继续按 token 不同 → `kSessionMismatch`、token 相同且 generation 不同 → `kGenerationMismatch`、token/generation 相同且六 hash 不同 → `kSourceIdentityMismatch`；
4. generation 是 syntax-valid u64，Stage 2 非 0 仍属于 generation，不并入 schema；
5. shape/numeric/ID/predecessor rejection 的 source 必须 exact 等于 committed identity；
6. public `validateSnapshotIdentitySyntax()` 与 `validateStage2CommittedIdentity()` 的 field/message/violation 集合不变，只修 private typed class；
7. Step 6 lower-level scatter ABI、failure priority 和零写规则不变。

新增 KAT 精确覆盖 bad version、token 0、六种 bad hash、以及它们与 generation/shape 同时错误时均以 schema/source-null 优先；syntax-valid session/generation/source mismatch 保持原分类。Step 3 observation、Step 5 validator、Step 6 scatter chained gates全部回放。

### 2.2 Binding exposure 的总计划勘误

为让 parent 独立证明 observation 属于当前 native handle，Step 7 明确把 binding 新增面冻结为两个只读 property：

- `session_token: int | None`；
- `csr_snapshot_observation: dict | None`。

这不增加顶层 session state token，不修改 execution record，也不暴露 CSR input/result、raw pointer、reference 或 scatter。总计划 §12.2 的“只暴露 observation”在 Step 7 回填时修订为上述两个只读值。

### 2.3 Signoff collector 分流勘误

总计划 §8.2 仍写 signoff 入口调用 legacy `collect_sta_signoff_items()`，与 Step 7 的全corner纯预检冲突。冻结勘误为：`run_harden()` 继续且只消费原函数；`run_sta()` 继续且只消费新 strict immutable preflight，二者不得互调或共享可变 dict。

冻结本计划后，总计划 Step 7 回填必须同时修订 malformed identity、binding token、collector 分流三项，不得只登记计划 SHA。

## 3. Frozen child production inventory 与 target 图

新增：

- `source/data_manager/adapter/csr/CsrSessionSnapshotAdapter.hpp`；
- `source/data_manager/adapter/csr/CsrSessionSnapshotAdapterInternal.hpp`；
- `source/data_manager/adapter/csr/CsrSessionSnapshotAdapter.cpp`；
- `interface/StaCsrSessionContext.hpp`；
- `interface/StaCsrSessionContext.cpp`；
- `interface/STAInterfaceOperations.cpp`：从既有 1700+ 行 `STAInterface.cpp` 行为等价搬出 constructor/singleton 外的外部 operation/lifecycle 定义并接 exclusive guard；
- `src/interface/python/py_ista/py_ista_snapshot.h`：binding-private serializer 声明。

修改：

- `CsrSnapshotIdentityValidator.cpp`；
- `TimingResultScatter.cpp`、`TimingResultScatterInternal.hpp`、`TimingResultScatterPublish.cpp`；
- adapter/interface CMake；
- `IncrementalStaSession.{hpp,cpp}`；
- `STAInterface.{hpp,cpp}`；
- `StaLifecycleGuard.{hpp,cpp}`；
- `py_ista.{h,cpp}`、`py_register_ista.h`；
- `src/interface/python/py_ista/CMakeLists.txt`；
- `chipcompiler/tools/ecc/{sta_snapshot.py,sta_session.py,module.py,runner.py}`；
- tests、inventory/isolation 和 wheel action；
- 修改 `test/projection/StaCsrProjectionProbe.cpp` 与 `CheckCsrReferenceInputIsolation.cmake` 的唯一probe source hash；
- 新增 `test/projection/projection_default_compat_v1.json`；
- 新增 `test/csr_session/{csr_session_contract.py,csr_session_controller.py,csr_session_controller_selftest.py}`。

Exact target 迁移：

- `ista_timing_csr_core`：18 sources/objects，direct links 仍为空；
- `ista_timing_csr_snapshot_contract`：3，唯一 direct `PUBLIC ista_timing_csr_core`；
- `ista_timing_graph_csr_adapter`：17 → 18；direct `PUBLIC ista_timing_csr_core ista_timing_csr_snapshot_contract`，`PRIVATE ista_timing_database_headers`；
- `ista_interface`：5 → 7；新增 context 与 operations 两个 cpp，唯一新增 direct link 为 `PRIVATE ista_timing_graph_csr_adapter`，不得 direct link snapshot/core；
- `ista_source`、`ista_module` 不聚合 adapter/snapshot；
- `py_ista` 把 `aux_source_directory` 改为显式 exact `py_ista.cpp;py_ista_utils.cpp`，仍为两个 object且既有 direct link ownership不变；只为该target增加 adapter public include 与 snapshot public include 两个 `PRIVATE` include-only usage requirement，不新增 direct link或binding cpp，禁止相对路径偶然穿透。

旧17个adapter object继续禁止 snapshot header；只允许新 bridge object和既有 no-fail `TimingResultScatterPublish.cpp.o` 使用 exact snapshot public headers。interface implementation只能include adapter/session façade，不可裸include snapshot reducer/storage/FIFO/backend/scatter lower-level header；adapter任何object都不得include interface。named session wrapper只在 `StaCsrSessionContext.hpp` 定义，`STAInterface.hpp` 与 `IncrementalStaSession.hpp` 仅forward-declare，因此source/module和普通public-header消费者不传递看到adapter/snapshot。

`IncrementalStaSession.hpp` 只forward-declare `StaCsrSessionContext/StaCsrReferenceAttempt/StaCsrScatterAttempt` 与 `csr::StaAnalysisContext/CsrSnapshotObservation/CsrTimingResult`；released cache与getter/handoff只在header中使用 `std::unique_ptr<csr::CsrSnapshotObservation>`，析构与所有deep-copy定义移到完整类型可见的cpp，禁止实例化 `optional<CsrSnapshotObservation>`。`STAInterface.hpp` 同样只用forward declaration、named wrapper返回值与pointer/reference参数，不include context/adapter/snapshot。binding-private serializer header也只forward-declare DTO。因此 `py_ista_utils.cpp.o` 与 `python_moodule.cc.o` 不获得 snapshot dep。binding depfile allow-list只放行exact `py_ista.cpp.o` 与binding embed测试的单一test object；使用 `ninja -t deps` 检查，不假定物理 `.o.d` 存在。CMake gate同时锁 `py_ista` exact sources/direct links/PRIVATE include dirs，证明include-only边不改变冻结target图。

所有新增或机械拆出的文件 <700 行；既有大文件只接受删除/move或窄调用点。

## 4. Analysis context 与 token allocation

### 4.1 Exact native context

binding initialize 的 required keyword mapping exact 为：

~~~text
{
  liberty_corner: canonical non-empty exact str,
  temperature: canonical decimal exact str | "__unspecified_temperature__",
  rc_corner: canonical non-empty exact str
}
~~~

mapping 必须 exact 三键；拒 missing/extra/non-string、空串、首尾空白、非 canonical temperature、NaN/Inf 表示。binding parser 调用既有 `validateAnalysisContextIntrinsic()`，失败抛 `ValueError`，handle 保持 tokenless `created`，可用合法 context 重试或 side-effect-free close。

typed C++ initialize 的固定优先级为：

1. 非 created → existing `kInvalidState`；
2. intrinsic context invalid → `kInitFailed`，state 仍 created，token/record/operation 均无，可重试；
3. Stage 1 request resolution failure → existing unsupported，closed，不消费 token；
4. allocator exhausted → `kInitFailed`，closed，不调用 lease/operation；
5. 分配 token；
6. 构造 immutable `StaCsrSessionContext`；
7. 调用 production initialize/取得 lease。

合法 context 在步骤 5 后的分配、context 构造、lease/init/rollback失败均永久烧掉 token。raw invalid context 与 unsupported request 同时存在时 raw context preflight 先失败；valid context 的 unsupported request仍保持 Stage 1 行为。

该优先级也适用于parent direct与signoff入口：先完成raw argument/context/SPEF或全部corner纯预检，再做 `preflight_stage1_request()`。invalid context + CUDA 固定报context错误；valid context + CUDA才报unsupported。两阶段都在artifact、subflow、monitor/event、engine与native factory之前，组合KAT锁定该顺序。

### 4.2 Allocator

在 `StaLifecycleGuard.{hpp,cpp}` 新增可注入、可独立测试的 `StaSessionTokenAllocator`：

- atomic next 初值1；
- CAS 唯一分配 `1..UINT64_MAX`；
- 发出 `UINT64_MAX` 时把 next 原子设为0；
- next==0 是 sticky exhausted sentinel，永久返回 `nullopt`；
- 不提供 production reset/setter；测试使用局部 allocator 以 `UINT64_MAX` 初值构造；
- production 使用 function-local process singleton；
- 并发 allocation 唯一、不丢号、不产生0；
- `StaOwnerLease::acquireSession(0)` 及 require-use/close token0 明确拒绝，形成纵深门。

`IncrementalStaSession` 内部以 atomic u64 的0作为“尚未分配”sentinel，public `sessionToken()` 映射为 `optional<uint64_t>`；allocator仍绝不发出0。factory/constructor不触 allocator，token以release-store一次发布、acquire-load读取；分配前为null，分配后即使后续失败也保留burned/active token。

## 5. Session snapshot adapter

### 5.1 Public façade

~~~cpp
struct CsrCommittedSessionSnapshot
{
  CsrReferenceInput input;
  CsrCaptureMetadata metadata;
  std::unique_ptr<CsrSnapshotObservation> active_observation;
  std::unique_ptr<CsrSnapshotObservation> released_observation;
};

using CsrSessionSnapshotBuildResult =
    std::variant<std::unique_ptr<CsrCommittedSessionSnapshot>,
                 CsrCaptureCode>;

CsrSessionSnapshotBuildResult buildCsrSessionSnapshot(
    const Database& database,
    const StaAnalysisContext& context,
    std::uint64_t session_token);

CsrComputationResult computeCsrSessionReference(
    CsrCommittedSessionSnapshot& snapshot);

CsrTimingResultScatterAttempt scatterCsrSessionTimingResult(
    Database& database,
    CsrCommittedSessionSnapshot& snapshot,
    const CsrTimingResult& result,
    const StaAnalysisContext& current_context,
    std::uint64_t active_session_token);

void releaseCsrSessionSnapshot(
    CsrCommittedSessionSnapshot& snapshot) noexcept;
~~~

`input.source_identity` 是 token/generation 的唯一 canonical source；两个non-null owning observation pointer仅保存schema要求的active/released DTO，不另存第三份 identity/generation。

`releaseCsrSessionSnapshot()` 是monotonic idempotent：首次只swap预构造的owning active/released pointer；active随即指向released DTO。若active已released则no-op并逐字段不变，绝不把旧ready/invalidated twin换回。lower-level double-release KAT锁定此纵深合同。

### 5.2 One-shot build 与 export measurement

`buildCsrSessionSnapshot()` 固定顺序：

1. steady-clock start；
2. `exportCsrReferenceInputCandidate(database, context, token)`；
3. exporter success已证明 `validateReferenceInputForSession`；不得在 bridge 再裸调用同一 validator；
4. 唯一 `replayFifoLevelization(input)` 生成 candidate metadata；
5. incomplete → `kActiveCycle`；
6. steady-clock stop，得到 finite/nonnegative `export_ms`；
7. `makeReadySnapshotObservation(input, metadata, export_ms)`，其内部 validation/storage/FIFO replay保持既有合同；
8. 用 Step 3 reducer预构造 exact released twin；
9. 在独立 `unique_ptr` candidate 中完成全部复制/分配/验证；
10. caller仅以 pointer swap no-fail commit。

export timing包含高层 exporter与首次 FIFO/metadata生成；不含 observation reducer、modeled-storage visitor、released twin或commit。任何 typed failure/throw均无 partial snapshot/observation。

## 6. Session-local context 与状态机

~~~cpp
enum class StaCsrSessionSubstate : std::uint8_t
{
  kAwaitingCapture,
  kCaptureFailed,
  kReady,
  kInvalidated,
  kReleased
};

enum class StaCsrSessionOperationCode : std::uint8_t
{
  kInvalidState
};

struct StaCsrSessionOperationFailure
{
  StaCsrSessionOperationCode code{
      StaCsrSessionOperationCode::kInvalidState};
  std::uint64_t writes_applied{0};
};

struct StaCsrCaptureAttempt
{
  std::variant<csr::CsrCaptureResult,
               StaCsrSessionOperationFailure> value;
};

struct StaCsrReferenceAttempt
{
  std::variant<csr::CsrComputationResult,
               StaCsrSessionOperationFailure> value;
};

struct StaCsrScatterAttempt
{
  csr::CsrTimingResultScatterAttempt value;
};
~~~

`StaCsrSessionContext` public面只保留immutable canonical context与nonzero token value accessors；mutable substate accessor也收为private，不暴露observation pointer/reference。以下substate/live mutator/read均为private，只有 `friend class STAInterface` 可调用，unit test只经exact `StaCsrSessionContextTestAccess` friend seam：

- `capture(const Database&)`；
- `computeReference()`；
- `scatter(Database&, const csr::CsrTimingResult&)`；
- `release(std::unique_ptr<csr::CsrSnapshotObservation>* detached_out) noexcept`；
- `copyObservation(std::unique_ptr<csr::CsrSnapshotObservation>* detached_out)`，out入参必须预清空；在guard内deep-copy，success/null才表示None，local invalid-state保持out null并由STAInterface映射为失败status。

内部以 `unique_ptr<csr::CsrCommittedSessionSnapshot>` 持有 snapshot。capture进入即把 awaiting改为capture_failed；typed failure/throw都永久消费 one-shot。只有完整 candidate pointer swap后变ready。第二次capture在首次成功或失败后均返回local invalid-state/0且逐字段不变。

`release(detached_out)` 是唯一不返回invalid-state的mutator：要求non-null owning out已清空；从awaiting/capture_failed转released且out仍null；从ready/invalidated调用lower-level monotonic pointer swap后，以nothrow `unique_ptr` move把released observation交给out并转released；已released则idempotent no-op且不覆盖out。每次均noexcept，double release逐字段不变。reference/scatter在错误substate才返回local invalid-state或 `CsrScatterCode::kInvalidState/writes=0`，不调用 Database/singleton/reducer，observation不变。

状态矩阵：

| top/session event | CSR substate | observation |
|---|---|---|
| created / initialized | no context / awaiting | None |
| cpu/full run success | awaiting | None |
| incremental full+capture success | ready | ready/gen0 |
| full pipeline failure | awaiting | None |
| capture typed failure/throw | capture_failed | None |
| reference typed outcome | ready | ready + reference_ms |
| scatter rejection/success | ready | ready + event/success timing |
| current drift | invalidated | invalidated |
| close before capture/failure | released | None |
| close after ready/invalidated | released | released twin |

## 7. Reference 与 scatter 的 observation 原子性

### 7.1 Reference

reference仅在ready执行，调用 `CsrCpuReferenceBackend::compute(input)`。`reference_ms`从 compute 调用前到其返回后，排除 observation reducer/commit。timing result、unsupported support result和三种 computation code均保留原 typed outcome，并都记录一次reference timing。

active successor与其released twin在返回 outcome 前全部预构造；reducer/分配失败时 outcome不逃逸、旧observation不变。最后noexcept双swap，之后只返回预构造outcome。reference不改变top state。

### 7.2 Shared scatter preparation

把 Step 6 anonymous prepublish orchestration抽为 `TimingResultScatterInternal.hpp` 的 private shared result；lower-level `scatterCsrTimingResult()` 与session façade共用同一 current capture、priority、stable resolution和detached preparation，禁止复制算法。

scatter timing从 current staged export 前开始，到 classification/stable resolution/detached preparation或typed reject完成后停止；排除 observation reducer与publish。对 attempt：

- invalid_state：不形成event；
- snapshot_invalidated：预构造 `InvalidationAction(current_fingerprints,duration)`，清旧rejection，context转invalidated，顶层转poisoned；
- schema..predecessor：预构造 `ScatterRejectionAction`；schema source null，其余 source 使用syntax-valid result identity；
- success：预构造 `ScatterSuccessAction` 并清旧rejection。

### 7.3 Joint no-fail publish

复用既有唯一 no-allocation `TimingResultScatterPublish.cpp`，新增 private noexcept helpers：

- observation active/released pair 双swap；
- Database prepared timing publish + observation pair joint publish；
- release时只做active→released monotonic publish；已released no-op。

该adapter TU只对adapter-owned string/vector/map/optional/observation/prepared、`csr::CsrComputationResult`、`csr::CsrTimingResultScatterAttempt` 与private prepared-return类型做nothrow move-construct/destruct/swap static assertions，绝不include或实例化interface-owned `StaCsr*Attempt`。source/object/undefined-symbol gate拒 allocator/delete/hash/export/validator/reducer/logger/callback/interface。

`StaCsrSessionContext.cpp` 在完整类型可见处另对named `StaCsrCaptureAttempt/StaCsrReferenceAttempt/StaCsrScatterAttempt` 的outer wrapper及其contained variant做从各自exact final component构造、move与destruct全部nothrow static assertions；public headers只forward-declare。standalone header compile与 `ninja -t deps` 证明adapter不见interface、source/module和普通interface消费者不见adapter/snapshot。

success路径在首写前完成 checked write count、完整success attempt、active/released successors与全部scratch析构；joint publisher先写Database allow-list，再nothrow双swap，调用后下一条且唯一可执行语句为plain return。exclusive guard覆盖整个prepare→joint publish，其他线程看不到中间态。

`CsrSessionSnapshotAdapter.cpp` 的reference/scatter façade唯一拥有adapter outcome preparation、observation successor reduction以及observation或Database+observation publish；publisher后的下一条且唯一可执行语句为返回预构造adapter outcome的plain return。`StaCsrSessionContext.cpp` 不include reducer/publisher/lower-level scatter，只在façade返回后做已static-assert的nothrow named-wrapper构造、必要的enum assignment与plain return。capture成功则在context中先完整预构造 `StaCsrCaptureAttempt` 与snapshot candidate，最后以nothrow owning-pointer swap提交，下一条且唯一可执行语句为plain return。allocation ordinal failpoint与source-shape gate覆盖capture/reference/rejection/invalidation/success各类caller收件前的完整调用；任何post-commit throw都会因状态变化而失败。

## 8. Unique Database-exclusive authority

### 8.1 Public surface 收紧

`STAInterface.hpp` 的production public declaration allow-list按名称与signature分类冻结为：

- static：`getInst/destroyInst`；
- legacy lifecycle/operation：`initSTA/runSTA/extractLib/destroySTA/updateTiming/writeSDF/reportTiming/createClock/setPropagatedClock/getPorts/getClocks`；
- typed session：`initializeSession/runSessionBaseline/closeSession/copySessionCsrSnapshotObservation`；
- test-only：`computeSessionCsrReferenceForTesting/scatterSessionCsrTimingResultForTesting/lifecycleStateForTesting/setLifecycleOperationsForTesting`。

除上述exact集合外不得出现其他public helper。`input/output/writeLib` 与全部wrap/build/make/is/get内部helper均移入private；这明确包括 `isSDFDelayArc/isSDFCheckArc/getLibFilePath/makeLibArc/makeLibScalarTable`。private friend面只保留：

- `friend class DataManager`，允许既有 `STAI.input/output` 三个受控 lifecycle callback；
- `friend class TimingCharacterizer`，允许唯一 `STAI.writeLib`；
- test-only exact `friend class StaCsrSessionProbeAccess`，只允许一个受guard的const-Database oracle callback callsite，production无调用者；
- test-only exact `friend class StaInterfaceLifecycleTestAccess`，只读私有constructor count，唯一调用者为lifecycle test。

private test seam的exact signature为 `inspectSessionDatabaseForTesting(uint64_t token, const std::function<void(const Database&)>& callback)`；只有 `StaCsrSessionProbeAccess` 可调用，callback全程持operation guard，throw只经RAII退出且不得改lifecycle。source parser gate抽取public区声明并与allow-list逐项相等，拒任何未列方法；另锁外部private-friend调用者仅 `DataManager.cpp` 两处、`TimingCharacterizer.cpp` 一处、session probe access一处与lifecycle test access一处。外部 operation/lifecycle 实现从大文件机械搬到 <700行的 `STAInterfaceOperations.cpp`；行为移动与guard修改分开审阅，`STAInterface.cpp` 不新增成片逻辑。

### 8.2 Guard protocol

`STAInterface` 持有一个 non-recursive operation mutex、lifecycle mutex、close-pending owner和thread-local recursion sentinel。operation RAII guard与 `ClosePendingReservation` 均不可复制、可移动；前者析构总清sentinel/解锁，后者若未commit则在lifecycle lock下noexcept清除自己设置的pending。

use协议：

1. 在任何lifecycle lock/owner/pending访问前先查recursion sentinel；同线程任何嵌套立即以existing typed `kInvalidState` 拒绝，形成固定最高优先级；
2. lifecycle lock做owner/token与close-pending预检；
3. 释放 lifecycle lock；
4. 取得operation mutex并登记本线程owner sentinel；
5. lifecycle lock二次校验owner/token且close仍未pending；
6. 仍在任何context/Database访问前按下述pointer规则校验non-null context immutable token与active owner token exact相等；
7. 释放 lifecycle lock，执行完整operation；
8. 异常/返回均RAII释放；需要quarantine时在仍持operation lock期间短暂取得lifecycle lock。

close协议：

1. 在任何lifecycle lock/owner/pending访问前先查本线程operation sentinel；同线程operation→close立即返回existing typed `kInvalidState`（legacy路径用既有contract failure），owner/pending/Database/context逐字段不变；
2. lifecycle lock验证cleanup owner；
3. 构造scope-owned `ClosePendingReservation`并设置pending，阻止新use；
4. 释放 lifecycle lock后等待operation mutex，取得后登记同一sentinel；
5. lifecycle lock二次验证owner与reservation仍exact匹配；
6. non-null context token必须与cleanup owner token exact相等，否则在触context/Database/cleanup前typed拒绝并由reservation回滚pending；
7. 在operation guard内context monotonic release并把released observation detached handoff给session；
8. native cleanup；
9. lifecycle `completeClose/quarantine`提交后才commit reservation；cleanup failure也走提交而非回滚owner；
10. RAII释放operation mutex。

reservation覆盖二次校验失败、锁异常和所有commit前早退/throw；析构只清自己拥有的pending，不改owner/context。等待operation时永不持lifecycle。close cleanup callback→任何use/close先命中sentinel而立即拒绝；close pending前已排队的use取得锁后必须二次失败且不得触Database。source gate锁定use/close的sentinel precheck均位于首次lifecycle访问之前，并锁reservation的唯一set/clear/commit点及所有close出口。

pointer规则exact为：initialize无context；run/close只为cpu/full或确实尚无context的路径允许null；copy/reference/scatter要求non-null。任何non-null context都必须在owner二次校验后、首个context/Database触点前检查 `context.token()==owner.token`。foreign-context KAT以owner A/context B覆盖run/copy/reference/scatter/close，要求existing `kInvalidState`（scatter为invalid_state）、writes0、pending清空、Database及A/B observations逐字段不变。

exact effective guarded入口：

- private `initializeOwned/runOwned/closeOwned`（public init/run/destroy及typed wrappers只delegate，不二次加锁）；
- `extractLib/updateTiming/writeSDF/reportTiming`；
- `createClock/setPropagatedClock/getPorts/getClocks`；
- `computeSessionCsrReferenceForTesting/scatterSessionCsrTimingResultForTesting`；
- `copySessionCsrSnapshotObservation` 与private probe const-Database inspection seam。

`copySessionCsrSnapshotObservation` 使用 `StaStatus + pre-cleared unique_ptr out`：在operation guard内完成整个detached owning DTO deep-copy后才释放锁；success/null才表示None，任一failure/throw保持out null，返回pointer不指向内部对象且allocation失败不改状态。active read若先获得锁返回完整before，scatter若先获得锁返回完整after；close先赢时live read typed拒绝，而 `IncrementalStaSession` 从close内handoff的stable released owning cache读取完整after。

singleton lifetime另行冻结：`getInst()` 只含C++11线程安全初始化的 `static STAInterface* const process_instance = new STAInterface()` 并返回其引用，唯一instance地址故意process-lifetime不回收；删除当前无同步if/new与mutable static pointer。`destroyInst()` 是administrative logical reset而不delete storage，从根上消除首次并发双构造和getInst返回reference后并发回收的UAF。destroy先查同线程sentinel，再取得operation mutex和lifecycle mutex；仅none、无pending时重置initialized/timing flags与test operations到production default。source gate锁single function-local initializer和无 `delete _sta_interface_instance`；首次barrier KAT通过private test access断言所有地址相同、constructor count exact1，跨destroy地址稳定，另覆盖active/queued/recursive destroy与destroy后重新initialize。set-test-operations同样只在none/idle且受operation authority时允许。

确定性KAT使用barrier/latch与bounded timeout、禁止sleep，覆盖首次getInst×多线程、same-token scatter×2、foreign-context全操作、run-vs-scatter、read-vs-scatter、read-vs-close、close-vs-scatter、close-vs-long-run、destroyInst-vs-operation、排队use二次拒绝、异常释放、operation callback→closeOwned/destroy、close cleanup→use/close。递归close/destroy断言无死锁、pending未残留、随后正常close exact1；read结果只能是完整before/after或规定的typed rejection。全guard连续覆盖full baseline+capture，两者之间不得解锁。

## 9. Incremental session、capture 与 close

`StaSessionOperations` exact pure-virtual面为：

~~~cpp
virtual StaStatus initialize(std::uint64_t token, std::map<std::string, std::any>& config_map) = 0;
virtual StaStatus runFullBaseline(std::uint64_t token, StaCsrSessionContext* capture_or_null) = 0;
virtual StaStatus close(std::uint64_t token, StaCsrSessionContext* context,
                        std::unique_ptr<csr::CsrSnapshotObservation>* released_out) = 0;
virtual StaStatus copyObservation(std::uint64_t token, StaCsrSessionContext* context,
                                  std::unique_ptr<csr::CsrSnapshotObservation>* detached_out) = 0;
virtual StaCsrReferenceAttempt computeCsrReferenceForTesting(std::uint64_t token, StaCsrSessionContext* context) = 0;
virtual StaCsrScatterAttempt scatterCsrTimingResultForTesting(
    std::uint64_t token, StaCsrSessionContext* context, const csr::CsrTimingResult& result) = 0;
~~~

`STAInterface` 新增typed方法的exact signatures为：

~~~cpp
StaStatus initializeSession(std::uint64_t token, std::map<std::string, std::any>& config_map);
StaStatus runSessionBaseline(std::uint64_t token, StaCsrSessionContext* capture_or_null);
StaStatus closeSession(std::uint64_t token, StaCsrSessionContext* context,
                       std::unique_ptr<csr::CsrSnapshotObservation>* released_out);
StaStatus copySessionCsrSnapshotObservation(
    std::uint64_t token, StaCsrSessionContext* context,
    std::unique_ptr<csr::CsrSnapshotObservation>* detached_out);
StaCsrReferenceAttempt computeSessionCsrReferenceForTesting(
    std::uint64_t token, StaCsrSessionContext* context);
StaCsrScatterAttempt scatterSessionCsrTimingResultForTesting(
    std::uint64_t token, StaCsrSessionContext* context,
    const csr::CsrTimingResult& result);
~~~

`IncrementalStaSession::initialize` 的exact新签名为 `initialize(const csr::StaAnalysisContext&, std::map<std::string, std::any>)`；旧的context-free overload不保留，避免绕过raw context preflight。其新增test/value wrappers exact为：

~~~cpp
StaCsrReferenceAttempt computeCsrReferenceForTesting();
StaCsrScatterAttempt scatterCsrTimingResultForTesting(
    const csr::CsrTimingResult& result);
std::unique_ptr<csr::CsrSnapshotObservation> snapshotObservation();
~~~

`IncrementalStaSession` 自身增加per-object non-recursive API mutex与thread-local current-session sentinel，串行化initialize/run/close/reference/scatter/observation getter；同一对象这些operation/copy callback重入在等待mutex前返回existing local invalid-state，返回value的observation getter则抛携带同一status的 `StaSessionException`，绝不把重入失败解释成None或进入STAInterface。immutable request以及atomic state/token value getter不取API mutex；各状态转换在关联record/context/cache全部提交后release-store，getter acquire-load，因此callback与并发读取无data race。lock order固定为session API guard → STAInterface operation guard，析构也走同一exact-once close状态机。不同session同线程嵌套最终由STAInterface sentinel typed拒绝。fake override compile与declaration parser gate锁定全部token/context/result参数、引用限定、返回类型和非-noexcept约定。

cpu/full向run传null；cpu/incremental传context。`runOwned()` 在同一exclusive guard内先跑full pipeline，再capture。full失败或capture typed/throw统一映射existing `kRunFailed`、top poisoned、无record；capture cleanup failure仍按existing cleanup priority。只有二者全成功、active detached read可通过后，`IncrementalStaSession::runFullBaseline()` 才设置baseline_executed并返回原resolved record。

close在exclusive guard内调用 `context.release(released_out)`：release先monotonic pointer publish，再以static-asserted nothrow `unique_ptr` move/destruct把released observation交给预清空的out parameter，之后才销毁DataManager/释放lease。handoff后context不再暴露observation；重复release为no-op且不覆盖caller out。native cleanup失败仍top closed、session owning cache保持released并返回existing `kCleanupFailed`。无context/full/capture-failed时out保持null。

`IncrementalStaSession::snapshotObservation()` 返回 `std::unique_ptr<csr::CsrSnapshotObservation>` detached value：active状态以pre-cleared out调用operations guarded deep-copy，先检查 `StaStatus`；failure保持out null并抛对应 `StaSessionException`，只有success/null才是None。对任一non-null active/released DTO，getter在返回前于native内部要求atomic session token、仍保留的immutable context token与observation identity token三者exact相等，否则抛contract error；close只release observation而不销毁immutable context。closed状态只deep-copy session-owned released cache且不触singleton；created/initialized/full/capture-failed为null。cache member、getter与析构均out-of-line，保持header incomplete-type边界。

close使用预清空local handoff；无论operations close返回cleanup failure还是在handoff后抛异常，都先把非null out move进session cache、再把top置closed并形成最终status。二次close幂等短路，不执行二次Step 3 release。close后reference/scatter先短路local invalid-state/0，析构仍noexcept且cleanup attempt exact一次。session API并发KAT使getter-vs-close只能返回完整active或完整released，绝无data race/torn value；fake close-after-handoff throw专门证明cache不丢。

## 10. Binding serializer

`py_ista.cpp` 新增：

- exact context mapping parser；
- optional uint64 token property；
- optional observation serializer；
- `initialize(analysis_context=required, config="", config_dict={})`。

serializer直接构造detached Python dict/list/scalar，不经JSON string。getter只调用 `IncrementalStaSession::snapshotObservation()`：active走双层guard owning deep-copy，closed deep-copy stable owning cache；随后才在GIL下序列化并销毁local pointer。exact root/nested keys使用schema v1；enum调用既有 `csr::token()`，null为 `None`，u64为Python int，duration为float。每次property读取返回新dict，不得返回内部引用。

binding-private `py_ista_snapshot.h` 只forward-declare DTO，只供 `py_ista.cpp` 与embed unit测试；`py_register_ista.h` 只注册wrapper函数且不include snapshot header。`py_ista.cpp` 借§3两个PRIVATE include-only目录直接include完整adapter façade/snapshot enum token header；禁止相对include。native getter已完成session/context/observation三方校验；binding只再断言公开session optional token与non-null observation identity token一致，否则抛contract error，不新增context-token exposure。

binding CMake显式锁 `py_ista.cpp;py_ista_utils.cpp`、既有exact direct links与两个PRIVATE include dirs。embed test exact单source `StaCsrSnapshotBindingContractTest.cpp`，direct links仅 `py_ista;pybind11::embed`，使用同两个PRIVATE include dirs；depfile只允许该test object与 `py_ista.cpp.o` 命中snapshot/adapter header。

binding只读测试覆盖：

- factory token None；
- valid init token exact nonbool u64/nonzero；
- invalid mapping ValueError、state created、token None、随后valid retry；
- full observation None；
- incremental ready/released exact dict；
- cleanup failure后仍为released、二次getter不重试close；
- detached dict mutation不改变下次读取；
- token/context/observation一致；
- 无input/result/reference/scatter/raw property。

## 11. Parent session transport

`sta_snapshot.py` 新增并唯一复用三个pure helper：`make_direct_sta_analysis_context()`、`sta_analysis_context_to_native_mapping(context)`、`validate_sta_spef_rc_consistency(context, spef_path)`。它们分别冻结direct sentinels、exact三键native mapping与SPEF/RC双向一致性；module/signoff/session不得复制编码或各自解释sentinel。

`IncrementalStaSession` parent wrapper新增required immutable `analysis_context`，保存：

- `_session_token: int | None`；
- `_active_observation: StaSnapshotObservation | None`；
- `_snapshot_observation: StaSnapshotObservation | None`。

唯一新增public read-only property `snapshot_observation: StaSnapshotObservation | None`：未run/full/capture-failed为None；incremental run后且未close返回immutable ready active；successful close后返回released；close getter/parse/transition失败后为None。active不另设public property，module不得读私有字段。initialize成功后立即读取一次native token，strict拒bool、0、负数、>u64或None。

`run_full_baseline()` 固定顺序：

1. native run；
2. strict parse exact 10-field record；
3. 与Stage 1 preflight record exact比较；
4. 读取一次active raw observation并strict parse；
5. cpu/full要求None；
6. cpu/incremental要求ready、generation0、token等于独立native token、corner fingerprint等于parent canonical encoder；
7. initial capture还要求last rejection/invalidation、reference/scatter均None；
8. 缓存active，全部通过才返回record。

`close()` 固定为：

1. 幂等短路；
2. native close exact一次，保存return或exception；
3. 只有native call正常返回时，才在丢handle前读取released raw property exact一次；即使return不是None也仍完成这次读取；
4. close return必须exact None；wrong-return是本阶段primary contract error；
5. strict parse released并调用 `validate_snapshot_observation_transition(active,released,StaReleaseObservationAction())`；
6. 仅全部成功才缓存released/None；任一close/getter/parse/transition失败都清active与public snapshot cache；
7. `finally` 无条件丢native handle、标closed并保证close/getter均不重试，失败后public property固定为None。

若wrong-return与released getter/parse/transition同时失败，wrong-return保持primary，released错误为cause；若无wrong-return则released错误为primary close-side error。context manager body的bad record/active observation永远保持总primary，任一native close或released阶段错误挂为 `__cause__`。任何坏released、wrong return或close异常均不产生成功结果。

close KAT使用独立fake覆盖：wrong-return×{clean getter、getter throw、parse failure、transition failure}；bad-record与bad-active分别×{clean close、native close throw、non-None wrong-return、released getter/parse/transition failure}；另有native-close-throw且released getter exact0。至少显式锁body failure+wrong-return与body failure+native throw两格仍以原body对象为primary、对应close-side对象为exact `__cause__`。每格逐项断言primary/cause对象identity、closed、handle丢弃、active/public cache清空、native close/getter exact次数及二次close无调用。

## 12. Module API 与 artifact 顺序

新增 type alias：

~~~python
StaSnapshotObservationSink = Callable[
    [StaAnalysisContext, StaSnapshotObservation | None],
    None,
]
~~~

`ECCToolsModule.run_timing()` 新增：

- `analysis_context: StaAnalysisContext | None = None`；
- `snapshot_observation_sink: StaSnapshotObservationSink | None = None`。

None只能经 `make_direct_sta_analysis_context()` 解析；显式context先做intrinsic validation，再由共享helper冻结 `bool(spef_path) == (rc_corner != "__no_rc_corner__")`。有SPEF却缺raw RC、无SPEF却声明真实RC都在artifact discard/native前失败。raw preflight先exact normalize `output_modes`；只要求已启用的 `report`/`structured` destination为非空路径，未启用destination可为空且不得参与resolve/alias判断；只有两种mode同时启用时才要求report/feature `resolve(strict=False)` 后不相等。direct alias与symlink alias均在discard/setup/factory前失败。

成功顺序严格：

1. raw context/argument/SPEF consistency pure preflight；
2. Stage 1 request/capability preflight；
3. discard stale run outputs；
4. lib/sdc/spef setup；
5. native initialize(exact context mapping)；
6. run与active validation；
7. successful close/released validation；
8. 只通过public `session.snapshot_observation` 取值并调用sink(context,value) exact一次；
9. `publish_sta_artifacts`；
10. 返回原 `StaExecutionRecord`。

direct module KAT锁invalid-context+CUDA报context、valid-context+CUDA报unsupported，以及report/feature direct/symlink alias各自单独与CUDA组合时alias错误保持primary；全部要求discard/setup/native-session factory/sink/publish为0。另锁 `("report",)` 配空feature与 `("structured",)` 配空report的既有成功兼容，两种单mode均不做cross-kind alias判断。sink异常禁止publish/return；publish异常时sink已经成功一次，但调用方仍无record。sink默认None时返回类型、artifact和Stage 1日志兼容；module不得保存last observation或访问session私有字段。

### 12.1 Post-synthesis direct entry

`run_sta_without_spef()` 在任何capability、stale artifact discard、mkdir、module/engine factory/load或预注入module method前调用pure `preflight_sta_direct_run(workspace, step) -> StaSignoffRunItem`。它冻结direct context并一次验证netlist、至少一个Liberty、SDC、config均为regular file，work及两个实际启用的report/feature destination、resolve后非别名与positive nonbool max_paths；只计算path，不写文件或内存态。

顺序exact为：完整raw direct preflight → Stage 1 request/capability preflight → discard stale outputs → mkdir/setup → module/engine construction/load → `run_timing`。现有“invalid raw仍删除旧artifact”测试改为preserve不变；这是有意收紧而非兼容保留。

KAT覆盖missing SDC/liberty/netlist/config、空Liberty、destination direct/symlink alias分别与CUDA组合：raw invalid固定先报raw错误，valid raw+CUDA才unsupported。每格分别跑 `ecc_module=None` 与预注入spy module；前者锁constructor/load/discard为0，后者锁 `update_step_paths/init_config/init_techlef/init_lefs/read_verilog/run_timing` 全0；两者还共同锁stale artifact byte、不存在目录、native factory/sink/publish、workspace mutation、monitor/event均0。

## 13. All-corner signoff preflight 与隔离 sink

新增 `chipcompiler/tools/ecc/sta_signoff.py`，核心 immutable model：

~~~python
@dataclass(frozen=True)
class StaSignoffRunItem:
    config: str
    work_dir: str
    report_dir: Path
    feature_dir: Path
    liberty_files: tuple[str, ...]
    sdc_path: str
    spef_path: str
    max_paths: int
    artifact_corner: str
    analysis_context: StaAnalysisContext
~~~

现有 `runner.collect_sta_signoff_items(workspace) -> list[dict]` 完全保留单参数、list类型、五个legacy键 `corner/temperature/rcx_corner/liberty_files/spef_file`、顺序与当前空列表/日志行为；`run_harden()` 继续只消费该legacy函数，production无需改型。第二轮清理后，`preflight_sta_signoff_run(workspace, step) -> tuple[StaSignoffRunItem, ...]` 在一个只读流程中验证配置并直接构建最终运行项，仅供 `run_sta()`；不再保留中间 source model 或重复规范化 context。`preflight_sta_direct_run(workspace, step) -> StaSignoffRunItem` 仅供 `run_sta_without_spef()`。调用关系由功能回归验证；源码清单门禁已在上一轮清理中删除。

strict preflight一次性、纯只读验证全部corner：

- STA config、signoff/liberty/RC outer containers与每层key/value均为exact预期类型，signoff outer、Liberty outer与RC outer分别非空；
- 每个被引用Liberty corner的 `liberty_files` 为exact non-empty list，元素为exact non-empty path string；
- 每个signoff RC group为exact non-empty list，pair/item字段齐全且至少产生一个raw pair；
- raw liberty/temperature/RC intrinsic normalization，调用共享context/SPEF helper；
- duplicate liberty corner、duplicate raw signoff pair；
- 全部Liberty/SPEF/SDC/config regular file；
- work/report/feature配置与positive nonbool max_paths；
- 输入容器的非空约束保证至少生成一项；完成全部sanitize/alias验证后返回 frozen `tuple[StaSignoffRunItem,...]`；
- 空signoff outer、空dict group、空Liberty outer、被引用Liberty file list为空、空RC list在输入边界分别拒绝；删除上述约束之后不可达的零raw pair及空final tuple分支。全部验证仍在任何subflow/engine/discard前完成。
- 先计算全部raw `artifact_corner` 与sanitize结果，再要求artifact_corner全局唯一；
- 对每项 `report_dir.resolve(strict=False)`、`feature_dir.resolve(strict=False)` 做各自及cross-kind全局唯一，拒不同raw corner sanitize后碰撞（如 `A/B` vs `A_B`）和report/feature root alias；
- artifact path只计算，不mkdir/discard，不构造 `EccSubFlow`，不改workspace/subflow内存态，不写JSON，不发monitor/event/log-side-effect telemetry；
- 保留config corner顺序和Liberty path顺序。

`run_sta()` 固定为：strict全corner/raw-context preflight → Stage 1 request/capability preflight → 构造唯一 `EccSubFlow` → 唯一一次engine creation → load-data event/update → 顺序运行frozen items。第二corner非法或invalid-context+CUDA时，subflow constructor/file/update、workspace mutation、monitor/event、engine/run_timing/discard/artifact/sink全部0；组合错误仍按§4 context-first。

每个corner循环创建独立local capture与closure；callback拒第二次调用、context不等或跨corner引用。`run_timing()` 成功返回后要求exact一次：

- 记录原Stage 1 execution telemetry；
- incremental时记录一条CSR summary（raw context、released state、token/generation、N/E/L、host bytes、timings）；
- 再记录artifact saved。

cpu/full不新增CSR summary。禁止module/global/runner “last observation”。兼容测试分别锁legacy `collect_sta_signoff_items` + `run_harden` dict访问、strict immutable STA路径与post-synthesis direct preflight；逐项非空合同与碰撞测试都从不存在subflow JSON开始，并断言文件/内存/monitor/event均不变。

## 14. Failure/side-effect matrix

| failure point | record | sink | artifact publish | close/token |
|---|---:|---:|---:|---|
| raw context/request/signoff preflight | 0 | 0 | 0；subflow/file/event/engine均0 | token 0 |
| factory | 0 | 0 | 0 | 无handle |
| invalid native context | 0 | 0 | 0 | created/tokenless，可重试 |
| token exhaustion | 0 | 0 | 0 | closed，无lease |
| lease/init failure | 0 | 0 | 0 | token已烧；cleanup按既有合同 |
| full/capture failure | 0 | 0 | 0 | close exact一次；obs None |
| malformed record/active obs | 0 | 0 | 0 | close exact一次 |
| body + close双失败 | 0 | 0 | 0 | body primary，close cause |
| native cleanup failure | 0 | 0 | 0 | closed；released cache保留；close1 |
| bad released/wrong return | 0 | 0 | 0 | closed；cache None；close/getter≤1 |
| sink throw | 0 | 1 attempt | 0 | 已成功released |
| publish throw | 0 | 1 success | existing cleanup | 已成功released |
| cpu/full success | exact record | 1，None | 1 | token非0/close1 |
| incremental success | exact record | 1，released | 1 | token非0/close1 |

## 15. Tests、inventory 与 CI

新增四个native executable；test CMake在使用前显式 `find_package(Threads REQUIRED)`，禁止依赖Abseil目录顺序。四者compile options均exact `-Wall;-Wextra;-Werror;-pedantic;-ffp-contract=off`：

| target | exact sources | exact direct links |
|---|---|---|
| `ista_csr_session_snapshot_adapter_contract_test` | `CsrSessionSnapshotAdapterContractTest.cpp` | `ista_timing_graph_csr_adapter;ista_timing_database_headers` |
| `ista_csr_session_context_test` | `StaCsrSessionContextTest.cpp` | `ista_interface;ista_timing_graph_csr_adapter;ista_timing_database_headers` |
| `ista_csr_session_lifecycle_test` | `StaCsrSessionLifecycleTest.cpp` | `ista_interface;ista_timing_graph_csr_adapter;ista_timing_database_headers;Threads::Threads` |
| `ista_csr_snapshot_binding_contract_test` | `StaCsrSnapshotBindingContractTest.cpp` | `py_ista;pybind11::embed` |

每个test source自含小fixture且自身<700行，不偷聚合旧test cpp。binding target另锁§10两个PRIVATE include dirs。test CMake还注册umbrella inventory与controller self-test，合计exact 6 unit +1 smoke；相对Step6为unit 78→84、property保持20、smoke5→6：

| CTest name | exact command contract | labels / timeout |
|---|---|---|
| 上述四个target同名 | exact target executable、无参数 | `ista_unit`；adapter/context 60s，lifecycle/binding 120s |
| `ista_csr_step7_source_inventory` | 单一 `cmake -P CheckCsrStep7SourceInventory.cmake`，只传冻结root/build/tool/packed inventory参数 | `ista_unit`；120s |
| `ista_csr_session_controller_validation` | exact argv `${ISTA_TEST_PYTHON_EXECUTABLE};${CMAKE_CURRENT_SOURCE_DIR}/csr_session/csr_session_controller.py;--manifest;${CMAKE_CURRENT_SOURCE_DIR}/baseline/manifest.json;--default-compat;${CMAKE_CURRENT_SOURCE_DIR}/projection/projection_default_compat_v1.json;--self-test` | exact label `ista_unit`；60s；exact env `PYTHONDONTWRITEBYTECODE=1` |
| `ista_csr_session_fresh_process` | exact argv `${ISTA_TEST_PYTHON_EXECUTABLE};${CMAKE_CURRENT_SOURCE_DIR}/csr_session/csr_session_controller.py;--probe;$<TARGET_FILE:ista_csr_projection_probe>;--manifest;${CMAKE_CURRENT_SOURCE_DIR}/baseline/manifest.json;--default-compat;${CMAKE_CURRENT_SOURCE_DIR}/projection/projection_default_compat_v1.json;--run-root;${CMAKE_CURRENT_BINARY_DIR}/csr-session-runs;--repeats;3;--timeout-seconds;75`；controller先为每个manifest case各启动exact三次不含 `--probe-mode` 的legacy-default child，再为每个session child追加exact `--probe-mode;session` | exact label `ista_smoke`；1050s（6个default+6个session child，各75s上限并留150s余量）；exact env `PYTHONDONTWRITEBYTECODE=1` |

不新增 `StaCsrSessionProbe.cpp` 或第二个probe target。现有 `ista_csr_projection_probe` 保持exact五source/direct links，新增optional exact `--probe-mode session`。缺省projection与session两分支都只经同一个 `StaCsrSessionProbeAccess` callsite取得guarded const Database；probe source中 `STADM.getDatabase(` occurrence exact0。session模式复用真实LEF/Liberty/Verilog/SDC加载、full baseline与atomic temp-file writer，文件仍<700行。

编码前基线已从probe source SHA `a91baa76ed378ba600621445d8ebe94f0b1636c56650da3f2a7e52f4f2ece64d` 的最新3-repeat结果冻结进 `projection_default_compat_v1.json`。该文件由strict duplicate-safe loader读取，root exact四键 `schema/baseline_probe_source_sha256/canonicalization/payload_sha256_by_case`；schema exact `ista-csr-projection-default-compat/1.0.0`，baseline source SHA为上述值；canonicalization exact mapping为 `removed_root_keys:["run_nonce","repeat_index"]`、`sort_keys:true`、`separators:[",",":"]`、`ensure_ascii:false`、`final_newline:false`；payload mapping exact两键chain→`aa90a070164f8561cadd68852ff34a88e4045c6b9a37902bab6304952028d9dd`、diamond→`61a87d3fedefdcb12bc7c8868dbb361ad512f5f573413290d15fad08890bfa1f`。canonical payload只删除上述两个root key，再以UTF-8、`json.dumps(sort_keys=True,separators=(",",":"),ensure_ascii=False)`、无末尾换行求SHA。

Step 7只更新 `CheckCsrReferenceInputIsolation.cmake` 中probe source的旧hash为实施后exact hash；legacy `projection_controller.py/projection_contract.py/projection_controller_selftest.py/projection_canonical.py` hashes保持不变，现有projection fresh CTest继续通过。fresh session controller在任何session child前直接调用未修改的 `projection_controller.run_controller()`，参数exact为current probe、同一manifest、`run_root.resolve().parent / "projection-runs"`、`repeats=3` 与同一75s timeout；因此每个manifest case各运行三个与现有legacy fresh CTest完全同协议、明确不含 `--probe-mode` 的default child，并复用legacy `validate_repeat_count>=3`、strict schema/manifest验证与atomic publication。新controller对该已验证legacy summary的每case三个record逐个按compat文件计算canonical bytes，三者必须分别命中同一冻结SHA后才折叠为summary result；这是独立runtime default-compat oracle，失败即同一smoke CTest失败。workflow gate锁exact legacy函数调用/参数、default/session phase flag与compat schema/value；poison分别改变任一repeat的默认schema/key/payload、default command flag、legacy temp/final protocol或compat SHA并要求失败。

每个session-mode进程先跑cpu/full并要求observation None，再在同一已加载design上跑两个连续cpu/incremental session。full/default与每个incremental active期间都由同一exact test friend在STAInterface operation guard内把const Database交给probe callback；callback独立执行direct native projection、independent FIFO oracle、`exportCsrReferenceInputCandidate(context,token)` 与 `replayFifoLevelization`，不调用session bridge或observation builder。逐字段要求：

- active identity token等于独立session token、generation0、六content fingerprint等于direct exporter；
- observation N/E/L与direct input/FIFO一致且全为positive，projection/FIFO互证；
- close后的released只允许state变化，由Step3 transition validator证明其余字段exact；
- 两session token非0且不同，同input六content fingerprint/counts相同；
- chain/diamond的topology fingerprint、projection hash与至少一项N/E/L必须不同，拒合法空快照。

probe session mode的 `schema` literal exact为 `ista-csr-session-probe/1.0.0`，JSON root exact为 `schema/run_nonce/case/repeat_index/input_case_sha256/full_observation/sessions/complete`；每个session exact为 `session_token/active/released/oracle`，oracle exact为 `source_identity/node_count/edge_count/level_count/projection_sha256/fifo_sha256`。`csr_session_contract.py` 复用 `baseline_contract.load_json()` 的duplicate-key、NaN/Inf与single-value EOF-safe raw loader；controller要求exit0、stderr空、nonce/case/repeat echo、`input_case_sha256` exact等于manifest descriptor、sessions长度exact2、`complete is True`。

controller summary schema exact为 `ista-csr-session-controller/1.0.0`，root exact为 `schema/requested_repeats/default_compat_results/case_results/complete`。`default_compat_results` 按manifest顺序exact两项，每项exact `case/input_case_sha256/payload_sha256`；`case_results` 同序exact两项，每项exact `case/input_case_sha256/repeats`，repeats长度exact等于requested且按repeat_index递增保存完整validated session child record。所有case SHA再次等于manifest，summary `complete is True`。

controller为每个manifest case启动exact三个legacy-default subprocess与requested_repeats个相互独立的session subprocess；本CTest下即每case 3+3，全部12个run nonce与child目录全局不同。default child完全复用legacy `projection_controller` 的 `projection-{pid}-{nonce}` run-dir、`{case}-{repeat_index}-{nonce}` slot-dir、`.projection-result-{run_nonce}.tmp`/`projection-result.json` 及 `.controller-result-{summary_nonce}.tmp`/`controller-result.json`；不得引入第二套default basename或probe argv。session child仍用 `.csr-session-result-{run_nonce}.tmp`/`csr-session-result.json`，probe只exclusive创建temp，controller strict验证后才atomic publish到预先不存在的final。唯一csr-session run-dir内summary temp/final exact为 `.csr-session-controller-{summary_nonce}.tmp`/`csr-session-controller-result.json`，summary在strict round-trip验证后atomic publish；controller stdout只打印csr-session final summary path。

`csr_session_controller_selftest.py` 必须用raw bytes/files而非Python dict单独拒绝child与summary的duplicate key、trailing second JSON、trailing garbage、truncated JSON、NaN/Inf、false/missing complete、sessions长度非2、错误case/repeat或manifest `input_case_sha256`、任一legacy-default repeat compat不符、坏summary envelope/order/count、missing/extra result/temp/final、bool-as-int、wrong schema/token、bad transition、canned cross-case、相同chain/diamond、重复nonce、stderr、非零退出与75s child timeout；每个poison证明strict loader/controller真实失败。

跨进程只比较六content fingerprints、counts与projection/FIFO hashes；不比较token、host bytes/capacity/timing，timing只验finite/nonnegative。Step 7仍不声称backend/native数值parity。

parent新增小文件测试：

- `test_sta_session_snapshot.py`；
- `test_module_timing_snapshot.py`；
- `test_sta_signoff.py`；
- `test_runner_sta_snapshot.py`。

既有669行 `test/tools/ecc/test_runner.py` 的编码前exact SHA为 `497546869d950b79d1515217f8312b42daffc52dedb24fc5b94e405259f7226f`。Step 7只机械删除其 `sta_mode` import、`FakeSynthesisStaModule` 与四个完整test block：`test_run_sta_without_spef_reads_netlist_and_writes_to_step_report_and_feature`、`test_run_sta_without_spef_warns_when_sdc_is_missing`、`test_run_sta_without_spef_removes_stale_power_report_on_failure`、`test_run_sta_uses_matched_report_and_feature_corner_directories`；不得改其余byte，删除后exact 413行/SHA `6845d6ad7b73dce116e61602cc846bea186e39f85c46d21eda96dc4437035805`。四个自含新版回归迁入 `test_runner_sta_snapshot.py`：成功direct创建regular STA config并锁analysis context/sink kwargs，missing/raw invalid保留stale bytes且覆盖 `None`/预注入module，signoff fake调用每corner sink exact一次并锁context/value不串角。legacy `collect_sta_signoff_items + run_harden` dict兼容回归也在新文件通过public/imported调用锁原signature与行为；旧runner文件与新文件均显式运行。

### 15.1 Chained structural gates

新增umbrella `CheckCsrStep7SourceInventory.cmake`，只顺序include四个focused、各自<700行且不注册CTest的 `CheckCsrStep7Targets.cmake`、`CheckCsrStep7Dependencies.cmake`、`CheckCsrStep7GuardPublish.cmake`、`CheckCsrStep7Workflow.cmake`。umbrella是唯一Step7 inventory CTest。可执行line-count gate覆盖全部新增文件、机械拆出的 `STAInterfaceOperations.cpp`，以及所有baseline<700且被Step7实际修改的production/test/Python/CMake/YAML文件；明确包括375行probe、648行 `CheckCsrReferenceInputIsolation.cmake`、Step3/4 gates、controllers与test CMake，逐个实施后仍<700。既有>700大文件只允许删除或窄callsite，另以diff-addition gate拒成片新增；旧runner只允许§15所列exact block删除并锁迁移后的413行/SHA `6845d6ad7b73dce116e61602cc846bea186e39f85c46d21eda96dc4437035805`。

- target gate锁adapter18/interface7/core18/snapshot3/py_ista2、四unit exact sources/direct links/options、projection probe exact五source，以及新增objects；CTest JSON v1锁上述6 unit+1 smoke的exact command/label/timeout/environment，禁止probe/property executable直接注册；
- Step3 gate把exact `CsrSessionSnapshotAdapter.hpp`、`CsrSessionSnapshotAdapterInternal.hpp`、`CsrSessionSnapshotAdapter.cpp` 全部加入production local-Kahn token扫描；两个header的replay call exact0、只允许cpp exact1，production direct call 5→6、bare symbol 6→7。safe/poison分别向public/internal header注入queue/Kahn token，并证明漏bridge、错文件额外调用、本地拓扑实现都失败；
- Step4 gate同时把production FIFO exact count/file set 5→6并加入exact bridge；production exporter occurrence 3→4且bridge是唯一新增production caller，仍不新增 `validateReferenceInputForSession` direct caller；safe/poison覆盖第六调用错位；
- Step7 workflow gate另锁 `StaCsrProjectionProbe.cpp` test-source中 `exportCsrReferenceInputCandidate(` 与 `replayFifoLevelization(` 各exact1且同处guarded oracle callback，删除、移出callback或额外test-side call的poison均失败；
- Step5/6 projection target五source/direct-link inventory保持不变；只按§15更新旧isolation gate的probe hash并新增默认compat payload gate，Step6 direct lower-level behavior、publisher、scatter KAT与全部旧structural gate回放；
- old17 adapter objects仍禁snapshot；新bridge与既有publisher各有独立exact dep allow-list；interface只能direct adapter，source/module仍禁adapter/snapshot；
- binding dep只允许 `py_ista.cpp.o` 与embed test object命中snapshot/adapter header，utils/module禁止；同时锁显式source list、PRIVATE includes且direct links不变；
- source gate锁identity malformed→schema、factory零token、context-before-token、MAX sticky exhaustion、one-shot capture outer预构造/swap/plain-return、monotonic release/handoff-before-cleanup、adapter façade publisher后plain return及context三种named-wrapper构造/move/destruct noexcept；
- public/helper gate锁exact public allow-list与DataManager两处、TimingCharacterizer一处、probe/lifecycle-test friend各一处；guard gate锁effective entry、use/close sentinel-before-first-lifecycle、owner-context token check、double-check、reservation rollback/commit、status+detached-out read及native session/context/observation token三方getter校验；
- no-fail publisher source/nm/depfile/allocation-poison selftests、默认projection compat SHA与Stage0 chain/diamond/manifest golden、Stage1 enum/record hashes全部不变。

### 15.2 Wheel/Nix

wheel action：

- 显式build四个新unit executable、既有 `ista_csr_projection_probe` 的session mode、`py_ista`、`ecc_py`；
- 三标签CTest各exact一次并保留 `--no-tests=error`；
- cache rejection加入 `test/csr_session/__pycache__`；
- configure cache key加入 `src/**/*.cmake`，防止included gate复用旧configure。

本地仅在 `ecc` 根使用bare flake `nix develop`，新build dir `build-ista-step7`。回放Step3/4/5/6 structural gates、全部CSR、global unit/property/smoke、Python non-PDK、Ruff check/format、scoped ty、clang-format 21.1.8、diff-check、artifact/rej/pycache hygiene。

## 16. 实施与复审顺序

1. 三路独立设计审查本计划；任一finding先修计划并由原reviewer按新SHA复查。
2. 冻结计划SHA；总计划升级并回填Step7 SHA、malformed identity、binding/token与collector分流三项§2勘误。
3. 修identity classification及Step6 KAT，先跑Step3/6 chained gates。
4. token allocator、token0 lease纵深与factory零消费。
5. adapter build/reference/scatter/released twin与joint publisher。
6. session context与Incremental lifecycle。
7. STAInterface operation机械拆分、private helper与exclusive guard。
8. binding context/token/serializer。
9. parent session/module transport。
10. signoff preflight、runner local sink/log。
11. CMake/inventory/isolation/wheel。
12. 三路未参与实现的native/parent/gate code review；修正并由原reviewer重复。
13. 全门禁、Step7 as-built报告；再进入Step8。

## 17. DoD 与不声明

DoD：

- invalid context零token/lease/DB且可重试；valid failure烧token；MAX不wrap；
- incremental capture one-shot、gen0、active/released exact；full保持None；
- record只在capture+active validation后逃逸；
- malformed identity rejection与observation schema一致；
- Database+observation success joint no-fail，所有失败零写；
- same-thread递归在owner/pending前固定typed拒绝，foreign context在Database前拒绝且pending可回滚；release/handoff先于cleanup，closed getter不触singleton并保持session/context/observation token一致；
- 全corner与post-synthesis direct context/raw paths在capability/subflow/engine/artifact前纯预检，report/feature resolve后不别名，final paths唯一且per-corner sink不串值；
- target/link/include/depfile/callsite/guard/CTest JSON inventory精确；
- current probe不传 `--probe-mode` 的chain/diamond runtime canonical payload逐case命中编码前compat SHA，legacy projection Python hashes与fresh CTest不变；
- Step0/1兼容、所有门绿、设计和代码三路APPROVE。

不声明Step8 fresh-process backend/native数值等价、sequential/CRPR native parity、generation>0、mutation batch、CUDA/DualCSR、speedup、cross-process token唯一、cross-process host-byte/timing golden、commit或push。
