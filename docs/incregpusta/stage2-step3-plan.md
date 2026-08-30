# 阶段 2 Step 3：Identity 与 Snapshot Observation Pure Contract 详细实施计划

> 状态：v0.4 已获独立设计审查 APPROVE，并于 2026-08-20 完成实现；C++、CMake/isolation 与 schema/parent 独立实现复审均 APPROVE、0 finding
> 日期：2026-08-20
> 已批准设计稿 SHA-256：`188d1184ec0e16f62339c484df515aed08fe5e722fc32fc1f308adcb44e2b050`
> As-built 证据：18 个 CSR target build；CSR 30/30；unit/property/smoke 65/65；parent 293/293；schema/parity 2/2、40 descriptors；详见 [stage2-report.md](stage2-report.md)
> 基线：parent `ee2563b2d27165d9324d82103cdf28bddb414956`，ecc-tools `a7355b216b801f72a99d92e77765f49c744148b3`
> 前置：Step 1 pure CSR foundation 与 Step 2 Database结构投影均已完成并获独立代码审查 APPROVE
> 提交边界：本步骤不单独提交、不推送；仍按阶段 2 总计划 Step 10 一次性包装

本计划展开 [阶段 2 总详细计划](stage2-detailed-plan.md) 第 14 节 Step 3。它只实现identity、raw analysis context、modeled storage、normative observation、strict parser和pure transition reducer，不从Step 2的partial graph snapshot伪造生产snapshot，也不接Database、session、binding、runner、timing backend或scatter。

## 1. 审计结论与规范修正

### 1.1 Identity syntax 与 committed generation分层

旧private `validateIdentity()` 对任意 `CsrSnapshotIdentity` 强制generation 0，但 `generation_mismatch` 的foreign source必须schema-valid且generation不同。首版冻结两层：

1. identity syntax：`fingerprint_schema_version == "1.0.0"`、nonzero u64 token、任意u64 generation、六个lowercase SHA-256；
2. Stage 2 committed identity：先通过syntax，再要求generation固定0。

outer observation、rejection current、invalidation previous、`CsrReferenceInput.source_identity`与本阶段`CsrTimingResult.source_identity`使用committed层；foreign rejection source使用syntax层；schema mismatch source固定null。

### 1.2 Buffer与modeled bytes必须只有一个真源

JSON `node_keys/arc_keys`分别映射`input.nodes/input.arcs`；其余四个CSR vectors和metadata三个level vectors合计九项。删除可手填六字段`CsrReferenceStorageMetrics`，新增的九字段metrics只能由visitor即时读取真实`size/capacity`。

`host_bytes`首版是outer observation schema v1冻结的modeled estimate，不是allocator/RSS。root object只计一次，nested vector/string按固定公式递归，checked u64 overflow，无缓存、无caller输入、无跨ABI golden。

### 1.3 Metadata必须exact FIFO replay

仅验metadata长度会让cycle或伪造level进入ready observation。现有core已有两份匿名Kahn，本步必须抽为唯一DB-free FIFO helper。本步三个consumer精确为`validateComputationResult()`的cycle-code一致性、`validateTimingResult()`和`validateCaptureMetadata()`；`validateReferenceInput()`只验证结构并必须继续接受active cycle。

builder只接受complete replay，并要求`level_offsets/level_nodes/node_to_level`与replay逐项相等。空图metadata精确为`{0},{},{}`。

Step 5 backend与Step 7 capture producer也必须复用同一helper；最终production call-site inventory精确为上述三个validator、backend、capture producer五处。独立性只由test-only slow oracle提供，禁止再写production Kahn。

### 1.4 None与released历史是transition contract

capture前、cpu/full、capture失败和无snapshot close均为None。schema/parser必须接收null，optional release允许`None -> None`。单份released对象只能验证shape，不能证明历史；Step 3同时实现pure reducer与before/after/action transition validator，Step 7必须使用后者。

## 2. 目标与非目标

### 2.1 目标

- identity syntax/committed generation-0 public validator；
- pure `StaAnalysisContext` exact validation、Python normalization与C++/Python canonical fingerprint parity；
- 唯一FIFO levelization helper和exact `CsrCaptureMetadata` validation；
- 九buffer/count/support/timing/capacity/modeled-host visitor；
- typed observation、rejection/invalidation event、static validator与无partial-success ready builder；
- reference/scatter/invalidation/release reducers及optional transition validator；
- exact JSON Schema、共享strict JSON/schema engine、分lane corpus；
- parent frozen dataclass/self-contained parser，尚不接运行路径；
- 独立snapshot-contract target及source/object/depfile/target-property isolation。

### 2.2 非目标

- 不新增`CsrCommittedSnapshot`，不发布production snapshot handle；
- 不从`CsrGraphSnapshot`补默认identity/input后冒充完整`CsrReferenceInput`；
- 不分配session token，不实现counter、lease或generation bump；
- 不读Database/native timing/constraint/Liberty/SPEF；
- 不实现Step 4 adapter、Step 5 backend、Step 6 scatter或Step 7 session/binding；
- 不修改parent `sta_session.py`、`module.py`、`runner.py`或artifact顺序；
- 不改Stage 1十字段record、incremental samples schema v1或existing golden；
- 不声称modeled bytes是heap/RSS、allocator call数或跨ABI可比。

## 3. Target graph与阶段消费边界

新增：

```text
ista_timing_csr_snapshot_contract
  PUBLIC -> ista_timing_csr_core
```

identity validator实现属于`ista_timing_csr_core`；snapshot target只编译metadata/storage/observation/transition。本步不把snapshot target聚合进`ista_module`、`ista_source`、adapter、interface或binding。

snapshot target允许include pure core public headers、`CsrCaptureMetadata.hpp`及自己的headers；禁止`CsrGraphTypes`、TimingGraph adapter、Database/native advance、interface、binding、GraphBuilder、propagator、backend和scatter。core仍禁止capture metadata与全部snapshot headers。

Step 3保持adapter的Step 2 exact links不变。Step 7 public adapter API将暴露observation DTO，因此届时adapter新增 `PUBLIC -> ista_timing_csr_snapshot_contract`；所有storage/transition调用由adapter-owned source封装，interface只直接 `PRIVATE -> adapter`，不include或调用snapshot implementation API。Step 7前必须重新冻结对应target-property gate。

Step 4 detached complete-input API由caller显式传入已canonical的analysis context和nonzero token；测试使用synthetic token。Step 4 adapter不分配token、不commit、不发布observation、也不链接snapshot target。Step 7才由session真实分配token，调用adapter组合并发布ready observation。联合contract测试可以同时link adapter与snapshot，但不得以测试link改变production target graph。

## 4. Identity与raw analysis context

### 4.1 C++ identity API

声明加入现有`source/module/timing_csr/CsrReferenceValidator.hpp`，实现新增`CsrSnapshotIdentityValidator.cpp`并编入core：

```cpp
validateSnapshotIdentitySyntax(const Identity&, string_view prefix)
validateStage2CommittedIdentity(const Identity&, string_view prefix)
```

二者返回现有`vector<CsrContractViolation>`。所有可表示contract错误返回violations，不以`invalid_argument/out_of_range`表示；`bad_alloc`等资源异常不伪装为validation result。

syntax检查顺序：version → token → six hashes；generation为u64 typed field，0到UINT64_MAX全合法。committed在完整syntax检查后追加generation==0。现有input/result validators删除private双真源，统一调用committed API。

### 4.2 Parent `StaAnalysisContext`

`sta_snapshot.py`集中frozen `StaAnalysisContext`、canonical validator/normalizer与两层fingerprint helper，但本步不被session/module/runner导入。公开pure API冻结为：

```python
normalize_sta_analysis_context(*, liberty_corner: str, temperature: str | int | float | Decimal, rc_corner: str) -> StaAnalysisContext
validate_sta_analysis_context(context: StaAnalysisContext) -> None
canonical_analysis_context_bytes(context: StaAnalysisContext) -> bytes
corner_fingerprint(context: StaAnalysisContext) -> str
```

exact三字段：

```text
liberty_corner: non-empty raw str, no edge whitespace
temperature: canonical decimal str | "__unspecified_temperature__"
rc_corner: non-empty raw str, no edge whitespace
```

liberty/RC运行时要求`type(x) is str`。temperature只接受exact `str|int|float|Decimal`，先拒bool及任意自定义`__str__`对象；string拒edge whitespace，numeric/string均用`Decimal(str(x))`解析并拒NaN/Inf，输出无指数/尾零并归一`-0 -> 0`。`validate_sta_analysis_context()`只接受已经canonical的frozen三string对象。不得复用runner里用于artifact label的permissive/sanitized helper。SPEF与`__no_rc_corner__`一致性留Step 7全corner preflight。

两层算法必须分开冻结：`canonical_analysis_context_bytes()`精确复现C++ `canonicalAnalysisContextBytes()`的`analysis-context` domain、length-prefix和UTF-8 payload；`corner_fingerprint()`再精确执行`componentFingerprint("corner-fingerprint", payload)`，即第二层domain后以`appendBytes`加入payload长度和payload。observation的`corner_fingerprint`只比较第二层结果。

固定双KAT：

```text
{slow, 25, __no_rc_corner__}
sha256(canonical_analysis_context_bytes) = 9d72757619bf1225c9888aa02b1f9917c8ea54a475754a8aae5939a7a96a1b83
corner_fingerprint = 095aeaf315c1c903fb0d166788cf05aa90af0055e41a25ae86e3458ce5f62a2a
```

UTF-8双KAT另固定多字节长度语义：

```text
{慢, 25, __no_rc_corner__}
liberty_corner UTF-8 length prefix = 3
sha256(canonical_analysis_context_bytes) = 06402d67b192a27d7caef43a34054c58938df1e20fd5b9aefaffc5bc8486b8dd
corner_fingerprint = e3bafb5e252ccc546ba306fd33f30122773840f1bc37a616752ebb96da26eec2
```

C++ fingerprint contract test与Python测试分别独立固定ASCII和UTF-8两组、每组payload与component两层KAT；Python不得调用C++或复制C++输出文件作为expected，也不得用code-point数量代替UTF-8 byte length。

## 5. 唯一FIFO helper与metadata contract

在core新增`CsrFifoLevelization.{hpp,cpp}`，替换`CsrReferenceValidator.cpp`和`CsrTimingResultValidator.cpp`两份匿名实现。输入只含`CsrReferenceInput`，输出：

```cpp
struct CsrFifoLevelization {
  bool complete;
  vector<uint64_t> level_offsets;
  vector<NodeId> level_nodes;
  vector<uint64_t> node_to_level;
};
```

语义保持native/root contract：按`ordered_root_ids`入FIFO，按BaseOut row order遍历eligible levelization arcs；root level 1；处理arc时先更新sink level、再decrement indegree；complete仅在每节点恰出队一次时true。helper对malformed input不承担越界防护，调用前必须先通过`validateReferenceInput`；direct helper tests只给valid input。

snapshot target的public `validateCaptureMetadata(input, metadata)`唯一拥有一次完整`validateReferenceInput()`调用；通过后调用helper并要求complete，再exact比较三个vector。ready builder只调用该public validator一次，不另做重复input validation。内部如需拆shape/replay helper，只允许接收已验证input且不公开。shape错误稳定field：offsets非空/首0/单调/末N；level_nodes是`[0,N)`精确排列；node_to_level size N且与bucket互逆；空图exact `{0},{},{}`。cycle、正确尺寸但wrong order/bucket/map均失败，ready builder不返回observation。

新增独立`CsrFifoLevelizationContractTest.cpp` direct-link core，覆盖empty/single/multi-root/parallel/disabled/loop/cycle以及complete/order/level exact；`validateReferenceInput()`接受valid cyclic fixture、computation validator才核对cycle code。

## 6. Typed observation与唯一JSON映射

`CsrSnapshotObservation.hpp`放在`source/module/timing_csr_snapshot/`，不增长当前`CsrReferenceTypes.hpp`。复用已有state/capacity/scatter/invalidation/support enums，不新增rejection enum。

C++ exact成员：

```cpp
struct CsrSnapshotCounts { uint64_t nodes, arcs, levels; };
struct CsrSnapshotBufferMetrics {
  CsrBufferExtent node_keys, arc_keys, out_row_offsets, out_arc_ids,
                  in_row_offsets, in_arc_ids, level_offsets, level_nodes, node_to_level;
};
struct CsrCapacityObservation { CapacityAction last_action; uint64_t event_count; };
struct CsrSupportObservation { bool reference_supported; vector<CsrReferenceUnsupportedReason> unsupported_reasons; };
struct CsrTimingObservation { double export_ms; optional<double> reference_ms, scatter_ms; };
struct CsrModeledHostBytes { uint64_t logical, capacity; };
struct CsrCurrentFingerprints {
  optional<string> topology_fingerprint, clock_constraint_fingerprint,
                   library_fingerprint, corner_fingerprint,
                   parasitic_fingerprint, timing_input_fingerprint;
};
struct CsrScatterRejectionEvent { CsrScatterCode reason; uint64_t writes_applied; optional<Identity> source; Identity current; };
struct CsrInvalidationEvent { CsrInvalidationReason reason; uint64_t writes_applied; Identity previous_identity; CsrCurrentFingerprints current_fingerprints; };
struct CsrSnapshotObservation {
  string schema_version; State state; Identity identity; Counts counts;
  BufferMetrics buffers; Capacity capacity; Support support; Timing timing_ms;
  HostBytes host_bytes; optional<Rejection> last_rejection;
  optional<Invalidation> last_invalidation;
};
```

JSON字段与上述成员同名，唯一例外是C++ timing的`export_ms/reference_ms/scatter_ms`分别映射JSON `export/reference/scatter`；parity test使用显式映射表，不能把dataclass field set直接当JSON key set。

九buffer唯一真源：node_keys→input.nodes；arc_keys→input.arcs；四个out/in字段→同名input vectors；三个level字段→同名metadata vectors。counts来自nodes.size、arcs.size和level_count。support bool恰等于unsupported reason vector为空，reason由input复制并保持stable order。

API exact返回类型：

```cpp
using CsrObservationResult = variant<CsrSnapshotObservation, vector<CsrContractViolation>>;
using CsrOptionalObservation = optional<CsrSnapshotObservation>;
using CsrOptionalObservationResult = variant<CsrOptionalObservation, vector<CsrContractViolation>>;

makeReadySnapshotObservation(const CsrReferenceInput&, const CsrCaptureMetadata&, double export_ms)
```

error alternative必须nonempty且无partial observation。builder只调用一次拥有input/committed-identity validation的`validateCaptureMetadata()`，成功后依次执行storage visitor → construct → static observation validator。

## 7. Modeled storage visitor v1

删除可手填六字段`CsrReferenceStorageMetrics`，保留`CsrBufferExtent`。`CsrSnapshotStorage.{hpp,cpp}`返回九extent和host bytes；公式由outer observation schema `1.0.0`版本化，改变公式必须bump observation schema。

计算规则：

1. logical/capacity均从`sizeof(CsrReferenceInput)+sizeof(CsrCaptureMetadata)`开始，root只计一次；
2. vector object已在root/parent slot，不再加object size；logical加`size*sizeof(T)`，capacity加`capacity*sizeof(T)`；
3. 只递归`[0,size)`已构造元素的dynamic members；reserved slots不递归；
4. string object已在root/slot；logical加`size()`、capacity加`capacity()`，不加terminator/allocator metadata；SSO仍按此模型计数，与`sizeof(string)`表示的inline storage重叠是有意的versioned model；
5. array自身无backing bytes，但必须递归每个元素的dynamic members；optional dynamic object仅presence true时递归；scalar/enum/StrongId/optional scalar不递归；
6. 穷举input全部dynamic字段：顶层`schema_version`；identity的version与六hash；analysis context三string；nodes/lookups/instances/arcs与nested signatures/tables/axes/values；四CSR vectors、roots/starts/ends、clock tags/constraints/case/seeds/endpoints/caps/reasons；以及metadata三vectors。前三组精确为11个root string backing，不能被`sizeof(root)`替代；
7. 所有size_t→u64、add、mul、sum使用同一个production accumulator checked API；overflow返回field-specific nonempty violations，无wrap/saturate/partial report；
8. logical<=capacity，且任何非None observation两值都至少`sizeof(input)+sizeof(metadata)>0`。

visitor只读取对象，不把结果写回input/metadata。reserve仅改变capacity与host capacity，不改logical、canonical bytes或fingerprint；copy/move后重新读取目标对象真实capacity。

storage executable还必须实现一份不调用production visitor的test-only同ABI exact formula/delta oracle：只使用运行时`sizeof`、实际size/capacity和独立checked arithmetic，不保存跨ABI golden。它逐项断言root logical/capacity恰计一次、vector已构造slot恰计一次、reserved slot不递归、nested array/table递归、SSO短/长string backing、terminator增加量恒为0，并按每个dynamic family比较exact logical/capacity delta；因此把root/backing重复计数、额外加terminator或递归reserved slot都必须失败。另保留逐dynamic family mutation sensitivity、reserve/copy/move真实性与production accumulator add/mul/sum overflow测试。

## 8. Static validator、event与reducers

### 8.1 单对象规则

顺序：schema/state/committed identity → counts/buffers → capacity/support/timing/host → rejection → invalidation → state/event组合。

九个logical exact等式：node_keys=N、arc_keys=E、out/in row offsets=N+1、out/in arc IDs=E、level offsets=L+1、level nodes=N、node_to_level=N；全部+1 checked。`N==0 iff L==0`，`N==0 => E==0`，非空图`1<=L<=N`。每项capacity>=logical。

capacity固定`initial_allocate/1`；support reasons known、strict enum order、unique，supported iff empty。timing为nonnegative finite double/optional；event非null时scatter_ms必须non-null。host logical/capacity均>0且logical<=capacity。

state组合：ready=`(rejection null|object, invalidation null)`；invalidated=`(null, object)`；released可具有前两类保存形状，历史equal由transition validator证明。unknown enum、NaN/Inf、坏optional均返回violations；除资源异常外，malformed值不抛。

### 8.2 Rejection

reason只允许existing八项 mismatch code，writes固定0，current等于outer committed identity。

优先级：schema mismatch→source null；session mismatch→source syntax-valid/token different；generation mismatch→same token/generation different；source identity mismatch→same token+generation/至少一hash different；shape/numeric/id/predecessor→source与current逐字段equal。较早reason成立时后续差异不抢分类。

### 8.3 Invalidation

previous identity等于outer committed identity，writes 0。current_fingerprints显式六字段，每项hash或null。按topology→clock_constraint→library→corner→parasitic→timing_input，第一个null或different唯一决定reason；全相等non-null不能invalidate。

### 8.4 Reducer与optional transition

action不是自由字符串。C++冻结`CsrObservationActionKind`六值enum、`token(kind)`与六个typed variant alternatives；variant不重复存kind，非valueless action的kind由alternative唯一导出。Python冻结同名frozen action dataclass union，stable token精确为：

```cpp
enum class CsrObservationActionKind : uint8_t { kRead, kReferenceMeasurement, kScatterRejection, kScatterSuccess, kInvalidation, kRelease };
```

```text
read | reference_measurement | scatter_rejection | scatter_success | invalidation | release
```

payload精确为：read/release无payload；reference measurement与scatter success各含`duration_ms`；scatter rejection含`reason/source/duration_ms`；invalidation含`current_fingerprints/duration_ms`。duration均finite nonnegative。C++ API：

```cpp
using CsrObservationAction = variant<ReadAction, ReferenceMeasurementAction,
                                     ScatterRejectionAction, ScatterSuccessAction,
                                     InvalidationAction, ReleaseAction>;
using CsrObservationActionKindResult = variant<CsrObservationActionKind, vector<CsrContractViolation>>;
CsrObservationActionKindResult observationActionKind(const CsrObservationAction&);
CsrOptionalObservationResult reduceSnapshotObservation(
    const CsrOptionalObservation&, const CsrObservationAction&);
vector<CsrContractViolation> validateSnapshotObservationTransition(
    const CsrOptionalObservation&, const CsrOptionalObservation&,
    const CsrObservationAction&);
```

声明顺序以实际C++可编译性为准，但所有action入口必须先检查`action.valueless_by_exception()`：`observationActionKind()`返回field=`action`的nonempty violation alternative，reducer/transition validator透传同一错误，任何路径不得在检查前调用`get`/`visit`或抛`bad_variant_access`。测试若当前标准库和六个alternative无法稳定构造valueless实例，则用compile-time nothrow-property加source call-site inventory证明防御分支仍存在；一旦可构造，必须加入定点no-throw负测。

Python public API镜像为`reduce_snapshot_observation(before, action)`和`validate_snapshot_observation_transition(before, after, action)`；前者返回typed optional或抛`StaSnapshotContractError`，后者成功返回`None`、失败抛同一structured exception。Step 7 parent只调用这两个公开函数，不重写transition逻辑。unknown C++ enum/action token与Python unknown action均拒绝，并做token parity。

每个action reducer先static validate输入，copy后修改，再validate输出；失败返回nonempty violations/抛structured exception且原对象equal：

- read：None→None或任意valid object→逐字段exact equal object；
- reference measurement：ready object only；设置/覆盖reference_ms；
- scatter rejection：ready object only；覆盖last_rejection并设置scatter_ms；
- scatter success：ready object only；清last_rejection并设置scatter_ms；
- invalidation：ready object only；推导reason，原子清rejection、写invalidation、state→invalidated并设置scatter_ms；
- release：None→None，或ready/invalidated→released且除state外所有字段`operator==`；
- read是唯一在全部optional/state组合都合法且绝不改变字段的action；除read外的state-changing action矩阵精确为：None只允许release，ready允许reference/scatter/invalidation与release，invalidated只允许一次release，released不允许任何mutating action或二次release。换言之，None允许read+release，ready允许六action，invalidated允许read+release，released只允许read。

transition validator先static validatenon-null端，再根据typed payload检查exact changed/preserved set，并要求`after == reduce(before, action)`。除read/release的None→None外，其他成功action两端必须object；任何action都不得成功地产生None→object或object→None。reject→success→reject、ready→invalidated→released、ready→released，以及ready/invalidated/released/absent read逐字段exact preservation均覆盖。

## 9. JSON Schema、parent parser与分lane corpus

### 9.1 Shared strict JSON/schema engine

现有`validate_incremental_sta_samples.py`已694行。本步抽取其duplicate-key loader、finite number、draft subset resolver/validator到同目录test-only `json_schema_contract.py`，旧incremental validator和新snapshot validator共同import；迁移后必须重跑原schema self-test。禁止复制generic engine。

新增：

- `csr_snapshot_observation_v1.schema.json`；
- `validate_csr_snapshot_observation.py`；
- corpus manifest及raw/object/transition case files。

root schema为`anyOf [null, exact object]`。每层additionalProperties=false。`identitySyntax` generation为integer u64；`committedIdentity`在其上要求integer且const0。writes/event_count等const字段同时声明integer/u64，避免JSON numeric equality让0.0/1.0冒充integer。

duration schema为JSON number；companion validator/parser接受非bool int或float，转为Python float后要求finite nonnegative。超大int若不能有限转换则拒绝。此规则不区分合法`0`与`0.0`，最终dataclass统一为`0.0`；schema-alone只验证declarative shape，combined validator才执行cross-field/finite/history语义。

### 9.2 Parent实现

为保持<550目标，parent拆为：

- `sta_snapshot.py`：public enums/dataclasses/context normalizer/fingerprint/parser facade与`StaSnapshotContractError`；
- `_sta_snapshot_validation.py`：nested mapping helpers、single-object/transition rules和structured errors。

依赖固定单向：public模块拥有全部types/exception；private helper只能在`TYPE_CHECKING`下引用public types，public parser/reducer facade在函数内延迟import private helper，禁止module-import cycle。

`StaSnapshotContractError`继承`StaExecutionContractError`，并带稳定`.field`与`.category`。field path grammar固定为root `$`、property `$.identity.graph_generation`、array `$.support.unsupported_reasons[0]`；missing/extra指向`container.expected_key`，non-string key指向container。category token固定为：

```text
json_syntax | duplicate_key | key_type | missing_key | extra_key |
value_type | enum | format | range | non_finite | shape |
relationship | transition | overflow
```

primary error优先级为raw syntax/duplicate encounter order → mapping key_type → missing schema order → extra lexicographic → scalar field schema order → cross-field order → transition；每个corpus mutation必须只瞄准一个primary branch。root为null时直接合法；root为Mapping时直接走object branch并保留具体nested issue；其他root只报`$ / value_type`，禁止把object错误折叠成generic `anyOf`。

每层mapping先copy，逐key要求`type(key) is str`，再比较exact key set；u64始终`type(x) is int`，bool先拒绝。`snapshot_observation_from_mapping(Mapping|None)`返回typed object或None。

parent runtime文件自包含constants/rules，绝不读取child schema/corpus，因为wheel排除thirdparty。只有parent tests从source tree读取child schema/corpus做parity。本步不改session/module/runner；Step 7仍须用raw corner/temperature/RC并在engine/artifact前全corner preflight。

### 9.3 Corpus lanes

manifest为每case声明适用lane、baseline、lane-specific mutation recipe与expected validity/field/category/message：

1. `raw_loader`：独立raw JSON text，覆盖duplicate key、NaN/Infinity、syntax/trailing；Mapping/C++不宣称可重放；
2. `mapping`：从canonical baseline按recipe构造Python object/null，覆盖missing/extra、注入integer key、bool-as-int、NaN/Inf、negative/overflow、cross-field；child companion和parent parser同判；
3. `typed_cpp`：C++ compiled mutation factory按同一case id构造DTO，覆盖unknown enum cast/hash/range/cross-field/action/transition；断field+稳定message；
4. `transition`：baseline before加typed action和after mutation，action统一使用§8.4 token，不再使用未定义`kind`。

recipe vocabulary至少冻结`replace_value|delete_key|add_key|add_non_string_key|nan|positive_infinity|negative_infinity|unknown_enum`；每个lane可有不同recipe，不能要求普通JSON直接表达non-string key/NaN/enum cast。raw text单独存文件，普通manifest本身保持strict JSON。

C++ production/test不引入JSON parser。identity/FIFO/storage/observation/transition五个executable的compiled case table支持`--list-case-contracts`，每案输出exact 10列ASCII TSV：

```text
case_id  baseline  recipe_op  target  operand  action_token_or_dash  expected_validity  expected_field  expected_category_or_dash  expected_message
```

列分隔符是单个TAB；所有字段禁止TAB/CR/LF，空语义使用`-`而非空列。`expected_validity`只允许`valid|invalid`，action token必须为§8.4 stable token或`-`，recipe/target/operand必须与该C++ factory实际执行的mutation/action完全一致。manifest的每个`typed_cpp` lane保存同一compiled-contract descriptor；test-only Python parity CTest解析五个executable输出，要求全局case id唯一，并把排序后的完整10列descriptor与manifest projection逐字exact比较。缺/多/重、同ID不同recipe/field/category/message均失败，禁止只比较ID集合或让C++另写一套expected。

共享semantic case id只要求适用lane一致，禁止要求C++表示wire shape错误或Mapping检测duplicate key。child/parent异常比较structured field/category，不解析字符串。每个mutation先验证baseline valid。

## 10. 文件与CMake修改

### 10.1 ecc-tools production

- `source/module/timing_csr/CsrSnapshotIdentityValidator.cpp`；
- `source/module/timing_csr/CsrFifoLevelization.{hpp,cpp}`；
- `source/module/timing_csr_snapshot/CMakeLists.txt`；
- `source/module/timing_csr_snapshot/CsrSnapshotObservation.hpp`；
- `source/module/timing_csr_snapshot/CsrSnapshotStorage.{hpp,cpp}`；
- `source/module/timing_csr_snapshot/CsrSnapshotObservationValidator.{hpp,cpp}`；
- `source/module/timing_csr_snapshot/CsrSnapshotObservationTransition.{hpp,cpp}`；
- 窄改`CsrReferenceValidator.hpp/.cpp`、`CsrTimingResultValidator.cpp`复用identity/FIFO helper；
- 窄改`CsrReferenceTypes.hpp`删除手填metrics；
- 窄改source/module CMake、test CMake、wheel action和core/adapter isolation gates。

### 10.2 tests/schema

- `CsrSnapshotTestFixture.{hpp,cpp}`；
- identity、FIFO、storage、observation、transition五个contract executable；identity/FIFO只direct-link core，其余只direct-link snapshot target；
- 修改`CsrMetadataIsolationTest.cpp`，只删除旧手填metrics块并保持core-only；所有visitor-derived断言放storage executable；
- `CheckCsrSnapshotContractIsolation.cmake`；
- shared schema engine、新schema/validator、分lane corpus。

identity/FIFO executable只direct-link core；storage/observation/transition只direct-link snapshot target；联合adapter测试单独列明。snapshot target不得出现在source/module/interface aggregates；adapter Step 3 dep gate禁止snapshot headers。wheel显式build五个C++ executable并注册Python schema与compiled-contract descriptor parity CTest。

### 10.3 ECC parent

- `chipcompiler/tools/ecc/sta_snapshot.py`；
- `chipcompiler/tools/ecc/_sta_snapshot_validation.py`；
- `test/tools/ecc/test_sta_snapshot.py`，接近550行时按context/schema/transition自然拆test文件。

不改`sta_session.py`、`module.py`、`runner.py`。

## 11. 实施顺序

1. 同步修订总计划§5/§7.1/§11/§12/§13/§14/§16/§17和本计划，取得至少两路新SHA独立APPROVE；
2. 落identity/FIFO core helper，迁移两处旧实现并跑Step1/2回归；
3. 落metadata validator、typed observation、九buffer/storage visitor；
4. 落static validator、ready builder、events、reducers和optional transition；
5. 建snapshot target和exact target/source/object/depfile gates；
6. 抽shared schema engine，落schema/corpus/child validator；
7. 落parent context/parser/validation/parity tests；
8. clang-format/Ruff、全门禁与独立代码审查；有finding即修正重审；
9. 更新Step 3 as-built报告，不提交、不推送，继续Step 4。

## 12. Correctness矩阵

### 12.1 Identity/context/FIFO

- token 0/1/MAX、generation 0/1/MAX、六hash逐字段坏值；syntax接受nonzero generation，committed拒绝；
- generation mismatch source=1/MAX合法，schema/session/generation/source priority交叉；
- raw context exact input types/custom `__str__`/whitespace/bool/NaN/Inf/numeric string/exponent/trailing zero/-0/sentinels；ASCII与`慢` UTF-8 byte-length两组payload SHA/corner component双层C++/Python KAT exact；
- empty/single/multi-root/parallel/disabled/loop FIFO；cycle incomplete；metadata empty/correct/wrong size/order/bucket/map/duplicate/OOB；
- 五个production consumer使用同一helper的source/dependency inventory，禁止残留匿名Kahn；`validateReferenceInput` cyclic正测。

### 12.2 Storage/buffers

- empty与nonempty九extent、N/E/L等式和N/L domain；每个logical field独立mutation；
- `N=0,E>0,L=0`且extent自洽的反例；
- test-only同ABI exact formula/delta oracle冻结root/slot/backing只计一次、reserved不递归、nested array/table、11个root string、其余deep dynamic、SSO短/长string与zero terminator bytes；
- reserve只改capacity，push/erase改logical，copy/move重测真实capacity；
- checked accumulator add/mul/sum/MAX overflow；host logical/capacity均>0；
- input bytes/fingerprint不受reserve/metadata影响。

### 12.3 Observation/reducer

- ready/invalidated/released与None合法/非法组合；
- capacity/support/timing/host逐字段enum/type/range/cross-field；
- 八rejection和六invalidation逐reason/priority/first difference；event要求scatter timing；
- reference null→0→positive；reject→success→reject；ready→invalidated→released；ready→released；None→None release；
- read在None/ready/invalidated/released逐字段exact preservation；六action token/payload/unknown/valueless防御；invalidated只允许read+release，released只允许read；失败原对象equal。

### 12.4 Schema/parser lanes

- raw duplicate/NaN/Infinity/trailing；mapping missing/extra/non-string key/bool/negative/MAX/overflow；typed unknown enum/hash/event关系；
- schema-alone与companion职责分开，duration int/float均规范为float；
- generic identity可nonzero generation，outer/current/previous committed 0；
- raw/mapping/typed/transition manifest applicability与structured field/category；五个C++ executable的10列compiled-contract descriptor与manifest逐字段exact；
- parent runtime不访问thirdparty，test-only parity读取child assets；
- `StaExecutionRecord`字段与Stage1 tests完全不变。

## 13. 完成门

child：五个新C++ executable、schema/compiled-contract descriptor parity CTest、snapshot/core/adapter isolation、全部`^ista_csr_`、完整`ista_unit/property/smoke`、wheel explicit targets、clang-format 21.1.8、Mulan、每个新增/重写C++/Python/test文件<700且目标<550、diff-check/generated hygiene。

parent：snapshot/context/parser/transition/parity tests、全`test/tools/ecc`定向回归、Ruff check/format、scoped pyright或现有等价type check、diff-check。

最终review必须确认：没有generic gen0误用、caller metrics、duplicate FIFO/schema engine、released历史假验证、target反向依赖、parent runtime child-asset依赖、`CsrCommittedSnapshot`、token allocation、binding/scatter/production capture越界。

全部通过只表示Step 3 pure contract完成。Step 4仍须由caller提供token/context，在local complete input strict validation成功后返回detached完整candidate；Step 7才真实分配session token并发布observation。
