# IncreGPUSTA 开发检查规范

适用范围：Stage 0 起的 IncreGPUSTA 实现与后续开发。此文件由总实施计划要求在改动前阅读，不修改仓库通用 README。

## 构建与运行

`ECC_INCREGPUSTA_DEBUG_CHECKS` 默认 OFF，独立于 CMake Debug/Release。使用 `-DECC_INCREGPUSTA_DEBUG_CHECKS=ON` 开启开发诊断；Release + ON 仍执行诊断，不依赖 NDEBUG 或 assert。

native 库、binding、probe 共用生成的构建配置。Python 只读取 native 的 `incregpusta_debug_checks_enabled`，不提供运行期开关或环境变量。

## 必须区分的检查

始终保留外部输入解析与范围、session/generation/owner、算法必需的容量/数值/cycle、unsupported/fallback、事务原子提交、真实回滚与恢复。状态更新、必要快照/索引和恢复所需编辑记录不能放入诊断分支。

仅 ON 执行完整图/索引证明、独立 oracle、验证性第二次传播/重建、完整对象比较、诊断快照/摘要、详细访问计数与恒等式、故障注入。ON 不是保留冗余的理由：同一受控对象的同一不变量只在明确的归属点验证，不增加同源格式之间的等价性证明。关闭时必须同时消除仅为诊断准备的数据与序列化。未运行的验证记录为 not_run，禁止伪造 PASS 或完整验证凭证。

不能按函数名批量关闭：逐个沿调用链区分外部输入、内部已受控状态以及纯诊断消费者。混合函数必须拆开必要检查与诊断工作。编译开关使用作用域清楚的常量条件或预处理块，不设计通用策略框架。

## 测试与性能

OFF 保留正常功能与必要失败回归；ON 运行完整 oracle/fresh replay/逐字段比较和故障注入。在独立开发验收中比较两套构建相同输入的功能结果。

正式性能入口只接受 OFF；不启动 oracle、不生成完整 receipt、不比较 source isolation。保留预热、原始样本、实际结果、构建状态、requested/executed mode 和 fallback。初始加载与正常清理是功能生命周期，不能省略。ON 下性能入口必须在采样前拒绝。性能记录明确 correctness comparison=not_run，不把性能成功写成正确性证明。

每次变更更新检查分类和实现报告，记录实际命令、失败及修复。使用功能测试和代表性调用剖析验证诊断路径，不建立源码字符串、对象清单、固定测试数量门禁。不升级依赖或修改其他项目算法。

## 清理后的检查归属与诊断入口

Factory 在构造只读 verified stage 前执行最终 ON aggregate proof；publish 负责绑定、generation、poison 状态及原子交换。完整 levels proof 在生成路径执行一次：full 位于 backend；mixed 的受控 graph proof 位于 builder，result proof 位于 Kahn，最终 levels proof 位于重建边界。公共任意输入、外部 levels、测试注入 replay 仍完整验证；updater/index 的局部适用性与越界检查保留，不能用公共 skip-validation 参数绕过。

恢复只使用按已保存模式重放的路径。恢复结果转移所有权，不在发布前复制整份已完成状态；诊断 evidence 仅 ON 返回，不构成授权。预编辑 binding 在独占准备阶段借用实际 graph/index，必须在 apply/扩容前消费完毕；resolver/identity 的比较副本仅 ON 存在。不要为证明复制次数增加返回固定值的 API。

ON 使用现有 `dual_csr_trace_controller.py` 或 `incremental_levelization_controller.py`，以 `--probe <ON probe> --trace <trace> --run-root <existing directory> --timeout-seconds 900` 保存独立 targeted/fresh 结果和日志。旧诊断 timing smoke 已删除；重复性能采样使用 OFF smoke，构建信息只从 native `build-info` 获取。

Stage 6 每批只输出一份 canonical graph/timing，process 为 `ista-stage6-trace-process/5.0.0`，verdict 为 `ista-stage6-differential-verdict/4.0.0`。值等价与 level 合法性读取同一对象；它们证明不同性质，应同时保留。共享 JSON 编码不得变成共享 oracle 计算。

## Stage 7 CUDA 路径

`ISTA_ENABLE_CUDA` 默认 OFF；启用 CUDA 不自动开启诊断。native 只读 `incregpusta_cuda_enabled` 与 `incregpusta_debug_checks_enabled` 是 Python preflight 和 probe 的构建事实来源。缺设备、unsupported 分析、数值/cycle/capacity、CUDA status/sync、owner/session/generation、真实 rollback 和 cleanup 始终检查。受控 scatter 可复用已验证计算结果，外部任意结果继续完整验证。

ON 使用 `baseline/run_cuda_baseline.py` 和 `timing_dual_csr/cuda_full_trace_controller.py` 独立 fresh CPU 对照；正式 OFF controller 只运行目标 workload，不能生成 full receipt。原始 H2D/D2H/D2D bytes、分配、launch 和同步耗时属于性能事实，始终保存。详细观察/逐字段比较/source isolation 仅 ON。每轮必须防止旧输出伪装当前成功。

Stage 7 的每批完整导出和事务复制是历史实现成本。Stage 11 起 full 仍完整重建/分层/传播，但复用模型与容量；targeted 使用局部撤销，不保留每批整图 D2D 隔离副本。GPU 计时报告写明实际并行度和同步区间，不能将串行 kernel 正确性等同于加速。

## Stage 8 targeted CUDA 路径

生产 frozen trace 使用 `cuda/targeted-full-levelization`，每批仅生成 native 局部 patch，设备维护 Base∪Aux 并完成 full GPU levelization/propagation。该 Stage 8 策略不同于下面 Stage 9 的 `cuda/incremental`，不得混写 actual strategy。

每批 session/generation、高水位、incidence/重复写、局部 expected、typed table/seed 边界、cycle/数值和 CUDA 状态必须检查。Stage 8 的整库/设备图副本和全局 Arc 重排已由 Stage 11 的局部撤销、稳定槽位和受影响邻接更新替代；真实 rollback 始终保留。每批不得调用完整 GraphBuilder、CSR export/pack、CPU updater/timing/FIFO。

独立 native canonical export、实际 device readback/详细 Aux visits、完整 timing projection、逐 prefix targeted 对 CUDA/full 和 fresh CPU/full、恢复等价证明只在 ON controller。跨构建实际值验收可由单独测试程序通过具体 friend 读回设备；实现不得链接到生产 runtime，不改变 OFF 的 debugState 拒绝行为，也不增加运行期开关。

加载阶段先经过 Stage 7 baseline 生命周期，再建立持久 device session。加载成本计入端到端 process_ms；不得重复建立 baseline 设备状态。`initialization.scope=persistent_device_session_only` 不代表整个加载。每批 telemetry 的 malloc/transfer/launch 必须对应真实 API 调用，详细访问证明不能成为提交授权。


## Stage 9 hybrid CUDA incremental

`cuda/incremental` frozen trace 每批复用 canonical CPU mixed builder/Kahn，随后用旧 level D2D、新节点一次批量 H2D 和 GPU node2level 重建，再执行全图 GPU forward/backward propagation。endpoint binding 必须维护真实 levelization eligibility 和 BaseOut/AuxOut 归属；禁止构造假 payload 或另存 CPU Dual-CSR/timing shadow。

内部上一代 levels 以引用借用；OFF 保留维度、范围、高水位、generation、roots、indegree、processed count、cycle 和 CUDA status 检查。受控 mixed graph 完整 proof 仅 builder 的 ON 位置负责，Kahn 仅证明自己生成的 result，不嵌套公共 graph validator。外部 previous/graph/replay 输入仍完整校验。ON 的 CPU reconstruction oracle 与独立 level 不变量检查不能移入正常性能路径。

GPU reconstruction 计时必须从 CPU build/Kahn/plan 完成后开始，报告 CPU build、Kahn、plan、GPU reconstruction、update、propagation、scatter、batch/process total。完整传播仍是功能成本；历史串行 kernel 的正确性证据不能替代 Stage 12 并行实现及性能验收。

仅真实 old-level order conflict 支持显式 `full_with_record`。重试前完成失败批次的局部撤销并释放 pending，再针对同一健康 owner 执行 full；actual cycle、数值/容量及 CUDA 错误不得伪装 fallback 成功。详细 rejected attempt 只记录已实际发生的失败，默认 Error 拒绝后仍须允许健康批次。损坏 CUDA context 不复用，恢复验收在新的健康进程按实际 mixed 模式重放。

ON 使用 `cuda_targeted_trace_controller.py --strategy incremental` 保留逐 prefix 独立 CPU/full、CUDA/full、level 合法性、winner/source isolation 和恢复等价；OFF 同一入口加 `--performance`，先核验真实 build-info，再仅执行目标 workload。批次数必须绑定请求 trace，generation 连续；不能相信子进程自己缩减后的 prefix。通用 Python session 的未编辑初始化如实记录 baseline_only/full；通用 physical/greedy 集成仍属 Stage 13。

验收 Python binding 必须检查实际只读 CUDA/debug 构建状态。当前 ecc_py 链接到共用 bin，多个构建的链接和测试应顺序执行，分别保存并选择对应构建产物；不能因 Python 导入成功就认定来自指定 ON/OFF 配置。CUDA 启用构建的无设备拒绝在独立 `CUDA_VISIBLE_DEVICES=-1` 进程验证；默认 CUDA 关闭构建另做回归。


## Python/native fingerprint 契约

corner fingerprint 的生产定义为 `makeReferenceCornerFingerprint()` 的 `reference-corner-payload`（含 empty marker）再包装 `corner-fingerprint`；通用 `canonicalAnalysisContextBytes()` 编码仅表示 context，本身不是生产 corner payload。两端测试须覆盖生产 identity 构造和真实 binding 快照的捕获/释放，不能只比较通用 helper 的已知答案或由待测 Python 函数生成的 mock。

修改编码必须核对 domain/schema、标记、字节长度和 UTF-8；必要 context 校验及 native 身份绑定始终保留。Python snapshot observation 的额外匹配仅 ON，OFF 不因修复而采集诊断。此次修复保持 native schema/identity 值不变，不接受旧的错误 Python 指纹。

## Stage 10 顺序逻辑与真实设计

clock、CTQ、timing-check 原始表、physical/effective clock、CRPR 身份及每批 Q 负载更新属于功能数据；owner/session/generation、有限数值、容量、cycle 和回滚检查始终执行。沿用 ideal-clock contract 与 native 条件候选选择，不将 propagated clock 或条件表达式求值推断为已支持。

真实输入保留有序 LEF/Liberty 列表和完整 analysis context，frozen trace 使用 v2；严格 --replay 只读取实际编辑，生成 trace 成功不等于增量验收。分别验证 Q 负载和 D 输入编辑，每批对独立 fresh native CPU/full；初始化单列 baseline_only。

公开结果来自实际 committed timing 的 scatter，清除旧 path groups 后调用 analyzePropagatedTiming，不得重新 native propagation 掩盖差异。跨构建 readback、临时 native 副本、public 与恢复等价仅链接显式测试程序，可验证 OFF/ON；生产重型诊断仍仅 ON，普通性能入口拒绝 ON、不启动 oracle。

恢复记录区分重放批次和后续新批次。CUDA 新 session 重建不等于原地修复故障 context；测试命名不得暗示存在未实现的生产恢复接口。验收结果见 [Stage 10 报告](stage10-progress-report.md)。

## 诊断数据的内存边界

来源隔离记录文件顺序、角色、名称、路径、大小和分块 SHA-256；不内嵌工艺文件字节或十六进制。保留前后比较、输入内容核对和篡改测试，原始文件作为独立证据。摘要读取失败、短读和大小变化必须报错。

Stage 5/6 的每批 functional/structural 只由 published_observations 持有，transaction_receipt 单独保存提交与回滚证明。该内存清理当时采用 Stage 5 process v2、Stage 6 process v3、Stage 4 source-bearing probe v2。Stage 11 再迁移为 Stage 5 process v4、Stage 6 process v5、Stage 4 source-bearing probe v3；消费者同步更新，不保留旧格式包装。生产身份保持不变，OFF 性能格式随生命周期/计时契约升级。

大 JSON 直接写入输出流；来源规范化使用只读浅层视图。跨 prefix 只保留后续完整比较实际需要的 observations，及时释放已比较的 fresh、transaction 和来源对象。独立 oracle、事务隔离与真实恢复数据不能因节省内存而删除。

## Stage 11 存储、事务与按需结果

- 会话稳定拥有 Database/Liberty、graph/index/resolver 和 CUDA Runtime。模型只构造/上传一次；实例 load 与 timing 独立更新，容量不足才扩容相关数组。
- prepare 先预留容量、局部旧值和本批恢复记录，再 apply/backend；commit 只做无抛出的交换、单条历史追加、generation 推进和缓存失效。放弃也必须撤销；成功提交不得自动回滚。
- CPU incremental 不附加 native full 或 baseline CSR/FIFO。ON observation 只在显式读取时构造并按 generation 缓存；未请求就 close 不补建。
- 默认提交仅回传必要状态与 mixed 所需 offsets/inverse；完整节点排列和 timing 随消费者查询物化。同 generation 复用，新提交失效，pending/poison 拒绝查询。报告用 analyzePropagatedTiming，失败不得发布半份结果或退回旧报告。
- 原生 CSR 导出在构造时保留 native/Liberty 方向、fallback arc 覆盖、clock owner 冲突及数值边界；对刚生成对象再次执行完整 contract 证明仅 ON。必要 source identity 与失败阶段指纹保留。直接受控 export→CUDA 调用复用构造结果；公开裸 input/levels 入口仍完整校验，不添加公开 skip 标志。
- 路径保留 N×8 逻辑行和全部结构可达 tag；空行无 payload。域重排、必要全图传播、levels、工作区重置与扩容分别计量，不声称所有成本只随增量增长。
- 性能样本 fresh session 执行完整 prefix 后 close/destroy。分别记录提交、物化、报告与消费者端到端成本；OFF 完整比较/详细诊断记 not_run。默认预热 5 次、采样 30 次，短 smoke 明示，不能代替 Stage 12 性能门。

诊断 validator 按图建立保序索引，完整数组结构只在其边界校验一次；独立 oracle 的计算仍分开执行，不能用目标结果的 winner 限制候选集合。

当前协议以对应 serializer/controller 为准。Stage 11 已移除旧 Stage 3 authorization/coordinator、整库 candidate/carrier 和重复 receipt 路径；不为历史内部 API 保留兼容壳。

## Stage 12 局部候选与并行边界

候选选择不依赖 full/mixed 的全局访问顺序。每个结果 lane 先取数值极值，再从原 epsilon 窗中依次按 seed、入边行内序号、输入 transition 选取实际候选；保留其实际数值、winner、前驱和路径身份。不新增全图 ID/排序表，native oracle 保持独立计算。必要的数值和边界拒绝始终保留。

并行计算按层、同层节点单写入者。同 stream 的阶段边界保护 clock/data 弧状态及 endpoint 覆写；节点内保持候选选择规则。共享错误必须原子归并，可由线程局部 status 复用同步 helper 后统一上报，不能因早退漏报；并发多错不承诺串行首错顺序。ON 访问计数也须无竞争，OFF 编译剔除。实际 launch、同步、传输与分配另作运行剖析，不能用源码或固定计数断言代替。

当前 CUDA full trace/verdict 为 v4、targeted/incremental 为 v5，consumer raw 为 v2；访问审计按四阶段各保存 BaseOut/AuxOut/BaseIn，完整比较仅 ON。显式 kernel launch 与 CUB 执行调用分别记录；CUB 内部实际 launch 由运行剖析核对，不把一次算法调用当作一个 kernel。full Kahn 的设备决策回传单列，传播层间不得加入 host 等待。普通 OFF 四模式实验使用 samples v2、每个 fresh process 的完整 trace 配对，默认预热 5、采样 30，正确性及详细诊断为 not_run。

回归构建必须包含 controller 命令参数中间接调用的 probe。binding 按实际路径和只读构建状态验明；sanitizer 与 Release 若第三方库输出共用源码目录，须隔离该输出，不能仅分开 CMake build 目录。

必要的 capture 字段检查应按当批稳定身份建立局部查找索引，避免每条记录重扫完整集合。索引可借用当前调用期间只读的 records/plan，不能跨 apply、扩容或提交持有指针；完整请求与旧值核对仍须执行。此类查找顺序不得改变传播候选或 descriptor 输出顺序。 已维护且仍适用的稳定身份直接复用，不为每条弧重新扫描同源邻接；native 槽位复用时，必须在更新后的投影前完成 stable ref 重绑，并保留当前图的其余 key 字段及边界检查。

## Stage 13 RC 与生产接入

树形 RC 只在 CPU 准备拓扑、负载和结构归约；实时驱动电阻、极点、residue、有效电容、延迟及 slew 在所选 backend 求值，不把 native timing 答案当作 CUDA 输入。保持原生单位、表格 raw-load 语义、阈值与 fallback；无寄生的 ceil 规则不随之改动。

单个 driver 的候选求值和缓存更新必须有唯一写入者，各 sink 只读已完成的 driver 结果。数值失败不能发布部分结果或旧结果；诊断开关不能控制必要边界、数值和失败处理。完整 native 对照仅在开发诊断运行。新增 RC 支持须经过独立 native 和真实物理批次验收后才解除 unsupported。

共享 RC 结构按 net 持有不可变 owner，旧 owner 必须活到 pending/undo 使用结束；同负载 lane 可以共享归约。Q 没有出弧时，顺序 seed 仍须持有计算需要的模型。不要按 table 内容等价合并 native child/cache 身份；局部 expected 检查优先使用同一 owner，独立完整值证明仅在验收运行。

propagated clock 的 effective state 必须来自当前 physical 传播结果；ideal 语义不变。SDC 名单先完整验证再修改，不静默忽略命令。测试同时检查实际支持标志及非零时钟值，防止目标和 oracle 同时落到 ideal 仍比较通过。scalar RAT 与报告路径 CRPR 使用各自既有调用口径，不能重复加修正。

RC 求值中的“模型不可用”与非有限数值失败必须分开。native 允许继续下一模型或普通 NLDM 的情况须保留其 fallback；非有限输入或结果不能通过 fallback 隐藏。普通 NLDM 的负载沿用 native DFS 子树累加值，不能因数学等价改用不同求和顺序的 Arnoldi total-capacitance，ceil 换算会放大舍入差异。driver 缓存只在真实 miss 完成后发布，hit 不改变 last-miss 选择；Instance CTQ 副本与 Liberty graph child 不能按表内容合并身份。

输入端口 RC 使用实际 TimingLibrary 的全局五个阈值，按 reference payload 保存一份。net 初始化跳过尚未建立的 driver cache，动态求值依次使用完成的 driver、port 和 raw-tree fallback；无效数值不能当作零延迟。RC 初始化按 driver 内原生 cell ordinal 完成，不改 Arc 物理槽位或统一传播候选顺序。

CUDA RC 缓存是单份传播 scratch，每轮清空逻辑记录；graph child 每 analysis/output 最多五个不同 input slew，CTQ 独立域最多一个，不乘 path tag 或 fanout。driver owner 完成 slew 选择后发布各 family 的最后真实 miss，sink 只读完成记录；同值 table interning 不合并 native child 身份。变化的 RC owner 不进入永久追加的 Liberty pool，提交或撤销后释放/复用无 live 引用的版本。

RC 编辑复用局部 native/graph 撤销。prepared tree 在 apply 前校验完整 terminal、连通性与数值；撤销保存实际旧 map node 和共享 owner。负载变化必须刷新受影响 net 的全部 terminal、driver 与独立 Q seed，不只刷新移动 sink。设备 RC buffer、descriptor 和 owner 配对切换，上传/恢复排空 stream 后才释放旧对象；复用已有工作容量，不增加整图事务副本。

### 物理共同提交与恢复

- 恢复目录只由一个 owner 持锁。基线绑定真实输入文件内容、分析/构建配置、RC 层参数和 IDB 几何身份；每批仅保存稳定编辑、精确 DBU/朝向、实际执行模式与前后 generation。
- committed 文件的 no-replace rename 是提交点。它之前完成计算、记录写出及共同资格检查；之后只做既有无抛出提交与缓存代数更新，不插入查询物化。
- native 撤销要求 authority 仍有效。异常分支先在操作 guard 内结束事务并撤销，再根据提交标记、设备和日志健康状态 poison。普通创建文件失败且无残留可在成功撤销后重试。
- 显式恢复保持会话未开放状态，按原记录逐批重放，不重写已提交文件，不累计第二份历史前缀。恢复失败后的物理前缀不能充当新基线；再次恢复必须重新加载原 checkpoint。
- 文件原子改名覆盖 worker 失败；没有 fsync 时不宣称断电持久性。诊断读取、故障注入及恢复等价比较遵守原 ON 边界，实际恢复和必需身份检查保留在 OFF。

### Stage 13 生产接入维护

实验 TIMING_OPT 位于 CTS、基线合法化之后、routing 之前；普通流程的默认模式不变。重试自身产物失败时保留已提交 journal 和累计 greedy 预算；重跑上游时清除绑定旧 checkpoint 的后继历史。最终产物以当前 generation manifest 为唯一入口，routing 不得退回旧二进制 DB 或固定文件名。

生产 greedy 使用当前 RC、负载和 Liberty；继续以既有正 gain 规则选取，不新增以实际 WNS/TNS 退化撤销成功批次的策略。无正 gain、无合法位置及预算耗尽分别记录；没有真实 edits 的 baseline 不算增量验收。

仓内物理 probe 只负责加载、提交、查询与记录，独立 fresh 分支重新加载提交后的 DEF/netlist，并由 native CPU/full 重建 RC 和传播。完整比较、canary 与故障注入只属开发验收；输入身份使用分块摘要，不内嵌 Liberty/LEF 文件内容。usage 只保留使用步骤，运行结果放阶段报告和独立证据目录。

生产消费者只请求实际使用的数据。物理 greedy 通过现有查询的 summary_only 取得 generation 与 QOR；完整查询默认仍返回 timing/paths。摘要查询保留物化和报告准备，但不构造或跨 binding 传递未请求的完整返回对象。此选择不控制开发诊断。
