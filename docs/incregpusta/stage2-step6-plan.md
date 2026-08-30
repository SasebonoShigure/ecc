# ECC IncreGPUSTA 阶段 2 Step 6 详细实施计划

> 状态：v0.7 no-fail publish、bit-exact oracle 与 rerun evidence 勘误已由两路独立复审 APPROVE；正文冻结，最终 SHA 记录于 Stage 2 总计划
> 基线：Stage 2 总计划 v0.9；Step 5 production、全门禁、独立 code review 与 as-built 文档均已收口
> 范围：Arc fallback provenance、semantic native timing oracle、stable-key scatter、全量 prevalidation、no-fail publish、stale 零写入、scatter 后 native dynamic rerun
> 非范围：真实 session owner/token/commit/binding/parent observation（Step 7）；fresh-process backend/native differential（Step 8）

## 1. 进入条件与原则

Step 5 的 production、hand KAT、五 seed property、inventory/isolation、全 CSR/legacy/format 门禁和三路独立 code review 全部通过后，Step 6 才能编码。

- source snapshot 的 native rank、vector index、raw pointer 不可信；scatter 每次重导 current candidate 并按 semantic key 重解析。
- current drift 早于 result 自身错误，stale/foreign result 不能掩盖 invalidation。
- lookup、分配、复制、转换及 numeric/shape/ID/predecessor 检查全在首写前。
- publish translation unit 只做已证明 noexcept 的 scalar assignment/swap。
- 所有失败精确 `writes_applied=0`，用完整 native oracle 和 forbidden encoding 证明零写。
- Step 6 的 token/generation 参数只做 committed identity guard，不声称真实 owner/lease authority。
- native rerun只证明 scatter state/fallback 能被动态传播消费，不声称 backend/native parity。

## 2. Frozen production inventory

新增 `source/data_manager/adapter/csr/`：

- `CsrNativeTimingOracle.hpp`：semantic-keyed DTO，production scatter不得include；
- `TimingResultScatter.hpp`；
- `TimingResultScatterInternal.hpp`；
- `TimingResultScatter.cpp`：guard、current capture、priority orchestration；
- `TimingResultScatterValidation.cpp`；
- `TimingResultScatterPreparation.cpp`；
- `TimingResultScatterPublish.cpp`：唯一 Database timing mutation TU。

新增 exact 4 adapter cpp。target source/object 冻结：

- `ista_timing_graph_csr_adapter`：13 → 17；
- `ista_timing_csr_core`：18不变；
- `ista_timing_csr_snapshot_contract`：3不变。

adapter direct links仍为 `PUBLIC ista_timing_csr_core` 与 `PRIVATE ista_timing_database_headers`。Step 6 不链接 snapshot-contract，不加入 `ista_source`、`ista_module` 或 `ista_interface`。

修改：

- `advance/Arc.hpp`：typed fallback state、const readers、有损 mutable compatibility getter、noexcept replacement/normalization；
- `advance/TimingPathState.hpp`：四个 string family 的 const-reference/noexcept readers；
- `advance/TimingPoint.hpp`：allow-list const readers/noexcept publish入口；
- `advance/Database.hpp`：timing-order const/noexcept access；
- `adapter/csr/CsrReferenceTypes.hpp`：下移 `CsrCurrentFingerprints`；
- `adapter/csr/TimingGraphCsrAdapter.hpp`：staged export failure phase 与 partial fingerprint evidence；
- `adapter/csr/CsrReferenceInputAdapter.cpp`：按六 fingerprint 优先级分段导出并逐段发布 evidence；
- `adapter/csr/CsrReferenceInputAdapterInternal.hpp`：export phase/failure helper；
- `adapter/csr/CsrReferenceFingerprintPayload.hpp/.cpp`：六个既有 payload 的 component-only fingerprint helper；
- `module/timing_csr/CsrReferenceValidator.hpp/.cpp`：唯一 invalidation helper；既有 public validator API 不变；
- `module/timing_csr/CsrReferenceValidatorDetail.hpp`：保留 non-result untyped helper，新增 result-only typed overload；
- `module/timing_csr/CsrSnapshotIdentityValidator.cpp`：identity 规则使用单一 typed sink，legacy API只投影field/message；
- `module/timing_csr/CsrTimingResultValidator.cpp`、`CsrTimingResultArcValidator.cpp` 与 `CsrTimingResultValidatorInternal.hpp`：共享 typed result violation class；
- `module/timing_csr_snapshot/CsrSnapshotObservation.hpp`：复用 core type；
- `module/timing_csr_snapshot/CsrSnapshotInvalidationPolicyInternal.hpp`：delegate helper；
- `module/sdf_writer/SDFWriter.hpp/.cpp`：唯一 production timing-arc delay-map 读取迁移到 const overload，SDF bytes不变；
- `adapter/csr/CMakeLists.txt`：17-source inventory。

不修改 interface、pybind、parent Python、session context、production aggregate CMake或Stage 1 record。

## 3. Arc fallback provenance

~~~cpp
using TimingArcDelayMap =
    std::map<std::int32_t,
             std::map<AnalysisType,
                      std::map<TransType,
                               std::map<TransType, double>>>>;
using TimingArcDelayFallbackKey =
    std::tuple<std::int32_t, AnalysisType, TransType, TransType>;
using TimingArcDelayFallbackKeySet = std::set<TimingArcDelayFallbackKey>;

struct TimingArcDelayState
{
  TimingArcDelayMap delay_map;
  TimingArcDelayFallbackKeySet fallback_key_set;
  void swap(TimingArcDelayState&) noexcept;
  friend bool operator==(const TimingArcDelayState&,
                         const TimingArcDelayState&) = default;
};

[[nodiscard]] const TimingArcDelayState&
get_timing_arc_delay_state() const noexcept;
[[nodiscard]] TimingArcDelayMap&
get_timing_arc_delay_map() noexcept;
[[nodiscard]] const TimingArcDelayMap&
get_timing_arc_delay_map() const noexcept;
void replace_timing_arc_delay_state(TimingArcDelayState&&) noexcept;
~~~

规则：

- 现有map/set合并为单一state；typed const state reader是 provenance 的唯一完整观察口。
- legacy mutable delay-map getter作为有损 compatibility escape hatch 保留：返回map前必须先清空整个 fallback set；所得引用不得跨越任何其他 `Arc` member call 保存或使用。
- const delay-map overload只读且不改变 provenance；所有 production 读取必须经 const-qualified `Arc`，唯一现有 SDF caller 改用 `find/at`，禁止 mutable `operator[]`。
- legacy copying setter先在detached state复制map，复制成功后一次nothrow swap；异常保持原state逐字节不变，成功替换map并清空全部provenance。
- 每次 `update_timing_arc_delay()` 在任何 `operator[]` 前全局 prune fallback set：凡key在map中不存在exact lane即删除，覆盖通过旧mutable引用删除的未触碰 stale key。
- dynamic missing-lane 写在插入前显式 erase 同key marker；initialization missing-lane 首写才插入并标fallback。
- 首次dynamic写即使等值也替换fallback并清标，之后按analysis raw strict winner更新。
- fallback set在每个可观察 member-call 边界必须是delay-map lane子集；public typed replacement在swap后全局prune。scatter publish前另做detached-state验证，`Arc.hpp` 只把 exact `publishPreparedTimingResult(PreparedTimingResult&) noexcept` 声明为private friend，由该函数对已验证state直接nothrow swap；不增加public/raw bypass。
- 禁止raw fallback setter或mutable fallback getter；mutable delay-map getter只能出现在 exact test-only mutation allow-list，oracle contract仅用 escaped legacy引用构造reader必须拒绝的invalid-subset负例。
- exact state/map/set做nothrow-swappable static assertions。
- KAT覆盖mutable getter立即清空全部marker、删除fallback lane后dynamic重建不带marker、另一个未触碰stale marker被global prune、public replacement归一化invalid subset，以及initial/min/max/equal-first-dynamic/later-strict既有语义。
- source inventory锁定production无mutable getter caller、所有只读caller走const overload；测试只允许 `ArcTimingArcDelayTest.cpp`、`CsrReferencePoisonSupport.cpp` 与 `CsrNativeTimingOracleContractTest.cpp` 的硬编码mutation点取得mutable map，第三者只构造invalid-subset reader负例。

## 4. Fingerprints 与唯一 invalidation policy

`CsrCurrentFingerprints` 从 snapshot observation 原样移到 pure `CsrReferenceTypes.hpp`。snapshot header本就单向include该文件，不产生反向依赖。

~~~cpp
[[nodiscard]] std::optional<CsrInvalidationReason>
firstCsrInvalidationReason(
    const CsrSnapshotIdentity& committed,
    const CsrCurrentFingerprints& current) noexcept;
~~~

顺序严格 topology、clock constraint、library、corner、parasitic、timing input；missing与mismatch都命中该family。snapshot policy与scatter均delegate，不复制六分支。

### 4.1 Family-aware staged export evidence

禁止把导出失败统一伪装成 topology drift。现有 exporter 扩展为：

~~~cpp
enum class CsrReferenceInputExportPhase : std::uint8_t
{
  kAnalysisContextPreflight,
  kTopology,
  kClockConstraint,
  kLibrary,
  kCorner,
  kParasitic,
  kTimingInput
};

struct CsrReferenceInputExportFailure
{
  CsrCaptureCode code{CsrCaptureCode::kMalformedTopology};
  CsrReferenceInputExportPhase failed_phase{
      CsrReferenceInputExportPhase::kTopology};
  CsrCurrentFingerprints current_fingerprints;

  friend bool operator==(const CsrReferenceInputExportFailure&,
                         const CsrReferenceInputExportFailure&) = default;
};
~~~

导出和 evidence 顺序必须与 invalidation 顺序一致：

1. intrinsic analysis-context preflight；失败 phase 为 `kAnalysisContextPreflight`，scatter 返回 `kInvalidState`，不进入普通 invalidation helper；
2. topology 导出成功后只计算并填 topology fingerprint；
3. constraints/clocks 导出成功后填 clock-constraint fingerprint；
4. Liberty 导出成功后填 library fingerprint；
5. 从已验证 current context 填 corner fingerprint；
6. parasitic 导出与 cross-field context 校验均成功后才填 parasitic fingerprint；
7. timing-check/clock-seed/load/support 导出全部成功后填 timing-input fingerprint。

因此任何非 preflight failure 都携带所有更高优先级的已完成 family，失败 family 及后续 family 保持 null。scatter 把该 evidence 与 committed identity 交给唯一 `firstCsrInvalidationReason()`：更早 family 同时 drift 时仍返回更早 reason；否则 missing 的失败 family就是唯一 reason。若非 preflight failure 经 helper 得不到 reason，视为内部 `logic_error` 并在 publish 前失败，禁止任意 fallback。

为实现该顺序，现有 parasitic-before-Liberty 调用调整为 Liberty-before-corner-before-parasitic；各 component helper必须复用现有六 payload/domain 与 `makeSnapshotIdentity()` 规则，不另造编码。完整 success 的六 fingerprint及 canonical bytes必须与 Step 4 KAT逐字节不变。

KAT至少覆盖 pre-DB invalid context→invalid state、graph failure→topology、constraint failure→clock、Liberty table/numeric failure→library、corner drift+parasitic failure→corner、parasitic cross-field failure→parasitic、timing-input failure→timing input，以及 topology+library、library+parasitic 等重叠优先级。

## 5. Internal API 与 Step 7 边界

~~~cpp
struct CsrTimingResultScatterAttempt
{
  CsrScatterResult scatter_result;
  CsrCurrentFingerprints current_fingerprints;
  std::optional<CsrReferenceInputExportFailure> current_capture_error;
  friend bool operator==(const CsrTimingResultScatterAttempt&,
                         const CsrTimingResultScatterAttempt&) = default;
};

[[nodiscard]] CsrTimingResultScatterAttempt scatterCsrTimingResult(
    Database& database,
    const CsrReferenceInput& committed_input,
    const CsrTimingResult& result,
    const StaAnalysisContext& current_context,
    std::uint64_t active_session_token,
    std::uint64_t active_graph_generation);
~~~

Step 6 guard只验证token非0、committed input strict-valid/supported/generation0、active token/generation与committed identity一致。它不是owner boundary。Step 7先验证真实session/owner/lease，再调用并更新reducer/observation。

success path必须在首写前构造完整、非 `const`/非 `volatile` 的 `CsrTimingResultScatterAttempt success_attempt`：success result固定为 `{kSuccess, checked_count, nullopt}`，六current fingerprints为最终值，`current_capture_error` 固定 `nullopt`，所有string/optional storage均已完成。所有capture/validation/resolution scratch必须在publish前结束生命周期；首写时只允许prepared aggregate/state与success attempt等逐类型证明nothrow-destructible的对象仍存活。

### 5.1 Step 7 已冻结的 Database-exclusive boundary

Step 6 test只允许在单线程、调用者独占 Database 的条件下直接调用 lower-level scatter。Step 7 必须实现而不得重新解释的边界为：

- 唯一锁拥有者是 `STAInterface`；新增一个非递归 operation/Database-exclusive mutex及RAII guard，`StaCsrSessionContext`和owner token都不能代替互斥；
- lock order固定为先 lifecycle/owner state、后 Database-exclusive；取得后必须再次校验owner/token/generation，避免 check-to-lock TOCTOU；
- guard连续覆盖 owner/token 校验、current staged export、classification、stable resolution、detached preparation、publish、snapshot observation/reducer更新，期间不得释放再获取；
- `runOwned()`、`close()`、Step 7 capture/commit/release及所有经 `STAInterface` 暴露的 Database mutation必须共享同一 exclusive guard；inventory列出并锁死每个入口，legacy路径不得绕过；
- close先阻止新operation，再等待既有exclusive owner退出；同线程递归进入被合同拒绝，不依赖recursive mutex；
- Step 7 concurrency KAT用同token双线程证明第二个mutation不能越过guard，并覆盖run-vs-scatter、close-vs-scatter和异常释放。

Step 7 编码前若不能证明所有 exposed Database mutation入口共享该 guard，必须停留在设计阶段；不得以“调用方约定无并发”替代 production authority。

## 6. Frozen failure priority 与 typed validator

首个失败决定code：

1. lower-level active guard → `kInvalidState`；
2. current identity六family drift → `kSnapshotInvalidated` + 首个reason；
3. result schema → `kSchemaMismatch`；
4. result session → `kSessionMismatch`；
5. result generation → `kGenerationMismatch`；
6. result source六fingerprints → `kSourceIdentityMismatch`；
7. size/presence/sentinel/offset/row shape → `kShapeMismatch`；
8. field numeric policy → `kResultNumericInvalid`；
9. Node/Arc/clock-tag范围与stable mapping → `kIdMappingMismatch`；
10. predecessor tuple/endpoint/chain → `kPredecessorMismatch`；
11. success。

current drift必须在读取result schema前裁决；drift+malformed/foreign result仍invalidated。失败全部零写。

现有 result validator 改为单一 typed rule source：

~~~cpp
enum class CsrTimingResultViolationClass : std::uint8_t
{
  kSchema,
  kSession,
  kGeneration,
  kSourceIdentity,
  kShape,
  kNumeric,
  kIdMapping,
  kPredecessor
};

struct CsrTimingResultContractViolation
{
  CsrTimingResultViolationClass classification;
  std::string field;
  std::string message;
};
~~~

`validateTimingResultClassified()`定义于private internal header，前置条件明确为“input已经通过 `validateReferenceInputForSession()` 或 `validateReferenceInput()` 且 `unsupported_reasons.empty()`”。它不重复验证input，也不新增第九个input class。现有public `validateTimingResult()`保留当前两项前置行为：malformed input返回`input` violation，unsupported input返回`input.unsupported_reasons` violation；只有前置通过后才调用classified并逐项无损投影field/message。因此legacy API和错误文字不变，而所有result自身规则仍只有classified一份。

scatter必须先以`validateReferenceInputForSession()`、supported与generation guard证明上述前置条件，再直接调用classified；禁止调用public wrapper。inventory锁classified恰有两个production caller（legacy wrapper、scatter），并锁result-rule reject只存在于typed identity sink、`CsrTimingResultValidator.cpp`、`CsrTimingResultArcValidator.cpp`及Detail的result-only overload。两个result validator TU中的每个direct reject和每个result-only helper调用都必须显式传class，禁止把untyped `Violations`传入result规则。

identity语法也只有一份规则：`CsrSnapshotIdentityValidator.cpp`以typed sink在产生点分别标记schema/session/generation/source identity；既有`validateSnapshotIdentitySyntax()`与`validateStage2CommittedIdentity()`忽略class后投影，result validator直接消费typed形式。禁止根据field/message事后分类，禁止另写第二份fingerprint语法。

分类表冻结为：

- schema：顶层schema及identity fingerprint-schema；
- session：result token语法与对committed token的不等；
- generation：result generation合同与对committed generation的不等；
- source identity：六fingerprint语法与逐family不等；
- shape：extent/offset/row/presence/canonical-absent/FIFO与lane布局、fallback presence/value domain；
- numeric：finite/sentinel/sign、seed/scalar-extrema/no-SPEF数值一致性及所有算术值政策；
- ID mapping：NodeId/ArcId/ClockTagId范围、timing-arc index、transition/enum domain与stable lookup映射；
- predecessor：shape与ID均已成立后的predecessor tuple、endpoint、root/causality/chain规则；predecessor数组shape仍归shape，predecessor ID越界仍归ID mapping。

任何一条规则同时可命中多类时可以产生多条typed violation；scatter按固定class priority选择而不依赖append顺序。KAT至少包含schema+session+generation+fingerprint四类重叠和Arc shape+numeric重叠。

class→scatter code 的 switch 不写 `default`，启用 `-Wswitch-enum -Werror`；source inventory锁定八枚举项与八个mapping case。任何不可能的无映射值在首写前抛 `logic_error`。不存在“剩余 violation→shape”的 public fallback；mutation canary用于覆盖率证明，不替代 typed exhaustive mapping。

## 7. Stable-key re-resolution

每次scatter重跑 `exportCsrReferenceInputCandidate(database,current_context,committed_token)`：

1. current六fingerprints先与committed identity比较。
2. 从committed lookup表取得canonical NodeKey/ArcKey。
3. exact lookup current candidate同一semantic key。
4. Node full name解析current timing point，验证唯一/key相符。
5. current ArcRecord native rank解析current arc vector，验证bounds、唯一、端点/key。
6. source native rank、ArcId顺序、raw address绝不用于写入解析。
7. fingerprint相同但key/cardinality/rank不一致仍 `kIdMappingMismatch`。
8. 调用要求Database独占且无并发graph mutation；不声明并发事务。

guard 对 committed input 使用 `validateReferenceInputForSession(committed_input, active_session_token)`（exact一次）再检查supported与active generation；不新增 `validateReferenceInput()` direct call。

## 8. Prevalidation 与 detached preparation

首写前阶段固定为 guard → current capture/invalidation → result classification → stable resolution → detached replacement。

replacement覆盖且仅覆盖：

- TimingPoint：9个scalar/string/index family、effective clock五map、physical clock五map、data-slew、path-state，共21 family/node；
- Arc：delay/min/max、transition、input-output、graph、atomic timing-arc state、transition-type，共8 family/arc；
- Database timing-order vector，共1 family。

转换规则：

- absent scalar/string/index恢复native canonical default，不保留旧值；
- predecessor NodeId转current full name，ArcId转current native rank；
- clock/path tag经committed clock-tag table解码；
- map只含present lane，swap后清旧extra keys；
- timing-arc delay/fallback共同构造typed state；
- timing-order NodeId转current full name；
- level先检查native整数范围；
- lookup、分配、复制、enum转换、fallback subset、count overflow全在此完成。

## 9. No-fail publish 与 write count

publish前 static assert string/map/set/vector/state均nothrow-swappable；scalar setter、public normalization replacement及exact private-friend state swap均noexcept；checked count与完整success attempt预构造。`std::optional<std::string>`、`std::optional<CsrInvalidationReason>`、`CsrScatterResult`、`CsrCurrentFingerprints`、`CsrReferenceInputExportFailure`、其optional及完整attempt均逐项 `std::is_nothrow_move_constructible_v`；attempt和每个publish时仍存活的prepared aggregate/state逐项 `std::is_nothrow_destructible_v`，且不得含custom deleter/callback destructor。

orchestrator的首写只能是一次 `noexcept` publish调用；该调用之后的下一条且唯一可执行语句必须是 `return success_attempt;`。禁止post-publish字段赋值、count计算、花括号/临时返回值、`std::move(success_attempt)`、helper、日志、断言、callback或分支。source scanner与standalone `-Wswitch-enum -Werror` 编译共同锁定此形状；NRVO未发生时只走已证明nothrow的隐式move，禁止因const退化为copy。

publish source depfile/nm/scanner拒allocation、lookup、hash、validator、exporter、logger、callback。allocation failpoint覆盖caller的完整 `auto attempt = scatterCsrTimingResult(...);` 直接初始化；成功返回或进入catch之后立即disable，任何断言/oracle读取只能在disable之后执行。因此任何遗漏的post-write allocation都会以“异常且oracle已变化”被动态抓获。

`TimingResultScatterPublish.cpp` 只做scalar assignment/swap；timing-arc state只能由上述exact private friend直接swap已验证detached state，不调用会prune/lookup的public replacement或legacy copying setter，不触碰topology/adjacency、Pin/Instance/Net、start/end/root、Arc key/flags/raw pointer、library/constraint/parasitic、path group/summary/power/report/SDF。

success `writes_applied` 冻结为family count：

~~~text
21 * node_count + 8 * arc_count + 1
~~~

空图success为1；乘加checked overflow。它不是lane/element数。atomic仅指单线程调用内all-or-nothing。

## 10. Semantic native timing oracle

`CsrNativeTimingOracle.hpp` 位于adapter/csr以冻结DTO/header isolation；只有test-only reader使用。schema为 `ista-csr-native-timing-oracle/1.0.0`。

顶层保存native timing order NodeKey vector，node按canonical NodeKey bytes排序，arc按canonical ArcKey bytes排序。

Node覆盖key、level、is-clock、arrival/required/slack/launch、optional clock name、predecessor NodeKey/ArcKey、effective/physical各五lane family、data slew、按analysis/source/transition/clock-tag bytes排序的path state。path内start/predecessor/crpr均转semantic key。

Arc覆盖key、delay/min/max、transition/input-output/graph delay、transition type、signed timing-arc index排序及optional `{delay,is_fallback}`。fallback presence必须与delay presence一致。

排除token/generation/fingerprint/capacity、native address/index、topology/adjacency、path group/summary/power/report/SDF。

新增header-only test helper `CsrNativeSemanticKeyTestSupport.hpp`，把当前 `CsrNativeGraphRawProjector.cpp` anonymous namespace中的native NodeKey/ArcKey构造及其必要enum/table-signature转换原样抽出；public API exact为两个 `nativeSemanticNodeKey(...)` overload和一个 `nativeSemanticArcKeys(const Database&)`，全部 `[[nodiscard]] inline`。detail保持既有两遍parallel ordinal算法，不调用production `TimingSemanticKey`/`assignParallelOrdinals`/exporter/validator；helper本身不新增object。为让Step6逐项KAT调用真实raw-projector consumer，只有native-oracle contract target额外复用既有 `CsrNativeGraphRawProjector.cpp` object；其余五target与COMMON均不链接该object。

既有 `CsrNativeGraphRawProjector.cpp`、既有 `CsrNativeGraphOracleReader.cpp` 与新 `CsrNativeTimingOracleReader.cpp` 三者都必须include/call该helper并删除各自重复NodeKey/ArcKey builder。新top-level timing reader只构造一次full-name→NodeKey map与native-rank→ArcKey vector，再把const lookup传给Node/Arc子reader，后两者不得include helper或重算key。

reader接收 `const Database&`，只通过 `const TimingPoint&`、`const TimingPathState&`、`const Arc&` 与const Database order读取；`get_start_point/get_predecessor/get_clock_name/get_crpr_clock_pin` 四个path-state getter均返回 `const std::string&` 且 `noexcept`，禁止copy、`const_cast` 或mutable getter。reader不调用production exporter/backend/scatter/validator。stale predecessor、rank OOB、unknown enum、duplicate timing-arc index、fallback非子集、NaN均拒绝；invalid-subset只由oracle contract的test-only escaped legacy引用构造，public replacement必须先归一化而不能作为poison seam。

Step6 KAT在parallel-arc及port/instance-pin fixture上实际调用 `captureDirectNativeGraphProjection()` 与 `readNativeTimingOracle()`，逐项比较两者canonical-sorted NodeKey/ArcKey，证明两个consumer接线一致；helper算法正确性由既有handwritten parallel literal、bound-signature literal、production round-trip及五seed graph property独立证明，旧oracle的FIFO算法与independent encoding也保持独立。independent timing-oracle encoder对double写入raw IEEE-754 bits，必须区分`-0.0/+0.0`，reader仍拒NaN并允许既定±inf；timing reader前后比较forbidden encoding，并提供empty bytes KAT、signed-zero bit canary及每family mutation canary。

## 11. Native dynamic rerun

chain/diamond smoke：

1. native分析后读baseline oracle；
2. test-only materializer构造result；
3. poison全部scatter allow-list但保持source fingerprints；
4. scatter后oracle立即恢复；chain同时安装equal/different fallback并验证provenance；
5. immediate exact检查后，test-only定向安装该入口保证覆写的start scalar/data-slew losing canary与active graph-delay losing canary，并先证明forward与dynamic-arc projection均不同于baseline；
6. 不运行GraphBuilder，exact调用 `DelayCalculator::getInst().init()`，随后exact调用 `TimingPropagator::getInst().propagate()`；
7. rerun后forward scalar/data-slew projection与dynamic Arc graph/timing-arc projection均与baseline exact，fallback首次dynamic替换并清标；
8. required/path-group/summary是该入口非覆盖family；path-state虽由入口重算，但独立Step6 fixture只seed start rows、不复制native path propagator，因此这四类只验证scatter immediate restore，本smoke不声明rerun exact。Step 8 fresh-process full differential再覆盖完整path-state。

入口证据已冻结：`DelayCalculator::init()`只清parasitic cache；`TimingPropagator::propagate()`沿现有timing-order执行start seed、data-slew与delay，进入`DelayCalculator::calculateArc()`并以`is_initialization=false`更新timing-arc delay。定向canary必须选该入口无条件seed或按winner规则必然替换的lane，不能只在rerun前安装baseline而形成no-op false-green。两者均不调用GraphBuilder或重建Arc vector。

inventory锁probe中上述两个调用各exact1且顺序固定、GraphBuilder调用0，并锁定post-scatter canary安装及两类pre-rerun inequality evidence；KAT保存Arc vector size、data、每个Arc地址/key/native rank并证明rerun前后完全不变，同时以“installed fallback值恰等于首次dynamic值”和“值不同”两例证明首次dynamic都会清fallback，后续min/max raw-strict更新。Step 8才做fresh-process full differential。

## 12. Targets 与 tests

新增：

- `ista_csr_native_timing_oracle_contract_test`；
- `ista_csr_timing_scatter_contract_test`；
- `ista_csr_timing_scatter_atomicity_test`；
- `ista_csr_timing_scatter_property_test`；
- `ista_csr_timing_scatter_public_headers_test`；
- `ista_csr_timing_scatter_rerun_probe`；
- `ista_csr_step6_source_inventory` CTest。

### 12.1 Exact test files 与 target ownership

新增 test-only 文件冻结为：

- `CsrNativeSemanticKeyTestSupport.hpp`；
- `CsrNativeTimingOracleTestSupport.hpp`；
- `CsrNativeTimingOracleReader.cpp`；
- `CsrNativeTimingOracleNodeReader.cpp`；
- `CsrNativeTimingOracleArcReader.cpp`；
- `CsrNativeTimingOracleIndependentEncoding.cpp`；
- `CsrNativeTimingOracleContractTest.cpp`；
- `CsrTimingScatterTestFixture.hpp/.cpp`；
- `CsrTimingResultFromNativeOracle.cpp`；
- `CsrTimingScatterContractTest.cpp`；
- `CsrTimingScatterStaleContract.cpp`；
- `CsrTimingScatterAtomicityContract.cpp`；
- `CsrTimingScatterPropertyTest.cpp`；
- `CsrTimingScatterPublicHeadersMain.cpp`；
- `CsrTimingScatterHeaderIncludeOrderTest.cpp`；
- `CsrTimingScatterHeaderReverseIncludeOrderTest.cpp`；
- `public_header/CsrNativeTimingOracleHeaderTest.cpp`；
- `public_header/TimingResultScatterHeaderTest.cpp`；
- `timing_scatter/StaCsrTimingScatterRerunProbe.cpp`；
- `timing_scatter/timing_scatter_controller.py`；
- `CsrTimingScatterTests.cmake`；
- `CheckCsrStep6SourceInventory.cmake`。

除public-header target外，五个functional target的common source property精确为3个header加7个cpp：`CsrNativeSemanticKeyTestSupport.hpp`、`CsrNativeTimingOracleTestSupport.hpp`、`CsrTimingScatterTestFixture.hpp`、既有`CsrReferenceInputTestFixture.cpp`、既有`CsrReferenceInputNativeFixture.cpp`、四个reader/encoder cpp与`CsrTimingScatterTestFixture.cpp`。两个既有fixture provider分别提供analysis context与native fixture所有权/构造符号；直接复用其object，禁止include `.cpp`、复制实现或新增support library。header-only key helper不增加object。各target的完整 `SOURCES` 与对象数独立硬编码在 Step6 inventory，不从target自己的变量生成expected：

| target | exact source property（在common外追加） | exact cpp objects | exact direct links |
|---|---|---:|---|
| native oracle contract | `CsrNativeGraphRawProjector.cpp`、`CsrNativeTimingOracleContractTest.cpp` | 9 | `ista_timing_graph_csr_adapter;ista_timing_database_headers` |
| scatter contract | `CsrTimingResultFromNativeOracle.cpp`、`CsrTimingScatterContractTest.cpp`、`CsrTimingScatterStaleContract.cpp` | 10 | 同上 |
| scatter atomicity | `CsrTimingResultFromNativeOracle.cpp`、`CsrTimingScatterAtomicityContract.cpp` | 9 | 同上 |
| scatter property | `CsrTimingResultFromNativeOracle.cpp`、`CsrTimingScatterPropertyTest.cpp` | 9 | 同上 |
| public headers | public main、include-order、reverse-order、两个`public_header` cpp | 5 | 同上 |
| rerun probe | `CsrTimingResultFromNativeOracle.cpp`、`timing_scatter/StaCsrTimingScatterRerunProbe.cpp` | 9 | `ista_timing_graph_csr_adapter;ista_timing_database_headers;ista_source;idm` |

表中对象数是最终唯一权威值；public-header target不使用common group。inventory脚本必须逐target硬编码全部相对路径并从硬编码清单构造expected Ninja object，不得从packed actual反推expected。

六个 executable compile options均exact `-Wall;-Wextra;-Werror;-pedantic;-ffp-contract=off`，无额外direct link。`timing_scatter_controller.py`不是target source；它注册 `ista_csr_timing_scatter_rerun` smoke CTest，唯一probe参数来自 `$<TARGET_FILE:ista_csr_timing_scatter_rerun_probe>`。`ista_csr_step6_source_inventory`只有CTest、没有同名executable。

新增CTest inventory exact为：

| CTest | command | label | timeout |
|---|---|---|---:|
| `ista_csr_native_timing_oracle_contract_test` | 同名executable | `ista_unit` | 60 |
| `ista_csr_timing_scatter_contract_test` | 同名executable | `ista_unit` | 60 |
| `ista_csr_timing_scatter_atomicity_test` | 同名executable | `ista_unit` | 60 |
| `ista_csr_timing_scatter_property_seed_<seed>` ×5 | property executable `--seed <seed>` | `ista_property` | 60 |
| `ista_csr_timing_scatter_public_headers_test` | 同名executable | `ista_unit` | 60 |
| `ista_csr_timing_scatter_rerun` | controller + 唯一probe target-file参数 | `ista_smoke` | 300 |
| `ista_csr_step6_source_inventory` | CMake script，仅CTest | `ista_unit` | 60 |

因此新增exact 11个CTest：5 unit、5 property、1 smoke。`ista_csr_timing_scatter_property_test`与`ista_csr_timing_scatter_rerun_probe`均不得direct注册CTest。

### 12.2 Chained inventory/CMake/CI 修改

exact修改文件为：

- `test/CMakeLists.txt` include `CsrTimingScatterTests.cmake`，并把header-only semantic-key helper加入既有 `ista_csr_projection_probe` exact source property；
- `CsrTests.cmake` 的 `ISTA_CSR_NATIVE_GRAPH_SUPPORT_SOURCES` 加入semantic-key helper header；既有三个raw-projector target的cpp object数不变；
- `CsrNativeGraphRawProjector.cpp` 与 `CsrNativeGraphOracleReader.cpp` 删除重复key builder并调用helper；`CsrNativeGraphTestSupport.hpp` 注释收紧为FIFO/encoding保持独立而semantic-key construction共享；
- `CsrIsolationTests.cmake` 把adapter source/object 13→17、core18与snapshot3不变，并把semantic-key helper加入 `ISTA_CSR_DIRECT_PROJECTOR_FILES`；
- `ArcTimingArcDelayTest.cpp`、`CsrReferencePoisonSupport.cpp`、`CsrNativeTimingOracleContractTest.cpp`、`baseline/StaFullBaselineProbe.cpp` 的只读delay-map访问迁移到const；前三者仅在硬编码mutation点使用lossy mutable getter，oracle contract只构造invalid-subset负例；
- `CheckCsrAdapterIsolation.cmake`、`CheckCsrCoreIsolation.cmake`、`CheckCsrSnapshotContractIsolation.cmake` 增加scatter/oracle与test-only semantic-key helper反向规则；
- `CheckCsrStep4SourceInventory.cmake` 将 `exportCsrReferenceInputCandidate` occurrence 2→3，expected files加入 `TimingResultScatter.cpp`；`validateReferenceInput()`仍exact6次/5文件；新增 `validateReferenceInputForSession()` declaration、definition、Step4 exporter caller、scatter caller，exact4次/4文件；
- `CheckCsrStep5SourceInventory.cmake` 保持core18、snapshot3、既有四target/16 objects/3 slow objects完全不变，同时把 `CsrNativeTimingOracle`、`TimingResultScatter` 与semantic-key helper加入Step5 production/test/slow-oracle禁止依赖；
- child `.github/actions/build-wheel/action.yml` 显式build六个新executable，随后跑完整unit/property/smoke；hygiene显式拒baseline及timing_scatter目录的 `__pycache__`；
- `CsrTimingScatterTests.cmake` 与 `CheckCsrStep6SourceInventory.cmake` 锁定本节所有source/object/link/options、semantic-key helper的旧/新target ownership与depfile allow-list，以及exact 11个CTest的name/command/label/timeout/seeds/controller参数；拒property executable与rerun probe的direct CTest。

五property seed为 `1/7/42/20260820/0xdeadbeef`，各独立CTest、`ista_property`、timeout60。wheel action显式build新增executables后跑unit/property/smoke。

Fallback matrix：empty/bulk、initial、min/max、first dynamic equal replacement、later strict、legacy setter clear、mutable getter clears-all、erased fallback lane→dynamic nonfallback、untouched stale marker global prune、invalid subset prepublish reject、disabled/unreachable retain。

Oracle matrix：全部Node/Arc family、absent/zero/signed-zero raw-bit exact/允许±inf、effective/physical、same/different tag、parallel、timing order、predecessor conversion、const path-state读取、raw/timing/independent三方semantic-key一致、stale/OOB/unknown/duplicate/subset negatives、public replacement normalization、read-only/KAT/canary；scatter round-trip另以signed-zero signbit canary拒绝`-0.0/+0.0` false-green。

Success matrix：empty/singleton/chain/diamond/multi-root/parallel/disabled/loop、全allow-list、old extra keys清除、source/forbidden bytes不变、idempotence、exact count。

Failure matrix：guard、五个native可独立成功导出的current drift与overlap、timing-input phase-6 capture failure、export failure evidence、drift+bad result、schema/session/generation、六source fingerprint、shape/sentinel、NaN/inf/negative slew/overflow、Node/Arc/tag mapping、scalar/clock/path predecessor。纯invalidation helper仍用synthetic fingerprints覆盖六类（含timing-input mismatch）；当前exporter中timing-input payload由前五family及其exact derivation闭包决定，不为制造不可达的success-only drift而放松production校验。逐项完整oracle+forbidden comparison与zero writes。

Allocation fault：fresh fixture、expected oracle与setup全在启用hook前完成；count-only run取得入口至caller收件的总allocation数，再从ordinal 0逐个注入并补跑 `total+1` success点，覆盖current export、validation、resolution、preparation及完整success-attempt构造。hook跨越完整 `auto attempt = scatterCsrTimingResult(...);` 直接初始化，只有成功返回或catch后才disable，disable后才做assert/oracle读取；每个抛出点均验证完整oracle/forbidden bytes不变和零写，成功点验证预期写入。任何post-write allocation都会以异常+oracle变化失败；publish另以static/nm/source scanner证明零allocation。

Property禁止backend生成expected，执行oracle→materialized result→poison→scatter→oracle exact、idempotence、input unchanged、随机stale zero-write。

## 13. Isolation 与 CI

- adapter/core/snapshot exact 17/18/3，links与production SCC不变；
- 对adapter17、core18、snapshot3每个production source做source scan，每个production object做VALID depfile scan；全部必须拒 `CsrNativeTimingOracle.hpp` 与 `CsrNativeSemanticKeyTestSupport.hpp`，不能只扫scatter/core；
- oracle DTO header只允许`12.1`独立硬编码的test objects与public-header probes依赖；allow-list外任一test object依赖也失败；
- semantic-key helper reverse-dep allow-list exact为14 objects：既有graph export/encoding/property/projection四target各自的 `CsrNativeGraphRawProjector.cpp.o` 与 `CsrNativeGraphOracleReader.cpp.o` 共8个，加五个新functional target各自的 `CsrNativeTimingOracleReader.cpp.o` 共5个，再加native-oracle contract独占复用的 `CsrNativeGraphRawProjector.cpp.o` 1个；header source property及每个VALID depfile hard-code，唯一object增量就是该cross-consumer KAT；
- 两个既有fixture provider在五个functional target中产生exact 10个object实例；inventory逐target锁owner与VALID depfile，并额外证明这些provider depfile不含oracle DTO或semantic-key helper，禁止因COMMON扩展而扩大两类reverse allow-list；
- raw projector、旧graph oracle reader与top-level timing oracle reader分别exact include/call共享API，禁止三者重新声明 `makeNodeKey/makeArcBase/makeArcKeys`；Node/Arc子reader及independent encoder不得include helper；safe/poison另以duplicate builder和production `assignParallelOrdinals` 触发专用错误；
- 上述reverse-oracle/helper scanner具有source-safe/source-poison与depfile-safe/depfile-poison selftest，poison必须退出1并命中各自专用diagnostic；
- core拒Database/Arc/TimingPoint/oracle/scatter/snapshot/native propagator；
- snapshot拒adapter/scatter/oracle/Database，只复用pure fingerprint/helper；
- oracle reader拒production exporter/backend/scatter/table/FIFO/validator，并锁四个path-state const getter exact return type/noexcept及无copy/`const_cast`；
- Arc getter gate锁唯一production delay-map caller为const-qualified SDF读取，mutable调用只在三个test mutation allow-list；global prune、escape-hatch、public normalization与detached legacy-copy source KAT不得省略；
- materializer拒backend/scatter/native propagator；
- validation/preparation object拒native mutation symbols；
- publish source/object拒allocation/delete/lookup/hash/validator/exporter/logger/callback；source gate锁定Arc只授予exact publisher private friend、publisher对已验证state只做direct swap且不调用public normalization replacement；orchestrator source锁定non-const完整attempt构造与scratch析构早于唯一publish call，publish后的唯一语句为plain return，且逐个move/dtor trait static assertion齐全；
- scanner证明timing mutation只在publish TU；
- safe/poison selftests覆盖source、depfile、undefined-symbol、allocation detector；
- Step4 chained gate锁定exporter3、`validateReferenceInput` 6与`validateReferenceInputForSession` 4；Step5 chained gate证明其四target与slow oracle零漂移；
- typed-validator gate锁定七个exact modified files、classified两个production caller、legacy两项input precheck、single typed identity sink、八类枚举/mapping及所有result reject/helper显式class；两个result TU不得使用untyped `Violations/reject/appendViolations`；
- test target expected sources/objects在inventory脚本内独立hard-code；safe actual通过，交换contract/public packed list的poison invocation必须失败；
- public-header/include-order/standalone；
- exact `-Wall -Wextra -Werror -pedantic -ffp-contract=off`，受影响production TU另以`-Wswitch-enum` standalone严格编译，拒fast-math；
- 新增/重写文件小于700行，拒`const_cast`/C cast；
- child/parent diff-check、clang-format 21.1.8、artifact hygiene；
- 全CSR、相关legacy、unit/property/smoke及wheel等价门。

## 14. 实施与审查顺序

1. scatter/atomic与target/lifecycle两路独立设计审查；finding先修计划。
2. 冻结计划SHA并回填总计划。
3. Arc typed state与const/noexcept readers；跑legacy Arc。
4. fingerprints/helper迁移；跑snapshot回归。
5. oracle DTO、reader/encoder/KAT。
6. phased validator、stable resolver、detached preparation。
7. publish TU与static/nm门。
8. success/stale/atomicity/property。
9. native rerun。
10. CMake/inventory/isolation/wheel。
11. 两路未参与实现的code review；修正后重复。
12. 全门禁与as-built记录。

## 15. DoD 与非声明

DoD：fallback可读/恢复且被dynamic rerun消费；oracle覆盖全allow-list且只读；failure priority全可达且失败零写；stable resolution不使用source rank/address；publish only allow-list/no-fail；17/18/3和SCC不变；所有门绿；两路设计审查与两路code review APPROVE。

不声明真实session owner/token/commit/binding/parent observation、backend/native等价、generation>0 mutation、DualCSR/CUDA/speedup、crash/concurrent atomicity、topology/path-group/summary/power/report/SDF发布；不commit、不push。

## 16. v0.4 对既有及独立复审必审项的裁决

1. APPROVE：explicit token/generation只属于lower-level guard，真实owner留在Step7；
2. APPROVE：fingerprints下移pure types并由core唯一helper消费，不产生依赖环；
3. REVISED：删除六null→topology；采用`4.1` staged partial evidence，preflight invalid state与六family/multi-family均可精确判定；
4. APPROVE：write count固定 `21*N+8*E+1`，与21 node、8 arc、1 order family一一对应；
5. REVISED：rerun exact固定 `DelayCalculator::getInst().init()` 后接 `TimingPropagator::getInst().propagate()`，并以static inventory和地址/fallback KAT证明不重建Arc vector且消费installed fallback；
6. REVISED：删除generic validator→shape fallback，改用八类共享typed rule和exhaustive mapping；
7. REVISED：adapter17/core18/snapshot3全部source+depfile拒oracle header，仅`12.1` exact test allow-list允许，并有safe/poison selftest；
8. APPROVE：allocation ordinal覆盖export/validation/resolution/preparation，publish以static/nm/scanner证明零allocation；
9. REVISED：`5.1`冻结Step7由`STAInterface`持有共享Database-exclusive guard并覆盖所有mutation；
10. REVISED：`12.1–12.2`冻结每target exact source/object/link/options、Step4 exporter/validator计数、Step5零漂移、top test CMake、inventory与wheel清单；
11. REVISED：classified只接受已valid/supported input，legacy wrapper保留两项input precheck；Arc/Detail/identity纳入七文件exact allow-list及single typed sink；
12. REVISED：六executable落实为exact 11个CTest，并冻结各name/command/label/timeout及两个“不得direct注册”约束；
13. REVISED：`TimingPathState.hpp` 纳入exact production inventory，四string getter补const-reference/noexcept；oracle从 `const Database&` 到 `const TimingPathState&` 全链只读；
14. REVISED：抽取header-only `CsrNativeSemanticKeyTestSupport.hpp`，由既有raw projector、旧graph oracle与新timing oracle共享；handwritten/production/property KAT独立证明算法；v0.6仅让native-oracle contract复用一个既有raw-projector object做真实cross-consumer KAT，semantic reverse allow-list为exact 14，其余target零增量；
15. REVISED：legacy mutable Arc delay-map getter定义为先清全部provenance的有损逃生口，production全部const读取；每次update全局prune，并覆盖删除lane、dynamic重建及未触碰stale key；
16. REVISED：non-const完整success attempt在首写前构造，所有scratch先析构并逐成员nothrow-move/dtor证明；publish后只plain return，allocation failpoint保持armed直到caller收件。

v0.4 已由原 lifecycle/inventory reviewer与提出四项blocker的独立scatter/atomic reviewer对同一候选 SHA 双路 APPROVE。最终冻结 SHA 记录于总计划；任何正文变更都必须重新双审，状态元数据版SHA确认后方可编码。

v0.5 勘误缘由：首次真实链接证明`CsrTimingScatterTestFixture.cpp.o`保留analysis-context及native-fixture未定义符号，而冻结direct links均不提供；直接加入两个既有provider object是唯一不改变production、direct links与实现边界的修正。勘误不改变17/18/3、CTest数量、compile options、oracle/helper reverse allow-list或任何scatter语义；冻结前须由两路独立reviewer对同一候选SHA确认。

v0.6 勘误缘由：code review证明“逐项调用raw projection与timing oracle两个真实consumer”与“所有Step6 target都不链接raw-projector object”不可同时满足；复制算法、header-only替身、include `.cpp` 或跨executable拼接均不能证明真实consumer接线。最小修正只把既有 `CsrNativeGraphRawProjector.cpp` 追加到native-oracle contract：该target cpp 8→9、semantic helper reverse allow-list 13→14；COMMON、另五个target、direct links、compile options、17/18/3、CTest exact11与provider exact10全部不变。冻结前须由两路独立reviewer对同一候选SHA确认。

v0.7 勘误缘由：code review识别四个false-green/边界缺口：public replacement的subset归一化把lookup/delete带入publish；independent oracle把signed zero归一化；rerun在scatter已恢复baseline后可能no-op；timing-input success-only native drift在当前exact derivation闭包下不可达。最小修正采用exact private-friend direct swap、raw IEEE bits、post-scatter guaranteed-overwrite canary，并区分五类native success drift、phase-6 failure与六类pure-helper evidence；同时把legacy copying setter改为detached copy+swap并删除无caller的分叉optional-SoA overload，明确Step6 rerun exact仅覆盖forward scalar/data-slew与dynamic Arc而不复制path propagator。production object/target/link、17/18/3、CTest exact11与v0.6 source/object/reverse allow-list全部不变；仅test mutable getter source allow-list2→3。冻结前须由两路独立reviewer对同一候选SHA确认。
