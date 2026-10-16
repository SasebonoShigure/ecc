# Stage 14.6：CUDA incremental 专项精简与评估基线收敛

日期：2026-10-16。基线：ECC `8f427efbe20831b3a1ae79f71533ee02585c4fa6`、ecc-tools `79e3106dff1e3d2a50595cbb990f46e79ecefd46`。

状态：实施中。首轮源码排查、计划与独立设计审查完成；已完成基线报告推迟及回传等待计量的相关回归；native 绑定及修复后的加载器、测量入口已通过相关独立构建与实际进程测试，并取得小用例调用剖析证据；百万单元首批诊断剖析完成，公共及物理模式迁移通过本批相关回归；剩余改造与完整验收仍未完成，验证状态见[实施记录](stage14.6-progress-report.md)，本阶段整体尚未验收。下文“已确认”指调用链已核实，不代表收益已经测得。Stage 14.5 原始样本不改写；Stage 13 遗留项、Stage 12/15 正式性能门未执行的事实保留。

## 1. 当前维护和评估范围

- 只继续维护 native CPU/full 与 CUDA/incremental。CPU/incremental、CUDA/full 独立模式退出新功能、常规回归与新性能矩阵；按消费者迁移删除其专有入口、编排、测试和状态，不为历史兼容保留计算分支。
- 这是停止维护独立模式，不是删除所有 CPU/full 算法：CPU mixed builder/Kahn 是 CUDA incremental 的功能步骤；GPU 完整分层/传播仍服务初始化、实际恢复及显式 fallback。默认 CPU/full、诊断默认 OFF 保持。
- 新性能对手为 native CPU/full、HeteroSTA、OpenTimer v2、**独立 OpenSTA**。OpenROAD+OpenSTA 结果不能改名冒充独立 OpenSTA。已有跨工具文档和实验保留各自身份，不覆盖其文件或活跃任务。
- CUDA incremental 的结果正确性只以独立 fresh native CPU/full 为黄金标准。外部工具需确认输入、实际编辑、完成边界与结果有效；跨工具数值/选择分歧单列，不拿外部结果放宽本项目容差。
- 本阶段允许按瓶颈改变结构、流程和算法，但每项改动须说明真实消费者与失败恢复。默认仍是增量图更新、mixed 分层、全图传播；不能顺手改为 affected-cone AT/RAT，不能靠删维度或改变 epsilon/winner 获得加速。

## 2. 已确认的问题与修改方向

下面的源码链接基于上述 native 提交。`N` 为 timing nodes，`E` 为实际边数，`L` 为层数，`P` 为全部有效路径 tag 槽数，不能将 N 当成标准单元数。

### A. CPU 已知的分层信息又从 GPU 回读（优先处理）

证据：[mixed 重建](../../chipcompiler/thirdparty/ecc-tools/src/operation/iSTA/source/module/timing_cuda/CudaMixedLevelization.cu) 的 `reconstructMixed()` 在 CPU 生成 offsets、新节点位置和旧层复制范围，然后上传 offsets。`CudaDualCsrSession::Impl::execute()` 不区分来源，又下载 `level_offset_count`、整份 `node_levels` 和 offsets，并等待两次。内部 [full Kahn](../../chipcompiler/thirdparty/ecc-tools/src/operation/iSTA/source/module/timing_cuda/CsrCudaLevelization.cu) 也在 host 累积 offsets 后上传，成功路径同样不需要再下载相同 offsets。

处理：CPU 计算出的 count/offsets 由 pending session 持有并提交；内部 full 初始化保留自己的已知 offsets。只回传设备实际产生且 CPU 必须消费的数据。设备 status、实际完成与错误处理仍保留，不能假造成功。CPU 数据生成成功不等于 GPU 重建成功。

### B. 全节点 node_to_level 重建只为 host 消费，而非传播 kernel 必需

证据：mixed kernel `reconstructNodeToLevel()` 对每个 GPU 节点二分找层、atomicCAS 写入层号；此前还清零整表。传播 kernel 实际读取 order 和层区间，不读取这张逆映射。逆映射回到 CPU 后被下一批 [mixed graph builder](../../chipcompiler/thirdparty/ecc-tools/src/operation/iSTA/source/module/timing_incremental_levelization/MixedLevelizationGraphBuilder.cpp) 及 `propagate()` 的时钟工作表使用。层号采用 **1-based**，0 是无层标志。

处理：先让 CPU 复用 mixed 已求得的旧层→新层关系、新节点归属，保证下一批映射和时钟调度正确，再删除 OFF 的 GPU 全节点逆映射重建与 D2H。优先维护稳定层归属和紧凑重映射，不建立无界 generation 链，也不把同量全表重建简单转到 CPU。ON 独立检查完整排列/逆映射和实际边序；显式完整 levels 查询按需物化。

当前 D2H 逆映射为每批 `8×N` bytes：两类百万单元用例约 20.0 MB/21.3 MB，再随新增节点增长。这是源码确定的传输量，不是耗时或可保证收益。原子去重目前还承担排列有效性检测；移除前要由受控构造和必要容量/覆盖检查保证正确写入，公开任意输入仍完整验证，不能仅把所有检查关掉。

### C. 临时上传对象制造的等待，和真实错误决策混在一起

证据：`reconstructMixed()` 开始回传 patch status 并等待；结束为局部 `new_nodes/offsets` 的存活而等待；返回 `execute()` 后又等待 status/count、levels 和最后 propagation status。普通成功路径存在五个显式 host 等待点（不含扩容、异常和 ON 额外工作），其中目的不同。

处理：把实际异步上传源放入既有持久 staging，直到必要完成点才复用。检查同 stream status 防护和异常释放顺序后合并没有 host 决策消费者的等待；patch 失败时不得先发布 host 状态，异步错误、撤销及 cleanup 仍须被观察。不能仅删除 synchronize，也不新建通用内存池。

### D. mixed 每批仍扫描全部 host arcs 并重建 roots 证明

证据：`reconstructMixed()` 创建 N 长度 `root_state`，遍历全部 `host->bindings`；builder 逐条检查 old→old 层序，收集新节点关系。异常时实际 DAG 分类另有全图遍历。这并非只访问新增节点。

处理：在受控编辑的已提交状态上维护必要的 eligible 入度/根状态与变化边关系；对未变化 old→old 关系复用已成立的层序，处理新/改边并构造 mixed 约束。删除边、并行边、eligibility 变化必须更新计数。实际 cycle、old-level-order conflict 与 fallback 分类保留；公共裸图入口和 ON 独立证明仍可全扫。不得无依据把原扫描改成 debug，否则会漏掉真正的拓扑变化。

### E. 路径可达身份局部更新后，仍整表重打包并上传

证据：[updatePathDomain](../../chipcompiler/thirdparty/ecc-tools/src/operation/iSTA/source/module/timing_cuda/CsrCudaPacking.cpp) 局部求 dirty 可达行，但最后遍历全部 N×8 行，把未变 tag 也复制到另一份紧凑 payload；[transferPatch](../../chipcompiler/thirdparty/ecc-tools/src/operation/iSTA/source/module/timing_cuda/CudaDualCsrTransfer.cu) 在 domain 切换时完整上传 offsets/tags。每次插节点都会进入这条路径，成本为 O(N+P)，不是只与本批编辑数相关。

处理：区分“新增行”“旧行身份未变”“旧行 tag 集合确实变化”，复用未变行的稳定存储，仅追加/替换实际改变的行；真实增长和必要整理单列成本。保留全部可达 tag 与删除最后一条路径后的失效，不截断维度；committed/work 隔离、rollback 与后续查询必须同时迁移。不因追求紧凑而每批重写整个域，也不引入通用分配器。

### F. 时钟工作表每轮清空、排序、上传

证据：[propagate](../../chipcompiler/thirdparty/ecc-tools/src/operation/iSTA/source/module/timing_cuda/CsrCudaPropagation.cu) 从 `node_seeds` 重建 `clock_work`，按 level/owner/node 排序后全量 H2D。固定时钟树的数据编辑通常不改变 clock owner/连接，但新层编号可能变化，不能仅靠“没有编辑时钟”就复用旧 level。

处理：保留稳定 clock/domain 工作分组；复用 B 的层映射更新必要区间。只有身份、时钟连通性或层调度实际变化才更新对应信息。时钟传播本身是否可复用须另证明负载、RC、输入 slew、CRPR 等失效边界，本轮不能用缓存旧 timing 掩盖必要计算。

### G. 查询类型不同，却共同触发大范围物化（需按消费者细化）

证据：[candidateTiming](../../chipcompiler/thirdparty/ecc-tools/src/operation/iSTA/source/module/timing_cuda/CudaBufferCandidateTiming.cu) 已避免完整 PathState，但仍收集并回传所有 N 节点；[PhysicalStaSessionState::read](../../chipcompiler/thirdparty/ecc-tools/src/operation/iSTA/interface/PhysicalStaSessionState.cpp) 即使 summary_only 也先调用 `timingValues()`；后者回传所有 node/path/arc/child 状态及 OFF order，再统一解包。已有同 generation 缓存，不能把它重复列为“缺少缓存”。

处理：候选查询先确定拓扑上合法的 data-net/sink 集合，再读取完整候选所需的值，不提前按旧 slack 淘汰可能的新赢家。固定 trace 不请求候选时不调用它。summary、有限 paths、完整 timing、SDF 分别追踪必要字段，只物化实际需求；完整 timing 与完整输出仍交付全部字段。此项已确认过量范围，具体可删 arc/child 字段须逐消费者证明后决定，不一刀切。

### H. 内部 patch 路径重复校验不可变模型

证据：[validatePatch](../../chipcompiler/thirdparty/ecc-tools/src/operation/iSTA/source/module/timing_cuda/CudaDualCsrPatch.cu) 对 payload expected/replacement 调 `validateTransfer()`；[validator](../../chipcompiler/thirdparty/ecc-tools/src/operation/iSTA/source/module/timing_csr/CsrReferenceNativeModelValidator.cpp) 遍历 child、验证表并排序检查 arc indices。这也发生在受控生成、共享不可变 Liberty owner 的更新链上。

处理：公共裸 patch 输入保留边界验证；受控生产链按模型 owner 生命周期复用已经通过的模型结构验证。每次 session/generation、高水位、局部实际旧值、负载/RC 新值、容量及设备冲突检查仍保留。先检查全部调用者再收敛到既有模块内部实现，不增加公开 skip_validation、验证 token 或第二套策略层。

### I. 初始化与比较基线有额外工作，必须一起纠正

证据：[ProductionFreshSessionLoader](../../chipcompiler/thirdparty/ecc-tools/src/operation/iSTA/test/timing_edit/oracle/ProductionFreshSessionLoader.cpp) 在 CPU/full baseline 后仍导出完整 CSR；[NativeFullEditPreparer::bindBaseline](../../chipcompiler/thirdparty/ecc-tools/src/operation/iSTA/source/data_manager/adapter/timing_edit/NativeFullEditPreparer.cpp) 依赖这个对象建立语义绑定。[runFullStaPipeline(false)](../../chipcompiler/thirdparty/ecc-tools/src/operation/iSTA/interface/StaProductionLifecycle.cpp) 仍调用完整 `analyze()`，而 timing-only CUDA baseline 不做报告准备。

处理：native CPU/full 从 native 语义建立必要编辑绑定，计时基线不导出仅服务 CSR/诊断的对象；把必要 RAT 与可推迟报告分开，默认一次性 CPU/full 产物行为保持兼容。CUDA 初始化仍需要 CPU 解析、结构图和 CSR 输入，不能把其 initial full GPU 计算误称为先跑一遍 native CPU/full。分别剖析解析、结构构图、CSR 导出/索引、设备初始化和初始计算，不用“准备”一个数覆盖全部。

十轮 CPU/full insertion/timing 已走 timing-only 分支、只在末轮报告，不重复实施这项已完成改造。旧 14.5 数据保留原口径；清理后必须另测，不能直接从旧样本减去估计耗时。

### J. 当前分项计时不能完整解释回传等待

证据：`execute()` 把 levels D2H 和中间等待记在 propagation 前，而 `d2h_ms` 只取 propagation 后 events 4→5；mixed 的 levelization_ms 从 event 7 开始，还可能包含 host 调度间隔。字节计数含该次 levels，但名为 D2H 的时间并不覆盖所有 D2H。初始化、候选和最终物化另有边界。

处理：用既有 telemetry 分清 level metadata、状态决策、候选、最终结果回传及必要 host 等待；保持实际连续 wall time 为总量，嵌套分项不重复相加。详细同步剖析放独立运行，不为了测量给 OFF 样本新增每层等待；不能用现有 d2h_ms 推断全部传输耗时。

### 既有 OFF 样本的传输证据

复核 Stage 14.5 final85 的两类设计各三份正式样本，取每份前九轮（尚未查询结果或生成报告）；同设计三个样本的字节记录一致。首轮插入 100 个 buffer 后的传输如下，MB 为十进制：

| 用例 | 实际 H2D | 其中整表 path offsets | 实际 D2H | 其中 node_to_level |
|---|---:|---:|---:|---:|
| wide_2500002 | 240.122 MB | 160.013 MB | 20.002 MB | 20.002 MB |
| multiclock_2666692 | 282.756 MB | 170.681 MB | 21.335 MB | 21.335 MB |

实际总字节来自原始 telemetry；字段分量根据已核对的 uint64 Index、N×8 路径行布局和当批节点数推导。前九轮中，逆映射占 D2H 的 99.999% 以上，单是 path offsets 就占 H2D 的 66.64%/60.37%，尚未包含整表 tags。首轮除逆映射外的 D2H 分别仅 156/124 bytes，说明无报告批次的回传主要服务当前层状态维护，而非 timing 报告。

证据保存在 `/home/shigure/code/stage14.6-audit-20261016/transfer-evidence-from-final85.json`，包含六份样本路径及原始哈希、54 个批次记录和推导值；未重采、未改变原始结果。这支持优先处理 B、E，**不等于已经节省这些时间或已经获得加速**；GPU 完成等待、host 重打包和总墙钟成本需在实施后另测。

## 3. 不应误删的工作

- full levelizer 仍用于 CUDA baseline/恢复/显式 fallback，且 CPU/full 仍独立完整构图传播；停止维护 CUDA/full 独立模式不等于删掉这些内部能力。
- 局部 undo、committed/work 结果、实际修改历史、异步上传源生命周期、设备错误与 poison 属于生产功能，不能全部塞进 ON。
- 默认仍全图传播；节点/路径结果重置、动态延迟/RC 计算、AT/RAT、slack 和 timing-check 不能随报告推迟。可优化写入量/布局，但须证明所有读到的值均已被本代覆盖。
- `Runtime::ensure()` 已复用容量并延迟退休旧 buffer，不能声称每批都分配整套设备图。扩容成本与普通批次分开计量；只为内部 full 使用的 scratch 可按需保留，不每批跟随节点增长扩容。
- baseline 大输入、公共任意 levels/patch、numeric/cycle、容量/局部旧值，以及恢复后的继续编辑仍要验证；独立诊断及其专用数据才放 ON。

## 4. 实施顺序与迁移落点

1. 冻结当前代码、输入、消费需求和调用/分配/传输基线，先修正 I、J 的公平计时边界；不修改原始样本。
2. 收敛维护路径。检查 `sta_mode.py`、`sta_session.py`、native `StaExecutionContract`、`IncrementalStaSession`、physical session、binding、baseline/fallback/recovery、probe/controllers、CTest/parent tests 和 CI。旧组合在最早公共边界明确拒绝；旧结果解码与历史文档可读，不能默默接受后执行别的模式。共享结构按现有消费者保留。
3. 联合处理 A–C：CPU 层状态、GPU 重建、上传生命周期与收尾等待；覆盖无需查询的连续批次和查询后继续编辑。
4. 按独立剖析依次处理 E、D、F、H；每组先过针对性回归，不把一次巨大重构作为前提。G 按候选、summary、paths、完整结果依次细化。
5. 接通新性能对手，完成独立代码审查、OFF/ON/无 CUDA、sanitizer、真实物理与百万合成用例；更新阶段报告、总计划、开发规范与检查分类。

不设置删行数、固定测试数量或源码字符串门禁。阶段验收要有实际运行证据，保留失败和负收益；本次计划修改不自动 commit/push。

## 5. 新性能矩阵与正确性验收

| 被测/对手 | 角色与执行要求 |
|---|---|
| CUDA incremental | 被优化路径；实际增量编辑、mixed、GPU 传播；无静默 fallback |
| native CPU/full | 性能基线；独立 fresh 路径另作为 correctness oracle，oracle 不进入性能子进程 |
| HeteroSTA | 固定官方交付版本和 binary，确认许可与拓扑编辑能力；若必须重建，记录 rebuild 并计入成本 |
| OpenTimer v2 | 固定源码/构建；lazy 编辑必须等实际 timing 完成，记录真实线程及支持的时钟/SDC 语义 |
| OpenSTA | 固定独立 OpenSTA 源码/构建；包含实际网络编辑及 arrivals/requireds/slack 更新，不代称 OpenROAD |

外部依据：[HeteroSTA 官方入门](https://heterosta.pkueda.org.cn/documentation/get-started)、[OpenTimer 官方仓库](https://github.com/OpenTimer/OpenTimer)、[OpenSTA 官方仓库](https://github.com/The-OpenROAD-Project/OpenSTA)。版本、能力与命令在实际接入时重新核验；本阶段首轮排查没有运行外部工具，也没有确认 HeteroSTA 授权。已有跨工具资料是线索，不代替固定版本的小样本预检。

- correctness：同一累计编辑由独立 fresh native CPU/full 重建；CUDA 每批比较 topology/RC、AT/RAT/slack/slew、winner/前驱、CRPR、timing-check、公开 QOR/paths 和 levels。保留 min/max、rise/fall、多 clock/tag 等有效维度；OFF/ON 等价在独立开发验收进行。
- 专项测试：深链/宽层、旧层编号整体变化、插入/删边失效、并行弧、重复 seed、空路径行、tag 域增长、RC/负载变化、连续不查询、中间及重复查询、容量增长、真实 rollback、事务放弃、poison、新 session 恢复后继续提交、报告失败重试。保留 xtea/usb/zipdiv 物理 Q/D trace，百万宽层/多时钟用于规模验证。
- 两套对比：fixed trace 验证同编辑量成本；closed-loop 每工具使用自身最新 timing 与共同选择规则，记录不同选择、轮数、buffer 数和结果，不强迫跨工具得到同一图。CUDA 自己实际选择的累计 edits 仍可交 fresh native CPU/full 验证。
- 输入和消费者在测量前冻结。语义不支持不删寄存器/时钟绕过；外部工具不支持时记 unsupported，不可用记 blocked/not_run。共同语义子集另起 workload，所有工具包括 ECC 重新测量。
- 所有工具只在末轮交付约定报告；每轮候选数据、真实完成等待、必要网表重建/转换/传输均计入。三段主表为插 buffer 前、插 buffer 到报告前、报告；清理和进程全程另列。写磁盘产物是否包含必须一致且明确。
- 正式工程默认 5/30，既有 1/3 和用户明确指定的短测量仅作参考。每个完整循环是一个样本；实际线程/affinity、GPU 占用、版本、原始样本和负结果保留。Stage 15 按冻结可比对象分别给出置信区间和收益结论，不再维持 CUDA/full 旧双加速门。
- 高内存工作共用 512 GB 硬上限、swap=0，使用现有 Docker、tmux、空闲非 0 GPU；不改驱动权限。大流经 FIFO，保留紧凑证据，不覆盖活跃源码/二进制或用户文件。

## 6. 本轮交付边界

计划编写时只新增阶段、更新维护/评估规则并完成上述源码排查，未修改源码与既有原始测量。后续实施按[阶段记录](stage14.6-progress-report.md)追踪；独立审查与运行验收仍是阶段完成的前置条件，不以计划或首批提交代替。
