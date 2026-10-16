# IncreGPUSTA 开发检查分类

状态：Stage 14.5 本轮优化及参考测量已完成，Stage 12 原严格高性能验收仍未完成。各节保留当时的分类与迁移状态；已被替换的实现以后续明确记录的工作区状态为准，未合入候选不能作为当前默认路径。以下保留 2026-09-08 冗余清理及后续阶段记录。当前结果见 [清理报告](stage0-6-redundancy-cleanup-report.md)，此前诊断分离结果与限制见 [实施报告](debug-checks-implementation-report.md) 和 [实测证据](debug-check-acceptance.json)。开发规则见 [development-guidelines.md](development-guidelines.md)。复杂度中的 N/E 为节点/边数，B 为累计批次数，D 为本批编辑规模。

| 调用链 / 数据 | 用途与复杂度 | 归属 |
|---|---|---|
| CsrSessionSnapshotAdapter 的实际 input、metadata、active/released 身份与状态 | 真正导出、scatter、失效和释放；O(N+E) 的功能成本 | 始终保留 |
| makeReadyObservation、prepared observation pair、Python observation mapping | 对已受控快照进行重复归约、序列化与深拷贝；O(N+E) | ON |
| 外部 reference/descriptor/level 输入校验、局部 expected value、session/generation/owner | 阻止输入错误、串会话、越界和错误提交；通常 O(D)，输入首次构造可 O(N+E) | 始终保留 |
| Stage 3 CsrExecutionAuthorization | 受控执行的 session/generation 授权；O(1) | 始终保留；完整证明另存可缺省 payload |
| Stage 3 proveCsrFullExact、coordinator rebuilt snapshot / CSR replay / native readback | 证明候选与 CPU/full 完整等价；O(N+E) 或更高 | ON；OFF 不生成 full-exact proof |
| ExpectedBeforeBinding graph/index | 描述符实际消费的受控前态，值所有权跨 candidate 生命周期；O(N+E) | 始终保留；resolver/identity 完整副本仅 ON，移除固定复制计数 API |
| DualCsrVerifiedStage / Recovery 的 expected aggregate | 重复全对象比对副本；O(N+E+B) | ON；OFF 使用 session/generation/committed identity 绑定 |
| telemetry.logical_edges_after | edge view 实际驱动 levelization 的活动边数量；维护和公共输入核对 O(E) | 始终保留；字段的历史命名不代表纯诊断 |
| 其余 updater 结构计数、容量事件、full-export/candidate/full-levelizer 访问计数 | 证明实现路径与计数恒等式 | ON |
| updater 的 detached staged graph、native rollback database | 原子发布、真实回滚必需的隔离副本 | 始终保留 |
| factory / coordinator / index stage | 最终受控 aggregate 全检 O(N+E+B) 归 factory；删 factory 分项和 publish 对同一 staged 的重复全检 | 完整证明仅 ON；公开入口及局部 descriptor/index delta 和发布条件始终保留 |
| execution_trace 的 generation、mode、恢复用 descriptor/semantic trace | 恢复需要按原模式重建每批 | 始终保留 |
| execution_trace 的完整 levels 与 mixed 审计字段 | 重复存储每批诊断结果；累计 O(B(N+E)) | ON |
| mixed builder actual_pairs、详细 arc/storage 访问计数、恒等式 | 区分 parallel 与 proxy alias 的诊断集合；O(E log E) / O(E) | ON；mapped_pairs、边界、indegree 和 cycle 分类始终保留 |
| narrow capture 的 typed node/arc/model records 与 coverage | 编辑描述符和有效载荷的真实输入 | 始终保留；coverage 检查实际容器，不依赖诊断计数 |
| narrow capture audit、全图 export 访问证明 | 证明走了局部读取路径；含 O(D) 额外计数 | ON；实际成功与审计成功分离 |
| mode recovery 的重新加载、逐批重建和 publish | 真正恢复操作 | 始终保留 |
| mode recovery 的整份 expected rebound aggregate、prefix/full equality | 恢复后的独立等价性证明 | ON |
| 性能 replay 的加载、candidate、baseline、rollback、原始时序 | 工作负载生命周期与实际结果 | 始终保留 |
| 性能 replay 的 observation / resource / exact receipt / source isolation / fresh oracle | 完整功能验收和路径证明 | ON 诊断入口；OFF 性能入口无这些输出或步骤 |

禁止按函数名称批量关闭校验。新增或发现混合职责时，先从所有调用者和数据消费者判断，再拆分必要状态与诊断。未采集的计数不代表已证明为零；默认输出明确 `correctness_comparison=not_run`。

2026-09-08 补充分类：旧 `DualCsrVerifiedRecovery` 无成功消费者，整条删除；恢复唯一使用按模式重放，最终 aggregate move 交付。恢复 evidence 仅 ON 可选输出，不参与授权。Full/mixed 自产 levels 各在 backend/pipeline 保留一次 ON 完整证明，外部 levels 与 replay seam 始终验证。Stage 6 删除同源双份 receipt 与绑定比较，值等价和 level 合法性直接消费同一 canonical 对象。旧 ON timing smoke 删除，已有 controller 保留独立诊断；OFF 性能 CLI 删除三项冗余构建参数。

## Stage 7 CUDA 补充

| 调用链 / 数据 | 用途与复杂度 | 归属 |
|---|---|---|
| CUDA build/device preflight、runtime status/sync、容量乘法、finite/cycle/view failure | 确保真实支持、内存及数值安全；O(1) 或算法内 O(N+E) | 始终保留 |
| full pack/seed initialization、完整 H2D/D2H、scatter 和 native candidate | Stage 7 full 的实际功能/隔离成本；O(N+E+表+path storage) | 始终保留；不得挪用为 Stage 8 targeted |
| 受控内部 scatter 的完整结果重复一致性检查 | 已验证计算结果的独立防错证明；O(N+E+paths) | ON；公开任意输入 scatter 始终验证 |
| GPU trace input/timing observations、完整 projection、fresh CPU 子进程、source isolation | 独立正确性诊断；每 prefix 额外完整执行/序列化 | ON；OFF 无 receipt，comparison=not_run |
| 实际 bytes、allocations、launches、device/build 信息和 event/e2e | 性能事实，不是路径等价证明 | 始终保留 |
| native 安装回滚、第二批失败后的真实恢复、session poison/close | 事务功能，不依赖比较模式 | 始终保留；恢复后的完整独立等价性证明仅 ON |

本轮结果和实际调用剖析见 [Stage 7 实施与验收报告](stage7-progress-report.md)。未执行的 OOM 场景和全仓类型检查不得记为通过。

## Stage 8 targeted CUDA 补充

| 调用链 / 数据 | 用途与复杂度 | 归属 |
|---|---|---|
| NativeTargetedEditPreparer 局部适用性、稳定 ID/rank、clock 身份 | 描述符与正确原状态绑定；O(D) 局部读取，加必要地址元数据维护 | 始终保留 |
| Database 隔离复制/library pointer 重绑、Arc canonical permutation/predecessor 重映 | 正确事务和 fresh winner/load 顺序；O(N+E+timing storage) copy，O(E log E) 排列 | 始终保留；不是诊断副本 |
| device detached candidate、D2D seeds reset、changed rows/payload H2D | 原子更新和避免上批结果污染初态；D2D O(N+E+timing storage)，H2D 为本批变更及 metadata | 始终保留 |
| patch incidence/重复写、actual slot expected、table/seed 域、容量、cycle/finite、CUDA error | 输入/适用性/内存及数值安全；O(D) 或融合到算法遍历 | 始终保留 |
| origin owner/session/generation、prepared scatter 和初始/上一代 rollback owner | 正确联合发布；发布只做 noexcept 写入与所有权转移 | 始终保留 |
| canonical export/device debugState、完整 timing projection、四 pass Aux visits | 逐批独立证明；O(N+E+table+timing storage) 额外复制/遍历 | ON |
| targeted/CUDA full/fresh CPU 每 prefix 子进程、source isolation、恢复完整比较 | 独立 oracle 与生命周期证明 | ON controller；OFF 只采目标 workload |
| test-only device friend readback / Aux omission、硬件故障隔离程序 | 开发验收；读取实际设备或显式错误实验 | 仅测试程序，不链接生产路径；硬件故障机制要求 ON |

当前边界、实测字节/调用、失败及修复见 [Stage 8 报告](stage8-progress-report.md)。初始化两次 export/pack 与逐批零全量调用分开记录，不能混为一个局部成本承诺。


## Stage 9 hybrid levelization 补充

| 调用链 / 数据 | 用途与复杂度 | 归属 |
|---|---|---|
| binding source/sink/eligibility/真实 BaseOut-AuxOut | canonical topology 的必要输入；patch 随实际 incidence 更新，mixed build 遍历 O(E) | 始终保留；无 payload/CPU CSR 影子 |
| 借用 PreviousLevels、维度/局部 level 范围、高水位/roots/indegree/processed count | 受控状态适用性及内存、cycle 安全；尺寸 O(1)，其余融合到必要算法扫描 | 始终保留 |
| 公共 arbitrary previous/graph/replay 校验 | 外部数据边界；O(N+E) | 始终保留；不公开 skip 参数 |
| 受控 previous 完整 permutation/inverse、mixed graph/result 完整 proof | 重复一致性证明；O(N+E) | ON；graph 归 builder，result 归 Kahn，不调用嵌套公共全检 |
| GPU offsets/old-block copy plan/new-node placements、D2D/H2D/node2level | 重建真实 levels；O(levels+mixed nodes) 计划，O(N) 设备操作 | 始终保留；OFF 无 previous 深拷贝或 CPU reconstruction |
| canonical CPU reconstruction oracle、GPU 全 levels/timing_order 比较、独立 eligible-edge precedence | 独立证明 GPU 重建与层合法性；O(N+E) | ON |
| actual DAG classifier、Error/full_with_record policy、失败 candidate 释放及重试 | 区分 cycle 与可恢复 old-order conflict；失败路径 O(N+E)，真实 full 重试另计 | 始终保留；默认不 fallback，不伪造执行结果 |
| CPU/GPU 各阶段时间、真实传输/分配/launch、请求/执行/propagation scope | 实际功能与性能事实 | 始终保留；GPU event 不包含 CPU mixed 等待时间 |
| 独立 full/fresh prefix oracle、完整 timing/winner/level/source isolation、恢复比较 | 正确性验收 | ON；OFF performance 仅实际目标样本，comparison=not_run |
| 实际断点/API 调用、分配生命周期和跨构建设备读回 | 开发验收证据，不参与提交授权 | 外部测试/剖析程序；不链接生产、无固定返回计数 API |

具体结果见 [Stage 9 报告](stage9-progress-report.md)。cuda/targeted-full-levelization 的历史 Stage 8 格式保留；Stage 9 incremental 使用独立 trace/verdict/performance schema，不修改 Stage 6 或默认 OFF 性能契约。


## 2026-09-14 corner fingerprint 修复

| 调用链 / 数据 | 用途与复杂度 | 归属 |
|---|---|---|
| Python/native analysis context 类型、非空、规范化校验 | 外部输入约束；O(context UTF-8 字节数) | 始终保留 |
| native 生产 reference corner identity | 状态绑定；O(context UTF-8 字节数) | 始终保留，编码及 schema 不变 |
| Python observation corner 对比、释放 observation | 重复验证 native 捕获生命周期；fingerprint O(context 字节数) | ON；对齐 reference-corner-payload，OFF 不采集 |
| direct/ASCII/UTF-8 生产 KAT、真实 binding baseline 捕获和关闭 | 跨语言契约验收 | 测试入口；不用通用 analysis-context KAT 替代 |

修复与实测见 [CPU 增量测试报告](cpu-incremental-test-report.md)。检查未被删除或降级；旧格式和其他 context 的 fingerprint 仍被拒绝。

## Stage 10 顺序逻辑与真实设计补充

| 调用链 / 数据 | 用途与复杂度 | 归属 |
|---|---|---|
| clock owners、physical/effective lanes、deferred CK/Q、CRPR、check/CTQ 原始表 | 实际计算和发布；随 N/E、table 与 timing/path storage 增长 | 始终保留；CPU/CUDA 独立传播，无 CPU timing shadow |
| Q net load、既有 CTQ payload 更新、D slew/check seed、局部 expected/边界/finite/cycle | 编辑后 timing 与原子提交；局部更新和必要传播遍历 | 始终保留，不以 debug 关闭功能重算 |
| 外部有序 LEF/Liberty、完整 context、严格 replay、来源身份 | 加载与适用性；O(输入大小)，文件身份读取随总字节数增长 | 始终保留；source isolation 独立证明仅 ON |
| canonical load/timing 全检、clock/CRPR/winner/level 比较、fresh prefix oracle 与 receipt | 独立证明；额外 O(N+E+table+timing storage) 或完整重放 | ON 诊断入口 |
| 显式跨构建设备 readback、临时 native 副本、scatter 后 public、恢复前后等价 | 验收 OFF/ON；整份状态复制、比较与报告成本 | 仅测试程序，不链接生产或普通性能入口 |
| 实际按模式重放、新 session 绑定、恢复后继续提交、rollback | 真实生命周期；成本随重放批次和工作量增长 | 始终保留；故障注入仅 ON，完整比较仅开发测试 |

结果和实际剖析见 [Stage 10 报告](stage10-progress-report.md)。测试输出拒绝覆盖已有路径；未执行 oracle 的性能输出继续记录 correctness_comparison=not_run。

## 2026-09-16 诊断内存清理

| 数据 / 检查 | 用途与复杂度 | 归属 |
|---|---|---|
| 文件顺序、角色、名称、路径、大小和 SHA-256 | 来源隔离；读取 O(文件字节数)，摘要工作缓冲固定 64 KiB，记录 O(文件数) | ON；替代完整字节与 hex 副本，保留输入核对和篡改检测 |
| SHA-256 的必要身份计算 | 身份值不变；直接处理完整块，最多复制 128 字节尾部 | 保持原调用归属，不改变开关或身份格式 |
| published_observations + transaction_receipt | 每批唯一 functional/structural；独立提交、回滚、跨 prefix 证明 | ON；删除同源 exact_receipt.published 副本，完整原生 validator 保留 |
| JSON 写出、来源视图、跨 prefix 局部对象 | 直接写流、浅层只读规范化、释放已完成比较的数据 | 诊断工具；不新增缓存或运行时选项 |

结果见 [内存清理与回归报告](memory-cleanup-20260916.md)。

## Stage 11 生产路径与存储

| 调用链 / 数据 | 用途与成本 | 当前归属 |
|---|---|---|
| CPU incremental baseline 的附加 capture/FIFO；旧 Stage 3 coordinator/authorization；整库 candidate/carrier | 无生产消费者或被实际事务替代 | 删除，不留 ON 兼容层 |
| 显式 snapshot observation、摘要、完整证明、fresh/native 对照 | 开发诊断，额外遍历/复制/序列化随 N/E/paths 增长 | 仅 ON；close 不补建未请求对象 |
| NativeEditTransaction、graph/index/resolver patch undo | 保存实际修改位置、旧长度与新增键；成本随实际编辑及受影响邻接增长 | OFF/ON；full 重建的旧派生状态通过 move 保留 |
| ExpectedBeforeBinding graph/index | descriptor 的必要输入 | 借用至 apply/扩容前；诊断比较副本仅 ON |
| 恢复编辑与实际 mode/generation | 真实恢复所需；每批追加一条，不复制历史前缀 | OFF/ON；独立恢复等价仅开发验收 |
| immutable Liberty/模型/table、实例 ChildState/load | 真实计算；未变模型按会话复用，新增模型/数组扩容如实计量 | OFF/ON |
| committed/work 结果、设备容量/stream/events/scratch、受影响 Aux 行 | 原子结果发布与实际计算；传播/重置仍可能为全图成本 | OFF/ON；无每批整图事务 D2D |
| sparse seed 与 N×8 紧凑 tag 域 | 全部有效路径身份；空行无 payload，结构域变化需重新压缩 | OFF/ON；不能截断 tag |
| status、levels offsets/inverse | 提交与下一批 mixed 的功能输入 | OFF/ON；完整 order 在 OFF 延迟至实际查询 |
| timing D2H、稳定 ID scatter、report 后处理 | 当前 generation 消费者结果；首次物化后缓存 | 按需；不得 CPU 重传播、返回陈旧结果或发布半份状态 |
| native CSR export 的完整 input contract | 外部方向/模型镜像、fallback arc 完整性、数值与身份约束 | OFF/ON；受控 export→CUDA 不重复全检，公共 CUDA 裸输入仍校验 |
| ON winner 入弧索引及延迟 SoA 检查 | 保留全部合法候选的独立证明；按图保序索引、数组结构一次校验，逐候选保留数值/lineage 检查 | 仅 ON 诊断 controller；targeted/fresh 分别验证 |
| fresh sample 加载、close/destroy | 工作负载生命周期 | OFF/ON；成功清理不等于最终回滚 |
| 真实分配/传输/阶段耗时与外部 profiler | 性能事实；提交、物化、报告和端到端分开 | OFF/ON；详细证明与正确性比较在 OFF 记 not_run |

实施和验收进度见 [Stage 11 报告](stage11-progress-report.md)。以上归属不构成性能验收通过。

## Stage 12 候选选择与验收

| 调用链 / 数据 | 用途与成本 | 归属 |
|---|---|---|
| 节点内极值及 epsilon 窗内局部身份选择 | 功能语义；遍历实际候选，不建立全图顺序表；CPU 临时候选仅单节点复用，CUDA 两次局部遍历 | OFF/ON |
| JSON 重复键、native capture 的局部索引和完整 key 核对 | 外部输入与编辑适用性；解析随输入大小，索引随本批请求及必要捕获范围 | OFF/ON；不靠关闭校验消除重复搜索 |
| structured capture 的弧覆盖、并行重数、完整电容请求与旧值 | 借用当批记录建索引，分组一次验证；committed capacitance 仍有一次全表遍历 | OFF/ON；保留缺失、重复、身份和字段策略拒绝，不以重复搜索充当证明 |
| targeted 弧的 parallel ordinal 投影 | 通过 native slot→stable ref 读取已有序号，序号查询 O(1)；其余 key 字段仍取当前图 | OFF/ON；当前 data-only edit 保持并行组，复用槽位先完成重绑，保留边界及身份检查 |
| 并发 status 归并、阶段依赖及唯一写入位置 | 并行实现必须保留的数值/内存安全和提交资格 | OFF/ON；并行改造尚未验收 |
| BaseOut/AuxOut/BaseIn 四阶段详细访问计数 | 证明实际遍历路径；CPU forward 改为两次入边访问，CUDA 诊断数组为 12 项 | 仅 ON；full trace/verdict v4、targeted/incremental v5，不用于提交授权 |
| 独立 native/full、完整 timing/winner/paths、层合法性及不同 launch 形状比较 | 功能及并发验收；保留全部候选与既有 tolerance | 开发验收；普通性能不运行 |
| 消费者样本与配对统计 | 提交至所需结果可用、加载与清理、实际线程和设备事实；完整 trace 为样本 | OFF 性能；正确性及详细诊断为 not_run |

实际失败、修复及剩余门槛见 [Stage 12 实施记录](stage12-progress-report.md)，不能将上述分类当作并行或性能验收结果。

独立 native oracle 的结果转换仅用于诊断验收。节点、弧及 tag 映射复用已有有序记录进行二分查找，保留完整 key 与 ID 范围检查；不参与 OFF 消费者路径，也不新增持久索引。

Descriptor replay 的追加弧邻接证明仅在 ON 验收使用。每个 descriptor 对 BaseOut/BaseIn/Aux 各扫描一次，保留所有出现位置和重数；不因期望端点已找到就跳过其他行。

Stage 12 诊断回放仅复制其实际修改的外层容器、节点 net_name 记录与 Base 槽位；嵌套 model/table/key 借用只读记录。成功与失败回放均校验原始输入不变，所有逐字段比较仍保留在 ON；此项不改变生产 OFF 的工作负载。

并行实现保留 OFF/ON 的原子错误归并、唯一写入位置、实际 undo 和 stream 生命周期。full Kahn 的前沿扫描/稳定压缩、clock/domain 工作列表、endpoint 数值最大值归约均为必要计算，显式 launch、CUB 执行及决策回传分别计量；详细访问计数仍仅 ON。不同 launch 配置的全值比较和完整设备读回只属于开发验收。

受控 native CSR 导出的末尾完整 contract 复查从 Stage 12 起仅 ON；它包含再次生成身份，以及现有 validator 按实例清零全图 pin 标记的 O(instances × N) 开销。构造过程继续在 OFF/ON 执行拓扑、方向、模型、数值和 clock owner 冲突检查；公开裸 CSR validator 不变。source identity 及分阶段失败指纹参与绑定和失效分类，仍保留。重叠时钟由已有 reachability 遍历即时拒绝，不增加第二次 replay。

### Stage 12 诊断比较器的 seed 查找

完整 root seed/winner 比较只属于 ON 开发验收。比较器按节点一次分组，列表保留重复项与全部 tag，继续执行原来的唯一匹配、数值和 CRPR 判定；不将二次扫描当作正确性要求。独立审查、行为 canary 和真实 receipt 调用剖析记录见 Stage 12 实施记录。

## Stage 13 RC 数学路径（接入中）

| 数据 / 检查 | 用途与成本 | 归属 |
|---|---|---|
| 根树、terminal、单位归一化后的非负有限 R/C | 外部边界；O(RC nodes + terminals) | OFF/ON |
| Arnoldi/DMP 结构归约、driver 实时求值、各 sink 波形 | 计算所需；原生固定模型阶数，sink 数不限；不能用 native 答案代替 | OFF/ON |
| 数值溢出、求值不可用、波形搜索不能完成 | 防止错误结果与设备长时间无响应；失败不发布 | OFF/ON；当前搜索上限限制见报告，不算完整 RC 验收 |
| 独立 native DCTask 对照、解析 RC、自有输出与不同 launch 形状比较 | 开发正确性证明 | 测试入口；完整 native 对照仅 ON |
| CUDA memcheck/initcheck/racecheck/synccheck、CPU sanitizer | 实际内存和并发检查 | 独立验收进程；不进入生产 |
| 按 clock owner 发布 physical/effective state、deferred launch、SDC clock 名单完整核对 | 实际传播和输入边界；沿已有节点/clock 遍历执行 | OFF/ON |
| full/局部 RC owner、native cell arc ordinal、pin/port 负载与阈值 | 实际求值输入；模型按 net 共享，修改后替换受影响 owner | OFF/ON；受控 pre-route 生产求值已接通，完整阶段验收另记 |
| 全局 input-port 阈值、CPU RC 初始化顺序及 net fallback | 必要求值输入与数值失败处理；阈值单份、仅 RC cell 临时分组 | OFF/ON；仅对完整准备的 pre-route tree 解除对应拒绝 |
| CUDA RC 结构打包、raw-load table 与 driver/load 求值 | 归约按 owner 共享、terminal payload 不乘 child/fanout；仅更新受影响 net | OFF/ON 功能；CPU 全值差分只在 ON 测试 |
| start seed 与 RC net 局部 expected/旧值/容量及撤销 | 事务功能；预留空间、保存实际变更位置 | OFF/ON |
| prepared RC tree 完整 terminal、N−1/连通性、有限单位与值 | 外部输入边界；仅受影响 net，O(nodes + edges + terminals) | OFF/ON |
| raw RC map node、局部 host binding 及设备 descriptor/buffer 撤销 | 实际事务隔离；只保存受影响对象，旧值只存一份 | OFF/ON |
| RC 事务的独立 fresh 导出、逐字段比较及逐分配失败扫查 | 验证完整性与异常安全；不产生生产提交授权 | 测试入口，完整差分与故障注入仅 ON |
| propagated Q/D prefix、winner/level、fresh/native 与非零 effective clock 证明 | 独立验收 | ON；不进入普通性能路径 |

已接通固定 propagated clock 和受控 pre-route RC；一般 SPEF、mesh、gating/divider 等范围外语义仍拒绝。完整物理/寄生/CRPR 阶段验收单独记录。详见 [Stage 13 报告](stage13-progress-report.md)。

### Stage 13：物理准备与撤销（实施中）

- OFF/ON：物理编辑的 owner、名称冲突、data-net/clock 边界、局部旧连接、容量和 DBU 范围校验；按受影响 net 构造连接引用与索引，保存真实旧值到共同提交完成。
- OFF/ON：物理对象、pin、shape 和 via 的异常安全所有权；准备失败回收、放弃撤销、提交转移所有权属于功能安全。
- 测试专用：完整连接/坐标比较、实际分配计数；ON 测试逐分配故障注入。生产不链接分配拦截器，也不执行全设计连接扫描。

### Stage 13：共同提交记录与恢复（接入中）

| 工作 | 用途与成本 | 归属 |
|---|---|---|
| checkpoint 文件 SHA、实际 IDB 几何及分析/RC 配置身份 | 初始化/恢复时一次，绑定实际输入；不逐批扫描 | OFF/ON |
| 本批编辑与坐标记录、独占锁、原子提交标记 | 实际故障恢复；成本随本批记录大小变化 | OFF/ON |
| 局部撤销、日志清理失败及设备 poison 传播 | 防止跨层状态分叉与旧结果泄漏 | OFF/ON |
| 逐条已提交记录重放 | 显式恢复操作，不重新写记录或复制历史前缀 | OFF/ON |
| marker 前后进程退出、文件描述符耗尽与输出失败测试 | 开发验收的真实错误注入，不增加生产运行期开关 | 测试程序 |
| 恢复/撤销后的完整 timing、QOR、paths 等价比较 | 独立开发验收，不进入普通生产提交 | 测试程序；生产诊断仅 ON |

当前共同 CPU/full 与恢复入口尚在运行验证，不能据此解除四模式生产 RC gate 或标记 Stage 13 完成。

- Stage 13 当前 generation 结果查询是生产消费者：必须在 OFF/ON 中检查 session/owner/generation，在受保护操作中按需物化 timing，再准备 QOR/paths；测试中的重复读取与独立数值对照属于开发验收，OFF 普通运行不执行独立 oracle。

### Stage 13：生产消费者与验收入口

| 工作 | 归属及成本 |
|---|---|
| greedy 当前结果、RC/Liberty gain 和局部冲突筛选 | OFF/ON 实际消费者；沿既有正 gain 规则，真实退化不触发新增收益回滚 |
| 当前 generation 的几何、power/timing/SDF/DEF/netlist 与 manifest | OFF/ON 产物消费者；完整生成后发布。routing/公开读取核对 generation、文件大小与分块摘要，不在每批提交生成产物 |
| TIMING_OPT 输出失败后的 journal 恢复与产物重试 | OFF/ON 功能；复用已完成 greedy 停止记录，不重复编辑。上游重新执行使旧 checkpoint 历史失效 |
| 物理 trace、独立 fresh native/full、完整 NeutralWire 和 canary | 仅开发验收；完整读回只在 ON 编译。OFF 执行真实批次但不运行完整 oracle |
| 启动/关闭、实际分配栈、传输和 CUDA sanitizer | 独立验收进程；不得把分配事件数解释为函数调用次数，不把剖析结果当性能统计 |

- Stage 13 的逐轮 QOR 摘要查询属于历史消费者路径；Stage 14 默认 greedy 改用紧凑候选输入及 commit generation。显式 QOR/完整查询仍是 OFF/ON 功能消费者，不属于诊断。


## Stage 14：直接编辑、候选读取与末轮产物

| 工作 | 用途、成本与归属 |
|---|---|
| stable key、局部旧连接/负载、generation、容量和数值检查 | OFF/ON；直接 CSR 准备的适用性及安全边界，真实 undo 保存旧值 |
| IDB/位置/RC 与 host/device CSR 的共同事务 | OFF/ON；按实际变更保留撤销和共享模型 owner，成功不撤销；必要 full 重建与全图传播另计 |
| 先编辑 native 图再捕获/转换的普通 CSR 批次路径 | 删除；不保留双份权威图，也不移入 ON 作为同源证明 |
| 紧凑候选 slack/slew/有效性与 RC/Liberty gain | OFF/ON；从所选 backend 当前结果取得，不生成 native 报告或完整路径 D2H；必要节点扫描如实计量 |
| native 拓扑视图、完整 timing/QOR/paths、power/SDF/DEF/netlist | 仅实际消费者请求时在 OFF/ON 执行；默认末轮一次，显式中间查询有效，同代缓存复用 |
| 报告临时修改的 path entry 撤销 | OFF/ON；只保存实际修改位置，成功和异常后恢复，保护下一轮候选输入 |
| 默认每轮仅服务日志的 QOR/WNS/TNS、路径分组与序列化 | 删除及其专用复制/遍历；未执行指标不填成功值 |
| 独立 fresh native、全值/winner/CRPR/level 比较与故障注入 | ON 开发验收；不参与普通 OFF 提交或性能采样 |
| 四模式完整循环计时及配对统计 | OFF 独立性能入口；包含最终物化与产物，正确性/诊断为 not_run；实际调用、分配、传输剖析另跑 |

Stage 14 已完成功能、路径剖析及用户调整后的参考成本验收；具体证据、负结果与限制见 [实施记录](stage14-progress-report.md)。

### Stage 14 受控基线复用

私有 native-export 构造只接受现有 session owner 的受控导出；session/generation、高水位、数组边界和下游 index/state 检查保留在 OFF/ON。重复 reference 指纹重算及刚构建 state 的独立完整证明仅 ON；公共裸输入 factory 仍完整验证。resolver 复用同一导出；batch index 撤销保存实际旧值并预分配，均为 OFF/ON 功能。

## 2026-10-10 百万单元优化补充

- 受控 native export 的 baseline/index 构造：OFF 保留 dense ID、resolver 唯一性、binding 覆盖、session/generation；ON 在索引完成后证明 aggregate 一次。公共裸 index factory 继续全检。
- sealed builder：OFF/ON 保留 schema、generation、高水位、局部旧值、容量、reference 和 index delta 适用性。邻接成员已在 physical delta 构造时证明；整图副本重演与全图 ArcKey 排序复验只在 ON。公共 descriptor validator 不变。
- 捕获排序键缓存与末轮借用 ArcKey：功能实现优化，OFF/ON 相同；借用仅限 query guard 生命周期，scatter 身份与 parallel ordinal 仍验证。
- 实际运行证据及尚未完成的百万门/完整验收见 [优化记录](million-cell-optimization-20261010.md)，不将未运行的诊断记录为通过。


### 百万单元加载与起终点构造

IO 名字匹配、连接更新和起终点判定属于 OFF/ON 都需要的功能。优化使用加载函数内的 IO 名字索引，并利用 pin map 的唯一性消除起终点列表的反复全量搜索；不将这些功能移入 debug，也不增加诊断开关或永久缓存。名字索引拥有 key，IO 指针仅在不增删 IO 的单次加载步骤内使用；重复构图保留已有条目及原顺序。验证进度见百万标准单元优化报告。

百万单元优化第七轮：断环的起点/终点成员判断是功能语义，OFF/ON 均保留。只将每次节点访问的线性查找改为本次断环调用内的只读集合查找，仍按既有顺序遍历和选择断环弧；集合不跨构图保留，不改变停止边界。

### 百万单元输入准备优化（2026-10-10）

Verilog 句柄追加、native net/load 首次出现去重和旧连接缓存清理均属于 OFF/ON 必需功能。局部索引替代重复扫描，不关闭输入校验，不改变借用 C view 或连接顺序；解析展开与重复连接行为由独立测试覆盖。加载剖析单列，不能计作传播收益。

无待推断 inout 时的预备 cell graph 没有消费者，直接删除，不移入 ON。最终图清空重建、必要方向推断和断环仍为 OFF/ON 功能；有 inout 时保留预备图。第九版行为与运行证据状态见优化报告。

Verilog 解析树释放属于 OFF/ON 都需要的生命周期功能。第十版由导入器独占 reader、reader 独占 parsed file，借用 view 不负责释放；重新加载失效旧 view。导入后的 IDB 独立拥有语义数据，不为诊断保留整份 AST；释放不放入 debug 分支。sanitizer 与大规模实际内存结果单独验收。

第十三版候选将末轮 native 视图的全图重建替换为共享局部图 patch。原始编辑、图 patch 和 timing 发布仍在受保护查询内完成，准备失败使用同一事务恢复；全图结果准备与身份检查仍保留。未查询的多个批次按最终连接构建新增弧，不通过重复传播补齐结果。该改动是 OFF/ON 功能实现，性能与完整正确性仍待验收。


第十四版百万单元优化将直接 CSR 负载准备与受影响邻接准备按本批 net/端点分组，减少重复扫描。它们是 OFF/ON 都需要的功能；局部借用仅在 records 不扩容、节点身份不修改的准备函数内有效。driver、RC 覆盖、sink membership、局部旧值和 canonical 弧顺序不变，不将必要负载计算移入 debug。零/非零电容的独立 native 对照及实际运行剖析分别验收语义和成本。


第十五版百万单元优化的邻接排序键缓存和末轮 ArcKey 哈希分组均属于 OFF/ON 的功能实现。键和目标只在受保护准备/查询中借用；排序 tuple 不变，哈希碰撞仍用完整 canonical key 判等，parallel ordinal、覆盖及回滚语义不变。临时容器成本计入真实运行，专用计数/细分计时仅在独立剖析对象中编译，不新增生产诊断接口。


第十六版百万单元优化把 direct CSR 不消费的 node role / cell capacitance 捕获请求及其生成、映射复制移入 ON，保留独立 native capture 验证。OFF 恢复测试复用现有 graph-only 视图和 direct CSR，不再依赖诊断请求；真正的节点/弧/负载数据及 session/generation、局部旧值、事务和恢复仍在 OFF/ON 执行。新增实际运行成本与恢复结果证据见优化记录，完整回归状态按新版本单独记录。


## Stage 14.5：分类调查中（2026-10-11）

以下为处理归属，未完成的迁移不能记为 OFF 已删除；实现与调用证据在阶段报告逐项关闭。

| 路径 | 归属与成本 |
|---|---|
| 当前结果寻址、stable Arc ID到实际目标位置映射 | OFF/ON功能；改进表示与维护方式，不能直接删除或盲用旧槽位 |
| 受控视图完整pin owner、节点身份、Liberty/ArcKey再证明 | 追踪构造流程后移入ON；目前全图遍历与签名构造仍在OFF，不宣称已移除 |
| 相同canonical状态反复验证、无消费者快照、同源比较 | 删除；有独立价值的证明及专用复制/序列化才保留ON |
| 外部输入、实际容量/数值/设备失败、提交绑定、撤销和恢复 | OFF/ON功能；不因假设内部恶意调用而重复全图检查 |
| timing/QOR/paths及最终产物 | 按实际请求执行；可改变内部表示，不能减少需求或移出计时 |

不为受控状态增加验证token或公开skip-validation。独立oracle与默认生产路径分开，详见[Stage14.5计划](stage14.5-detailed-plan.md)。

隔离候选20正在验证：受控native视图的完整身份重证明仅ON，OFF保留本次查询的实际目标寻址与原子发布。报告重复旁路及其专用撤销链直接删除；旧链proof只属于独立验收二进制。完整路径、CRPR、时序检查及实际报告失败重试仍是功能。候选尚未合入，生产19的迁移状态不变。

### Stage14.5 直接CSR稀疏准备候选（未合入）

直接编辑只借用已提交弧payload，持有真实变化记录；正常OFF不构造native捕获计划。显式native捕获仍按需构造计划，ON保留所选状态证明；同源重建计划再比较的重复证明删除。descriptor/index适用性、会话绑定、局部旧值、RC/load语义和实际undo保留。候选21-r1的RC记录次序修正已通过OFF/ON/无CUDA选定回归；运行拦截确认正常OFF不生成完整capture plan，显式native/ON仍生成。普通二进制24次诊断成本对照通过公开结果核验，百万单元十批验收尚未运行；生产尚未采用。


### Stage14.5 按需路径展开候选（未合入）

端点/tag的required、slack、时序检查、完整QOR和报告排名仍是OFF/ON功能。路径点、弧信息和cell/net delay在对应报告、SDF或完整诊断真正读取时按需构造，同generation复用；不属于仅ON诊断。完整oracle的全部路径序列化仍显式展开，普通结果需求不缩减。构造失败不得发布部分路径；实际消费者耗时包括推迟的工作。候选22全新构建验证中，不能据代码宣称性能改善。

### Stage 14.5：2026-10-12 工作区迁移状态

以下是 2026-10-12 当时的迁移状态：已采用69组合、71诊断修复及72末轮报告优化，验收尚在进行。最终工作区状态见后续 2026-10-14 记录。

| 工作 | 当前归属 |
|---|---|
| 不可变Liberty模型的内容摘要复用及指纹版本2 | OFF/ON必要输入绑定；同次导出按不可变owner复用，指纹仍覆盖内容及可变字段 |
| native oracle并行弧序号生成 | 开发验证工具；按完整语义键计数替代平方扫描，保留独立native计算及全部比较字段，不进入普通OFF性能流程 |
| 报告候选的check弧与捕获时刻复用 | OFF/ON实际报告消费者；仅在一次端点选择内复用，不增设持久缓存。逐候选slew、CRPR和required计算保留；报告仅在消费者请求时运行 |

### Stage 14.5：最终采用状态（2026-10-14）

工作区采用 85 版；前文未合入、待验收等描述保留各轮历史，不代表当前状态。

| 工作 | 用途、复杂度与最终归属 |
|---|---|
| CSR 数值与 timing/QOR/paths | OFF/ON 实际消费者直接读取权威结果，按需展开路径；删除普通报告前的完整 native timing scatter。SDF 等确需 native 对象的消费者仍按需物化，成本计入最终消费 |
| 直接 CSR 稀疏准备及负载/邻接分组 | OFF/ON 保留实际变更、RC/load 和局部旧值；删除普通批次的 native capture plan、无消费者副本和同源重建比较。高扇出实际依赖扫描仍计量，不宣称只与编辑数成正比 |
| 基线身份与 ExpectedBeforeBinding | OFF 将基线所需内容移入唯一 owner，取消仅用于诊断的第二份完整身份；ON 保留独立诊断身份。session/generation、高水位、局部适用性、真实撤销和恢复均保留 |
| 图导出到 reference 的节点索引 | OFF/ON 直接转移既有索引所有权，取消 O(N) 重建和逐项分配；公共导出的输入检查及 ON 构造后完整证明保留 |
| cell Arc fallback 索引 | OFF/ON 仅为缺少 Liberty 弧的 owner 建索引；必要实例检查仍执行，有 fallback 时仍扫描弧。不构造普通实例无消费者的索引 |
| 私有 reference 导出的 Arc 身份再证明 | 删除；graph producer 已绑定 native rank，受控流程内未发生编辑。公共输入边界及独立 ON 图证明仍保留，不增加验证 token 或公开跳过选项 |
| IO、Liberty 表达式、units、cell master 的释放 | OFF/ON 生命周期功能；由实际 owner 释放，move 转移所有权，fixture 借用。不能放入 ON，也不长期保留对象掩盖悬挂引用 |
| 独立 native oracle、完整 graph/timing、level 与 canary | 独立 ON 验收；百万单元完整输出经有界 FIFO 比较，保存紧凑结果。普通 OFF 计时进程不启动 oracle |

实际调用、分配及传输剖析与最终采用版本的回归、1/3 测量见[实施记录](stage14.5-progress-report.md)。索引与基线复制减少有实际分配栈证据；未采用的 75/76/78 不计为默认路径收益。原始 Logger ODR、全仓严格编译/类型检查失败仍保留。

## Stage 14.6：待实施的分层与传输精简分类

2026-10-16 首轮源码排查完成。首批 timing-only CPU 基线报告推迟已通过相关 OFF/ON/无 CUDA 回归；J 回传计量改造已通过 OFF/ON/无 CUDA 构建及相关回归、OFF memcheck/initcheck，其余下面仍列目标归属。实际验证状态见[实施记录](stage14.6-progress-report.md)。当前实现依据与消费者见 [详细计划](stage14.6-detailed-plan.md)。本节 L/P/C 分别表示层数、路径 tag 槽数和时钟工作节点数。停止维护 CPU/incremental、CUDA/full 独立模式，保留 CUDA incremental 实际依赖的 CPU mixed 与内部 full 初始化/恢复/fallback。

| 数据或工作 | 当前成本/消费者 | 目标归属 |
|---|---|---|
| CPU 已生成的 level offsets/count 回读 | 重复 H2D→D2H 和等待；host 调度仍需 offsets | 删除回读，复用 pending CPU 状态；真实 device status 保留 |
| mixed GPU 全节点逆映射及 D2H | O(N log L) 重建、O(N) 传输；下一批 CPU mixed 与 clock_work 仍读取 | 先维护 CPU 紧凑层映射再移除；独立完整排列/逆映射证明仅 ON，显式完整查询按需物化 |
| 临时上传源保护的同步 | 为保证对象存活，不是数值检查 | 延长既有 staging 生命周期后合并；实际提交、失败和释放等待保留 |
| 全图 old→old 层序及 roots 扫描 | O(N+E)，部分变化有真实功能意义 | 受控路径维护变化关系及入度；真实 cycle/冲突始终处理，额外完整证明 ON |
| 路径域重打包、时钟工作表重排/上传 | 未变数据也重复复制，分别 O(N+P)、O(C log C) | 维护真实失效范围；不减少有效 tag、clock 或必要 propagation |
| 不可变模型 repeated validateTransfer | 相同 owner 的 child/table 重证 | 输入首次/外部裸数据保留，受控 owner 内复用；局部 expected/新值始终检查 |
| 候选及 summary 查询 | 全节点候选 D2H；summary 也经完整 timing 物化 | 真实候选集合/查询需求决定回传范围；不使用陈旧值、不漏赢家 |
| CPU/full benchmark 附加 CSR、初始报告准备 | 共同 harness 和旧 lifecycle 的额外开销 | 从 native 语义直接绑定；必要 RAT 保留，完整报告末轮；独立诊断导出 ON |
| D2H 分类及既有 Runtime 等待计量 | 每次已有同步 O(1) 计数与两次主机时钟读取；无新同步、事件或全图扫描 | OFF/ON 性能事实；字节/等待恒等式核对属于测试。撤销等待保留到 owner，close 及失败整段成本另计 |

必要工作不能仅因昂贵归为 ON；ON 也不保留无独立价值的重复证明。复杂度和传输量来自源码分析，收益与归属落实须经过运行剖析、CPU/full oracle、OFF/ON 和实际恢复验证。

本批 native 绑定直接读取节点/net 与已传播 clock-point，保留必要所有权及 clock 编辑限制。恢复身份属于 OFF/ON 功能：扫描 native 输入连接与约束，并按唯一已用 cell 编码模型及全局端口阈值；删除此前为了该身份而导出的整份 CSR。文件摘要、IDB 几何、RC 参数、实际恢复与失败处理保留。该改造已通过相关 OFF/ON/无 CUDA 回归；timing workload loader 与紧凑测量入口已通过独立 OFF/ON/无 CUDA 构建及相关实际进程复验，小用例调用剖析确认 native 路径没有 CSR 导出；百万规模证据仍待补齐。紧凑输入的源文件/规模/批次规则属于外部输入边界，OFF/ON 均保留；native 性能流程不生成仅供 CSR 身份绑定的对象。末轮实际消费者继续完整读取约定结果，中间未运行报告记为 null；独立 oracle 不进入 OFF 子进程。


### Stage 14.6：两模式生产边界

公共模式组合校验属于 OFF/ON 输入边界，在绑定和设备访问前执行。CPU/full 的显式快照及 reference/scatter 仍仅 ON 构造，不因保留诊断而恢复 CPU incremental 生产 owner。独立 CUDA/full 重放与其同源比较删除，逐 prefix fresh native CPU/full oracle 保留在 ON；实际回滚、恢复、共同提交、poison 及 CUDA full 初始化/fallback 仍为必要功能。历史四模式记录只读解码，不授权执行旧模式。
