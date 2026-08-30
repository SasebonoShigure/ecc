# 阶段 2 Step 2：Database 结构投影详细实施计划

> 状态：v0.2 设计已获多路独立 APPROVE；实现、测试与代码审查已完成，as-built 见 [stage2-report.md](stage2-report.md)
> 日期：2026-08-20
> 基线：parent `ee2563b2d27165d9324d82103cdf28bddb414956`，ecc-tools `a7355b216b801f72a99d92e77765f49c744148b3`
> 前置：Step 1 pure CSR foundation 已完成并获独立代码审查 APPROVE
> 审查基准：获批准的规范正文 SHA-256 为 `63e856e7364ec8a73d60c95dd17880a028bca622ae00f36aafacbe551bbf6bbd`
> 提交边界：本步骤不单独提交、不推送；仍按阶段 2 总计划 Step 10 一次性包装

本计划是 [阶段 2 总详细计划](stage2-detailed-plan.md) 第 14 节 Step 2 的规范化展开。Step 1 后的三路只读审计确认，原 v0.4 把完整 `CsrReferenceInput` 和完整 native timing oracle 排得过早；本文件冻结修正后的结构边界、API、target graph、测试和文字交付。

## 1. 审计结论与顺序修正

原 Step 2 不能诚实交付两个对象：

1. `CsrReferenceInput` 的 strict validator 已要求 nonzero token、六个 fingerprint、analysis context、deep Liberty transfer、constraints、start seeds、endpoint required、pin capacitance、output load、eligibility 和完整 unsupported reasons。identity 属于 Step 3，其余 immutable timing input 属于 Step 4；本步填空、填零或加 `partial` flag 都会制造假成功。
2. provisional `CsrNativeOracle` 内嵌完整 `CsrTimingResult`，但 `Arc` 的 timing-arc fallback provenance 仍为私有集合，Step 6 前无法无损读取。把 fallback 全写 false/default 会制造假 oracle。

顺序冻结为：Step 2 只导出 identity-free、non-committable `CsrGraphSnapshot`；Step 3 只实现 identity/observation pure contract；Step 4 才组合完整 immutable input、计算 identity、strict validate并原子materialize `CsrReferenceInput`；Step 6 才增加完整semantic-keyed timing oracle；Step 7才接session/binding，Step 8才做timing differential。

本步 API 中不得出现 `exportReferenceInput()`、`CsrCommittedSnapshot`、完整 timing oracle、scatter、generation、observation或session token。

## 2. 目标与明确非目标

本步目标：从 `const ista::Database&` 只读导出graph snapshot；按canonical key分配dense ID并保留native traversal；精确保留BaseOut/BaseIn、instance pin、root/start/end顺序；解码versioned semantic projection；以独立test-only raw projector验证round-trip；只读导出native timing order/node level结构oracle；建立无新增环的adapter target；用unit/property/fresh-process structural smoke证明正确性和只读性。

本步不构造/validate/commit `CsrReferenceInput`；不读取deep table数值、constraints、seed、required、cap/load、support reason或timing result；不运行production capture Kahn，active cycle仍可被结构snapshot表示；不建立identity/generation/capacity/observation；不接STAInterface/session/pybind/parent；不scatter、不实现backend/mutation/Dual-CSR/CUDA或性能声明。

## 3. 精确 typed schema

### 3.1 `CsrGraphSnapshot`

新增 `CsrGraphTypes.hpp`：

```cpp
inline constexpr auto kCsrGraphSnapshotSchema = "ista-csr-graph-snapshot/1.0.0";

struct CsrGraphArcRecord {
  ArcId id;
  ArcKey key;
  NodeId source;
  NodeId sink;
  ArcKind kind;
  std::uint64_t native_traversal_rank;
  bool is_clock_arc;
  bool is_disabled;
  bool is_loop_disabled;
};

struct CsrGraphSnapshot {
  std::string schema{kCsrGraphSnapshotSchema};
  std::vector<NodeRecord> nodes;
  std::vector<NodeIdLookupEntry> node_ids_by_key;
  std::vector<InstanceRecord> instances;
  std::vector<CsrGraphArcRecord> arcs;
  std::vector<ArcIdLookupEntry> arc_ids_by_key;
  std::vector<std::uint64_t> out_row_offsets;
  std::vector<ArcId> out_arc_ids;
  std::vector<std::uint64_t> in_row_offsets;
  std::vector<ArcId> in_arc_ids;
  std::vector<NodeId> ordered_root_ids;
  std::vector<NodeId> ordered_start_ids;
  std::vector<NodeId> ordered_end_ids;
};

struct CsrGraphContractViolation {
  CsrCaptureCode code;
  std::string field;
  std::string message;
};

struct CsrGraphExportFailure { CsrCaptureCode code; };
using CsrGraphExportResult = std::variant<CsrGraphSnapshot, CsrGraphExportFailure>;
```

snapshot复用Step 1 pure key/ID/node/instance DTO，但graph arc为独立record，类型层面不可能携带eligibility、transfer或output load。它也没有identity/context/capacity/constraint/seed/endpoint/cap/reason/metadata/timing字段。

本步failure code仅允许 `kMalformedTopology`（unknown/missing/stale reference、坏adjacency、unknown native enum、foreign library pointer、raw cell-port不一致）和 `kSemanticKeyCollision`。`kActiveCycle`不属于structural exporter。failure没有partial snapshot；`bad_alloc`、程序错误和未知异常继续抛出。

validator不抛出数据错误，按schema → nodes → instances → arcs → adjacency → ordered collections的固定顺序返回全部violations。`snapshot.schema`必须逐字等于`kCsrGraphSnapshotSchema`；空值、旧值或未知值首先产生`kMalformedTopology`，稳定field为`schema`。export/decode发现violations时返回首项code；同一输入的code/field/message顺序必须稳定，failure中仍无partial值。

### 3.2 `NativeGraphProjection`

新增 `NativeGraphProjection.hpp`，schema为 `ista-csr-native-graph-projection/1.0.0`。projection不用dense ID：

`NativeGraphProjectionResult`精确定义为`std::variant<NativeGraphProjection, CsrGraphExportFailure>`；decoder先strict validate snapshot，失败返回同一typed failure且无partial projection。


- node：NodeKey、direction、instance cell、net、port/start/end/sequential/clock/data/output roles；
- instance：name/cell、ordered NodeKey pins、sequential/check/gating/macro；
- arc：ArcKey、native traversal rank、clock/disabled/loop flags；
- adjacency row：canonical NodeKey row与保持native顺序的ArcKey vector，空行也存在；
- 顶层：schema、canonical node rows、native instance-map order、canonical arc rows、BaseOut/BaseIn、timing-point-map order roots、Database vector order starts/ends。

DTO使用exact defaulted equality，hash只作诊断。Step 4再组合 `NativeTimingGraphProjection{graph,constraints,transfers}`；本步不得声称constraint/transfer full round-trip。

精确DTO冻结为：

```cpp
struct NativeGraphNodeProjection {
  NodeKey key;
  PinDirection direction{PinDirection::kNone};
  std::string instance_cell;
  std::string net_name;
  bool is_port{false};
  bool is_startpoint{false};
  bool is_endpoint{false};
  bool is_sequential{false};
  bool is_clock_pin{false};
  bool is_data_pin{false};
  bool is_output_pin{false};
  friend bool operator==(const NativeGraphNodeProjection&, const NativeGraphNodeProjection&) = default;
};
struct NativeGraphInstanceProjection {
  std::string instance_name;
  std::string cell_name;
  std::vector<NodeKey> ordered_pins;
  bool is_sequential{false};
  bool has_timing_checks{false};
  bool is_clock_gating{false};
  bool is_macro{false};
  friend bool operator==(const NativeGraphInstanceProjection&, const NativeGraphInstanceProjection&) = default;
};
struct NativeGraphArcProjection {
  ArcKey key;  // source/sink只由key承载，不复制第二份endpoint字段。
  std::uint64_t native_traversal_rank{0};
  bool is_clock_arc{false};
  bool is_disabled{false};
  bool is_loop_disabled{false};
  friend bool operator==(const NativeGraphArcProjection&, const NativeGraphArcProjection&) = default;
};
struct NativeGraphAdjacencyRow {
  NodeKey node;
  std::vector<ArcKey> ordered_arcs;
  friend bool operator==(const NativeGraphAdjacencyRow&, const NativeGraphAdjacencyRow&) = default;
};
struct NativeGraphProjection {
  std::string schema{"ista-csr-native-graph-projection/1.0.0"};
  std::vector<NativeGraphNodeProjection> nodes;          // canonical NodeKey order
  std::vector<NativeGraphInstanceProjection> instances; // native instance-map order
  std::vector<NativeGraphArcProjection> arcs;            // canonical ArcKey order
  std::vector<NativeGraphAdjacencyRow> base_out;
  std::vector<NativeGraphAdjacencyRow> base_in;
  std::vector<NodeKey> ordered_roots;
  std::vector<NodeKey> ordered_starts;
  std::vector<NodeKey> ordered_ends;
  friend bool operator==(const NativeGraphProjection&, const NativeGraphProjection&) = default;
};
```

### 3.3 结构 oracle

删除provisional oracle中的`CsrTimingResult`，替换为 `CsrNativeGraphOracle.hpp`：

```cpp
inline constexpr auto kNativeGraphOracleSchema = "ista-csr-native-graph-oracle/1.0.0";
struct CsrNativeNodeLevel { NodeKey node_key; std::int32_t native_level; };
struct CsrNativeGraphOracle {
  std::string schema{kNativeGraphOracleSchema};
  std::vector<NodeKey> native_timing_order;
  std::vector<CsrNativeNodeLevel> native_node_levels; // canonical NodeKey order
};
```

oracle不含NodeId、Arc timing state、fallback或`CsrTimingResult`；level保持signed `int32_t`。reader只进入test target。完整`CsrNativeTimingOracle`延到Step 6。

## 4. Database → graph映射

### 4.1 Node与instance

- 遍历`pin_map`，要求map key等于Pin full name，且`timing_point_map`恰覆盖全部pin；`instance_map` key必须等于内部instance name，`net_map` key必须等于内部net name，已有`TimingCell`的cell-map key必须等于内部cell name；这些map key是projection的authority，内部name不一致即malformed，不能静默丢弃；
- port必须满足raw `pin_name == full_name`且`instance_name`为空，key只含kind/full_name；instance pin必须满足full name等于`instance_name:pin_name`、instance可解析、pin name在该instance ordered pin list中恰出现一次，并以这三个raw字段构造key；
- NodeKey按canonical encoded bytes排序后分配连续`[0,N)`，禁止map order/address/IDB ID；
- direction/is_port/net来自Pin；非空pin net name必须解析到同名net map key/internal name。instance cell与roles解析matching Instance；port的instance-only role全false；非空clock/data/output role name必须是该instance ordered pins中的exact full name；
- start/end bool只从Database vector membership派生。本步只验证vector无duplicate/stale、vector与派生bool逐项一致并保留既有顺序；因为logical role完整性还依赖Step 4才读取的clock/check constraints，本步不声称能检测真实start/end遗漏；
- instances严格按native map-name order；ordered pins保持`Instance::pin_name_list`且每个instance pin恰解析一次；instance cell name若能解析TimingCell，则同时要求cell-map key和内部cell name一致；不存在cell只允许进入下述合法fallback分支；
- `has_timing_checks = !check_arc_list.empty()`；gating直接读取；macro从matching TimingCell读取，cell不存在为false。

### 4.2 Arc、key与合法unbound fallback

- 按`arc_list` raw vector order读取base；source/sink/owner/type必须解析；cell两端必须是同一instance的ordered pins且owner等于该instance map key/internal name，net两端必须引用共同非空net且owner等于该net map key/internal name；
- bound cell arc解引用前必须证明`TimingCellArc*`属于当前instance cell的`cell_arc_list`，foreign/stale pointer先失败；随后要求pointed arc为`is_timing_graph_arc=true`，Arc raw source/sink library ports、endpoint local pin names和pointed TimingCellArc source/sink ports四方逐字一致；
- bound child signature保持native vector order，只读library name、signed index、sense、trigger/check、SDF condition及table presence/variable，不读axes/value。每个TimingArc的delay/slew map只允许`rise`/`fall` key，其他known/unknown transition均malformed；graph child的check-table map必须为空；
- signature-only validator独立执行canonical rules：unknown enum拒绝；`present=false`强制`variable1=variable2=none`；`present=true`允许二者都为none表示0D constant table，但`variable2!=none`时`variable1`也必须非none。它不借用Step 4的full table model validator；
- native合法unbound fallback cell arc的充分必要条件为：matching TimingCell不存在或其`cell_arc_list`为空，source是input/inout、sink是output/inout且二者不同，同时raw library ports都空且pointer null；同一fallback instance的unbound arc集合必须恰为ordered input-like × output-like的非self笛卡尔积、每对一次。cell list非空时，即使其中全部`is_timing_graph_arc=false`，也不得把null arc接受为fallback；
- 合法unbound arc的canonical ArcKey把library ports规范化为endpoint pin names，library signature为空；projection比较该规范语义，不比较raw空串。raw只空一端、null配非空identity、non-null配不一致ports，以及上述GraphBuilder不可产生的mixed状态均malformed；
- 该normalization保持现有validator“cell ports等于endpoint pin”契约，不丢arc、不新增伪unsupported；
- 完整base按raw order调用production `assignParallelOrdinals()`，之后按canonical ArcKey分配ArcId；rank保存raw index；flags不入key。

### 4.3 Adjacency与顺序

- BaseOut/BaseIn各为N+1 offsets，每个canonical NodeId一行；
- native adjacency map是稀疏容器：对已知节点用`find()`读取，缺key规范化为empty row且不得写回Database；map中出现unknown node key才是malformed；
- 已有row内遍历native adjacency vector并把raw arc index映射ArcId，禁止重建、去重或排序；raw index必须合法且方向匹配；duplicate/missing arc index均malformed，两张CSR各恰含每条arc一次并精确转置；
- roots为active `!disabled&&!loop_disabled` indegree零节点，按timing_point_map full-name order过滤；
- starts/ends保持Database vector order，只验证duplicate/stale、vector与membership-derived role相等及既有顺序；独立logical completeness延到Step 4；
- active cycle是合法structural snapshot；本步不运行Kahn、不返回`kActiveCycle`。

## 5. API、只读性与原子边界

```cpp
namespace ista { class Database; }
CsrGraphExportResult exportCsrGraphSnapshot(const ista::Database& database);
NativeGraphProjectionResult decodeNativeGraphProjection(const CsrGraphSnapshot& snapshot);
std::vector<CsrGraphContractViolation> validateCsrGraphSnapshot(const CsrGraphSnapshot& snapshot);
```

public header只forward-declare Database。export在local temporaries完成全部解析/build/validation，成功才move；decode不读取Database、不调用backend/Kahn。

为让只读由类型系统保证：仅在实际读取的 `Database/Pin/Instance/Net/Arc/TimingPoint/TimingLibrary/TimingCell/TimingCellArc/TimingArc/TimingTable` headers补窄const getter；禁止`const_cast`、读取时`operator[]`、`STADM`和任何写入；测试在export前后比较独立raw Database projection，必须完全相同。

test-only direct projector/oracle reader不得调用production adapter、decoder、record builder或`assignParallelOrdinals()`；它直接遍历raw Database，parallel ordinal用独立O(E²)此前等价base计数，只共享pure类型/token/canonical encoder。

structural snapshot/export完全不读取或验证native timing order与node level。test-only graph oracle可以忠实记录active-cycle Database中的partial timing order以及0/部分更新的level，不要求覆盖全部节点；独立slow FIFO若报告cycle，必须复现GraphBuilder“先update sink level、再decrement indegree”的处理顺序。

## 6. 无新增环的target graph

现有legacy target已有 `data_manager -> toolkit -> interface -> source -> data_manager` 环，因此adapter不得link `ista_data_manager`或加入该target。

```text
ista_timing_graph_csr_adapter
  PUBLIC  -> ista_timing_csr_core
  PRIVATE -> ista_timing_database_headers
ista_timing_database_headers
  LINK_LIBRARIES = empty
  INTERFACE_LINK_LIBRARIES = empty
```

header target只提供必要data-manager advance/basic与legacy logger include，不链接compiled target。adapter不include DataManager.hpp、不用STADM。Step 2只由tests/wheel显式链接adapter，不加入`ista_source/module/interface`；Step 7才允许interface单向PRIVATE链接adapter。

CMake顺序为data_manager/header → module/core → adapter → toolkit。configure gate检查core link为空、header两类link为空、adapter direct links精确为core+headers、adapter/header不链接legacy targets、`ista_source`本步不含adapter。

## 7. 文件级修改计划

生产新增：adapter `CMakeLists.txt`、`CsrGraphTypes.hpp`、`NativeGraphProjection.hpp`、`CsrNativeGraphOracle.hpp`、`CsrGraphEncoding.{hpp,cpp}`、`TimingGraphCsrAdapter.{hpp,cpp}`、internal header、arc export cpp、adjacency cpp、projection decoder cpp、`CsrGraphValidator.{hpp,cpp}`。

生产修改：删除/替换`CsrNativeOracle.hpp` full timing占位；上述native model header补const overload；source/data-manager/module CMake接无环target；semantic key/validator contract tests加入unbound normalization；test CMake、wheel和isolation gate接线。

测试新增：`CsrNativeGraphFixture.hpp`、独立projector/oracle reader、export/order/failure contract tests、fixed-seed property test、独立projection probe/controller及controller self-test。不得扩张664行Stage0 probe。

每个新production/test源硬门<700行，预算<550；接近预算按node/arc/adjacency/validator职责拆分。

## 8. 测试与防false-green门

### 8.1 Unit

覆盖empty/singleton/chain/diamond/multi-root；NodeId与map order不同；ArcId与raw rank不同；parallel 0/1；disabled/loop/clock arc；native row与ArcKey order相反；known-node absent adjacency key规范化为空row；instance pin/root/start/end；bound child signature/table token；合法unbound fallback；UTF-8 byte order。另以合法snapshot逐项mutation空/错误schema、signature presence/variable与transition-map/check-map规则；projection/oracle canonical bytes各有独立handwritten known answer、55/56边界和C++ encode→独立test decoder round-trip。

主断言：`direct raw Database projection == decode(export snapshot) == handwritten literal`。direct path不得调用production exporter/decoder；literal必须含非平凡row/ordinal。逐字段族mutation必须破坏equality。

failure覆盖missing pin/instance/timing point、pin/instance/net/cell bad map/internal name与ghost role ownership、extra unknown adjacency key、ghost/stale adjacency、duplicate/missing arc、wrong row、key collision、foreign/non-graph library pointer、partial/mixed raw ports、GraphBuilder不可产生的null fallback。failure无partial且Database不变。active cycle为snapshot正测，其native oracle允许partial order/level；独立slow FIFO才报告cycle。

### 8.2 Property

固定seed小图覆盖multi-root、parallel、disabled/loop overlay、空row、raw traversal/canonical ID错位；每seed独立CTest/timeout，失败打印seed与replay graph，不用`random_device`。验证round-trip、transpose、ordinal、row order、只读和determinism。

### 8.3 Fresh-process smoke

`CsrGraphEncoding`冻结`canonicalNativeGraphProjectionBytes()`与`canonicalNativeGraphOracleBytes()`：分别以`CanonicalEncoder.appendDomain("native-graph-projection","1.0.0")`和`appendDomain("native-graph-oracle","1.0.0")`开头，随后严格按3.2/3.3 DTO声明顺序编码；vector先U64长度，string/bytes沿用length prefix，bool/U64/I32沿用Step 1 big-endian，enum使用冻结token，NodeKey/ArcKey嵌入各自canonical bytes。该编码不含pointer、dense native index之外的地址、capacity或JSON实现细节。

probe result schema固定为`ista-csr-projection-probe/1.0.0`，所有JSON object均`additionalProperties=false`。exact required keys为`schema,run_nonce,case,top,expected_clock,repeat_index,input_case_sha256,node_count,arc_count,direct_projection,decoded_projection,native_graph_oracle,independent_fifo_oracle,projection_sha256,oracle_sha256,database_before_sha256,database_after_sha256,complete`。`direct_projection`/`decoded_projection`是上述projection canonical bytes的非空小写偶数长度hex，两个oracle字段同理；null、空串、空object和坏hex一律拒绝。controller内的独立strict decoder不得调用production encoder，必须验证domain/version、完整消费、enum、key、vector shape和`node_count/arc_count`，且chain/diamond两者都要求count为非bool正整数。

`run_nonce`为controller生成的32个小写hex字符，case为`chain|diamond`，`top`与`expected_clock`为非空字符串且必须逐字等于选中manifest case，repeat index为非bool非负整数，五个SHA字段为64个小写hex字符，complete固定true。`projection_sha256`/`oracle_sha256`分别是对应canonical bytes的SHA-256；before/after是export前后独立raw projection canonical bytes的SHA-256，二者必须等于projection hash。direct/decoded bytes和native/independent oracle bytes必须分别逐字相等。

controller result schema固定为`ista-csr-projection-controller/1.0.0`，exact required keys为`schema,requested_repeats,case_results,complete`；`requested_repeats`必须是非bool整数且`>=3`。`case_results`是按`chain,diamond`顺序的exact两项，每项exact keys为`case,repeats`，repeats包含且只包含索引`[0,requested_repeats)`的完整probe record。missing/extra/duplicate case或repeat、bad version/type/hash/equality、stderr非空、nonzero exit、incomplete均失败。

controller先strict解析共享的checked-in `baseline/manifest.json`，要求schema和exact `chain|diamond` case唯一，并逐项复算每个case声明的5个input file SHA。`input_case_sha256`定义为SHA-256(`CanonicalEncoder` domain `ista-csr-projection-input-case/1.0.0`，依次编码case `name,top,verilog,sdc,expected_clock`，再按canonical encoded path排序编码exact 5组`input path + 已复算SHA`)；它不是整个共享manifest的hash。controller把选中case的exact `name,top,expected_clock`、已校验input路径、case fingerprint、repeat index、nonce和唯一temp destination传给probe；这些构成运行现有hermetic full setup所需的完整canonical case descriptor。probe逐字段回传`case,top,expected_clock,index,nonce,input_case_sha256`，controller必须全部核对；每个case跨repeat projection/oracle hash稳定，chain和diamond的case fingerprint及projection hash必须不同，解码后shape必须非空。这样把输出绑定到真实case，禁止把chain运行两次冒充diamond。

新projection probe/controller对chain/diamond各至少3进程：现有hermetic parse/full建立DB；DB存活时只读export；direct projection等于decoded projection；native graph oracle等于独立FIFO order/level；content hash跨进程稳定；export前后raw projection相同；stderr空。每次controller运行使用`${CMAKE_CURRENT_BINARY_DIR}`下新的唯一run directory并先验证所有final不存在。probe只能以`O_EXCL`创建controller指定的nonce temp file，不接收final路径；子进程退出后controller验证final仍不存在、temp是本次regular file且完整通过schema/content校验，再由controller原子rename为per-repeat final。controller summary同样由controller写同目录temp并原子rename；预存/直接写final、缺temp、错误nonce或失败后的旧`complete=true`均不得成功。

该smoke只证明真实parser/GraphBuilder结构/library signature/level-order读取，不证明parallel/unbound/constraint/transfer/timing/scatter parity；synthetic-only分支须在报告标明。

### 8.4 Isolation/CI

core gate增加adapter/projection/oracle/native path禁词。core与adapter各自有configure-time双向exact inventory：target实际`SOURCES`与冻结expected `.cpp`列表逐项相等，expected source与expected Ninja object/depfile一一对应；缺失、额外或重复source/object均失败。随后对清单中的每个object读取`ninja -t deps`；adapter允许exact adapter/pure core/native model closure，拒绝DataManager.hpp、interface、propagator/analyzer/builder、scatter/backend和非必要toolkit。

target-property门精确断言core link为空、header target两类link为空、adapter只有`PUBLIC ista_timing_csr_core`与`PRIVATE ista_timing_database_headers`，且source/module/interface聚合均不含adapter。至少一个unit和每个property executable的direct `LINK_LIBRARIES`只允许`ista_timing_graph_csr_adapter;ista_timing_database_headers`，严禁legacy SCC；fresh probe可另链legacy。adapter对native enum使用本地explicit switch，不调用可能依赖out-of-line logger的native token/helper，让窄link直接暴露任何未声明符号依赖。

test-only source scan禁止互调production builder。新增`ista_csr_projection_controller_validation --self-test`并标`ista_unit`，覆盖exit 0无结果、nonzero exit、stderr、missing/extra/bad version、null/empty/bad-hex payload、bool或小于3的repeats、缺失/重复case或repeat、wrong top/expected-clock/case-fingerprint/nonce、same-payload cross-case、projection/oracle/hash mismatch、incomplete、预存/直接写final、缺temp和stale final。wheel显式build窄unit/property、projection probe/controller/self-test，并以`--no-tests=error`分别运行`ista_unit`、`ista_property`、`ista_smoke`。

最终还跑Step1 10 CSR tests、完整ista_unit、既有smoke、clang-format dry-run、diff-check、行数和generated leakage。

## 9. 实施、审查与完成门

顺序：本计划及总计划v0.5先获两名独立设计APPROVE；实现unbound normalization/const getter并回归Step1；实现types/adapter/validator/decoder；实现independent projector/property；实现fresh smoke；由未参与实现者读取最终diff并独立build/test，finding修复后重复；更新stage2 report；保持未提交未push并进入Step3。

只有设计APPROVE、schema/API/target按审查版实现、unit/property/smoke与isolation全绿、无full input/timing oracle/identity/session/scatter越界、Step1/Stage0/1无回归、format/diff/<700/leakage通过、代码审查APPROVE且报告无夸大时，才可写“Step 2完成”。
