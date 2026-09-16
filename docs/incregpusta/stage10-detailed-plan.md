# Stage 10：补齐功能与真实设计验证

日期：2026-09-15。状态：实现与功能验收完成，独立审查 APPROVE；剩余 lint/type 失败和实际验证结果见 [实施与验收报告](stage10-progress-report.md)。以下保留实施方案和历史设计审查。

## 目标与起点

遵循总计划 Stage 10 和开发检查规范。补齐 sequential_instance、sequential_launch、timing_check、crpr、clock_tree_fanout、conditional_timing_arc 六类语义，使 xtea、usb、zipdiv 的 CPU/full、CPU/incremental、CUDA/full、CUDA/incremental 在原 ICS55 post-synthesis、无 SPEF 输入下完成 baseline 和真实多批 data-only frozen trace。

起点为 ecc `7c9cfe9`、ecc-tools `cbf035a12`，包含开始时已有未提交差异。原始 patch 与文件身份保存在本轮 build 证据目录；不覆盖 CLAUDE.md、用户报告、overview 或其他已有改动，不升级依赖，不修改通用 README，不自动 commit/push。

## 语义依据与边界

- native CPU/full 是独立黄金 oracle，保留原 ClockPropagator、TimingPropagator、TimingAnalyzer 和 DelayCalculator 的计算过程；不能让 oracle 改为调用待验收 CSR/backend。
- 本阶段支持既有 ideal-clock contract 下的时钟树扇出、顺序起点、CTQ、setup/hold/recovery/removal 和 CRPR 身份。propagated clock、clock gating/divider、case analysis 与 parasitic net 仍按原 typed reason 拒绝；不借六类语义扩展整个 STA 支持范围。
- native ideal clock 在所有可达 clock point 上具有 effective arrival/slew=0，effective predecessor 为空；仍计算 physical clock arrival/slew/predecessor。CRPR 使用 effective clock 路径，ideal clock 的校正为 0，但 launch clock node/transition 仍须完整传递和 scatter。不得伪造传播态或宣称已验证非零 propagated-clock CRPR。
- native DelayCalculator 不求值 sdf_condition；保留带条件的完整候选弧，按 trigger/sense、table presence 和 max/min 选择。条件字符串继续参与身份、报告与 SDF；不新增布尔解释器，不删除条件弧以获得通过。
- 未编辑初始化是 baseline_only/full。真实编辑仍在 isolated iSTA Database 与 host/device CSR 原子提交，full propagation 不变；EngineDB/IDB、placement、RC 与 closed-loop greedy 属于 Stage 11。

## 实现方案与接口

### 1. 共享输入与 CPU reference

- 复用已有 CsrReferenceInput 中的 nodes、instances、clock_owner_by_node、timing_check_endpoints 和 referenced_library_cells。扩展现有 TimingPayloadView 的只读访问，并同步 Flat/Dual 两个实现；不新增策略层或复制一份顺序专用完整 graph。
- 顺序 seed 保持由原始约束与 library role 推导，未计算 arrival/slew 的结构记录由 backend 在 clock pass 后解析。将原 kUnsupportedSequential 名称和仓内消费者统一迁移为 kDeferredSequential，明确这是待计算种子而非完成态；同一数值枚举不保留兼容别名。外部捕获结果和 validator 对应迁移 token，记录该诊断表示变更。
- 在 CsrCpuReferenceBackend 的 arc initialization 后、data propagation 前增加 clock propagation 与 deferred sequential seed 初始化。复用 evaluateCsrDynamicArc 的 table/单位/舍入规则，以 clock eligibility、原生 FIFO 顺序和 owner 执行 physical slew、physical arrival；effective ideal clock 由约束初始化。数据 slew/arrival 随后使用有效 clock seed，不复制 native timing 结果。
- 顺序 CK 起点使用 clock-to-Q 首个 trigger 的 effective clock arrival/slew，path_start 指向 Q，保留 register source、CRPR node/transition；Q 起点按原生 clock-to-Q arc 和当前 output load 计算，缺 clock 或非 register 起点仍遵守原生 scalar/slew 与 path presence 的不同规则。
- endpoint scalar required 按原生 max-analysis 选择顺序：优先 input path，再 register path；保持 rise/fall 与 clock-tag 首 winner 和 epsilon。选择首个匹配 setup/recovery check、应用 transition/table 选择和双轴单位换算、舍入，然后执行现有 backward propagation。hold/removal 及逐 path 检查由现有 analyzePropagatedTiming 对已发布路径计算，不能重新执行数据传播。
- 新增专用 clock/sequential 计算文件，避免在已很长的 reference validator/propagation 文件中散落特殊分支。必要验证留在公共入口；受控 stage 内不增加重复全图扫描。

### 2. CUDA full 与持久 Dual-CSR

- 在 device NodeState 保存 physical clock lanes 与 predecessor，在 PathState 保存 CRPR node/transition；Arc 打包保留 clock eligibility。复用现有缓冲区所有权、容量检查、D2D candidate 和 unpack/scatter，不另建 native clock/timing shadow。
- CUDA 内独立执行 clock slew/arrival、deferred sequential seed、data slew/arrival、endpoint required/backward。复用 device dynamicArc/table lookup，不调用 CPU reference 或 native propagation 替代 GPU 计算。
- 打包顺序 seed、选定 endpoint check 与原始表数据；共享机械字段编码，不共享 CPU 与 CUDA 的实际传播过程。新增数据必须纳入初始化、targeted append/patch、rollback、恢复、数值/边界校验及实际传输计量。
- 既有 clock/constraint/library/corner 绑定守卫继续使 clock state 复用有效。data-only 编辑可以改变 Q/data 的负载与 CTQ 延迟，每批在候选图中重新计算这些受影响结果；不把 Q 负载成本隐藏在诊断分支。
- GPU full 和 mixed 使用相同 propagation；full/mixed levelization 仍分别执行原有路径。保持 scalar/path winner、真实 Base∪Aux 访问、session/generation、fallback、poison 与失败原子性。

### 3. 支持判断、消费者与默认路径

- 在上述计算完成并获得针对性证据后，从 exportUnsupportedReasons 和公共 validator 的语义推导中移除已支持的六项拒绝。外部输入仍校验 raw role、clock owner、seed、table、容量与有限数值；其他 unsupported reason 保留。
- 同步 native typed capture、Dual-CSR payload/view、reference-input serializer/Python 解析、CUDA pack/unpack 及真实生产 trace consumer。必要引用重映包括 clock owner、seed 的 path_start/CRPR、check node 和新 append 节点；不另加运行时开关或公开 skip_validation。
- Release OFF 不执行完整 proof/oracle/fresh replay/诊断序列化；Release ON 执行独立证明。保留 native 只读构建状态；CUDA 增量初始化不伪造真实增量批次。

## 实施顺序与独立审查

1. 完成代码分析、详细计划、独立设计审查并修复 blocker。
2. 实现共享输入与 CPU reference 的 clock、sequential seed、endpoint check；运行 native 定向测试。
3. 接入 CUDA full、targeted/mixed candidate 和恢复；运行硬件定向测试。
4. 打通三设计四模式及真实多批 trace；发现差异先保留最小复现，再修正根因，不修改输入规避差异。
5. 由另一个未参与实现的独立 subagent 按 review-guidelines 审查完整 diff；修复、复查后完成回归和文档。

## 测试与成功标准

- 六类语义的定向 native fresh/full 对照：clock fanout 和 clock buffer physical state、CK/Q 起点、rising/falling CTQ、input/register 混合竞争与 winner、setup/hold/recovery/removal、带条件多 child max/min、缺表 fallback、CRPR 身份及 ideal-clock 校正。原生不支持语义保持 typed rejection，不测试“删除拒绝字符串”来证明能力。
- 保留 malformed input、stale generation、owner conflict、unsupported、cycle、数值失败、真实 rollback、按模式 recovery、恢复后继续提交；ON 故障注入。新增功能错误 canary 必须被实际差分捕获。
- 三设计均复用本次 CUDA CI 验证报告的原 mapped.v/SDC/ICS55 输入身份，不删除寄存器、不改约束、不抽取子电路。每个 OFF/ON + 四模式组合独立进程，baseline 重复两次比较公开 QOR/timing paths/execution；每个设计生成一个确定性、至少两批的 data-only buffer insertion trace。
- 每个 trace prefix 对独立 fresh native CPU/full，另对 CUDA/full；比较拓扑、完整适用 timing/clock/path/arc/winner、公开 QOR/timing paths 与实际模式，检查 level 合法性。CPU/CUDA incremental 每批实际执行请求策略且无静默 full；独立 OFF/ON 比较排除计时、诊断字段和 session 实例身份。
- 复用现有独立 Release OFF/ON、相同 GCC/CUDA/依赖，顺序构建和隔离共用 bin 的 binding，检查真实模块路径与只读状态。运行相关 strict native CTest、属性/生产 trace、parent 回归、修改文件 lint/type check 和两仓 diff check；全仓类型检查如仍失败如实记录。
- 正常 mixed/fallback 在 OFF/ON 下运行 memcheck/initcheck；故意设备错误单独记录。OFF 性能每样本仅目标 workload，保留加载/清理与原始样本，不启动 oracle/完整 receipt；ON 在采样前拒绝。剖析证明 CUDA 计算路径不调用 CPU timing shadow，OFF 不执行重型诊断。
- 性能结果不替代正确性，不预先承诺 speedup。全部要求取得当前证据并完成独立审查才标记 Stage 10 完成。

## 证据与交付

新建 stage10-progress-report.md，逐项记录六类支持、三设计四模式、真实批次、命令、原始日志、失败修复、审查与未完成项。同步总计划、开发检查规范和检查分类；保留既有历史记录。构建/运行脚本与原始大数据留在独立 build 证据目录，仓内只保留必要可复用测试及文档，不新增通用测试框架。

## 独立设计审查（2026-09-14）

审查者：独立 subagent `stage10_design_review`，只读审查未参与实现。结论 APPROVE，无 blocker。对照 native clock、sequential seed、TimingAnalyzer 和 DelayCalculator 确认范围及四模式验收完整。实现须保留首个匹配 timing check 的顺序；该 check 缺少当前 transition 时不继续寻找下一个，child table 候选不额外按 clock transition 过滤。


## 真实工艺输入补充设计审查（2026-09-14）

原单文件 trace 无法表达 H7CR/H7CL。独立设计审查 APPROVE：将真实 source refs 和测试 loader 改为有序 LEF/Liberty 列表，使用现有 StaAnalysisContext；frozen trace v2 编入所有文件顺序和 context。真实 JSON 必须完整指定 context，现有 synthetic recipe 保持单文件和原上下文。多文件 CLI 及 fresh replay 展开相同来源；共享机械 evidence 编码不共享 targeted/fresh 的计算。拒绝重复 canonical path，使用 ordinal+basename 避免同名文件证据冲突。Stage 5/6 和 OFF 性能输出 schema 不变。
