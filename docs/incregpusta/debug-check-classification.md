# Stage 0–12 开发检查分类

状态：Stage 11 已提交；Stage 12 本轮实现与参考测量已收尾，原严格高性能验收未完成。下表及 Stage 7–10 小节保留历史分类；被替换实现以末尾 Stage 11–12 分类为准。以下保留 2026-09-08 冗余清理及后续阶段记录。当前结果见 [清理报告](stage0-6-redundancy-cleanup-report.md)，此前诊断分离结果与限制见 [实施报告](debug-checks-implementation-report.md) 和 [实测证据](debug-check-acceptance.json)。开发规则见 [development-guidelines.md](development-guidelines.md)。复杂度中的 N/E 为节点/边数，B 为累计批次数，D 为本批编辑规模。

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
