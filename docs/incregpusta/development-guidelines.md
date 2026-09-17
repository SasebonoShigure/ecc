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

恢复只使用按已保存模式重放的路径。恢复结果转移所有权，不在发布前复制整份已完成状态；诊断 evidence 仅 ON 返回，不构成授权。预编辑 binding 保留实际 graph/index，resolver/identity 的比较副本仅 ON 存在。不要为证明复制次数增加返回固定值的 API。

ON 使用现有 `dual_csr_trace_controller.py` 或 `incremental_levelization_controller.py`，以 `--probe <ON probe> --trace <trace> --run-root <existing directory> --timeout-seconds 900` 保存独立 targeted/fresh 结果和日志。旧诊断 timing smoke 已删除；重复性能采样使用 OFF smoke，构建信息只从 native `build-info` 获取。

Stage 6 每批只输出一份 canonical graph/timing，process 为 `ista-stage6-trace-process/3.0.0`，verdict 为 `ista-stage6-differential-verdict/2.0.0`。值等价与 level 合法性读取同一对象；它们证明不同性质，应同时保留。共享 JSON 编码不得变成共享 oracle 计算。

## Stage 7 CUDA 路径

`ISTA_ENABLE_CUDA` 默认 OFF；启用 CUDA 不自动开启诊断。native 只读 `incregpusta_cuda_enabled` 与 `incregpusta_debug_checks_enabled` 是 Python preflight 和 probe 的构建事实来源。缺设备、unsupported 分析、数值/cycle/capacity、CUDA status/sync、owner/session/generation、真实 rollback 和 cleanup 始终检查。受控 scatter 可复用已验证计算结果，外部任意结果继续完整验证。

ON 使用 `baseline/run_cuda_baseline.py` 和 `timing_dual_csr/cuda_full_trace_controller.py` 独立 fresh CPU 对照；正式 OFF controller 只运行目标 workload，不能生成 full receipt。原始 H2D/D2H/D2D bytes、分配、launch 和同步耗时属于性能事实，始终保存。详细观察/逐字段比较/source isolation 仅 ON。每轮必须防止旧输出伪装当前成功。

Stage 7 full 每批完整导出和复制是功能成本；Stage 8 targeted 不得复用该全量路径并宣称局部更新。事务隔离所需 D2D 可以保留，但必须如实计量。GPU 计时报告写明实际并行度和同步区间，不能将串行 kernel 正确性等同于加速。

## Stage 8 targeted CUDA 路径

生产 frozen trace 使用 `cuda/targeted-full-levelization`，每批仅生成 native 局部 patch，设备维护 Base∪Aux 并完成 full GPU levelization/propagation。该 Stage 8 策略不同于下面 Stage 9 的 `cuda/incremental`，不得混写 actual strategy。

每批 session/generation、高水位、incidence/重复写、局部 expected、typed table/seed 边界、cycle/数值和 CUDA 状态必须检查。candidate D2D、native Database 事务复制、library pointer 重绑、canonical rank/predecessor 重映和真实 rollback 是功能成本；不可放进诊断条件。每批不得调用完整 GraphBuilder、CSR export/pack、CPU updater/timing/FIFO。

独立 native canonical export、实际 device readback/详细 Aux visits、完整 timing projection、逐 prefix targeted 对 CUDA/full 和 fresh CPU/full、恢复等价证明只在 ON controller。跨构建实际值验收可由单独测试程序通过具体 friend 读回设备；实现不得链接到生产 runtime，不改变 OFF 的 debugState 拒绝行为，也不增加运行期开关。

加载阶段先经过 Stage 7 baseline 生命周期，再建立持久 device session。两次初始化 export/pack 均是端到端 process_ms 的实际成本；`initialization.scope=persistent_device_session_only` 不代表整个加载。每批 telemetry 的 malloc/transfer/launch 必须对应真实 API 调用，详细访问证明不能成为提交授权。


## Stage 9 hybrid CUDA incremental

`cuda/incremental` frozen trace 每批复用 canonical CPU mixed builder/Kahn，随后用旧 level D2D、新节点一次批量 H2D 和 GPU node2level 重建，再执行全图 GPU forward/backward propagation。endpoint binding 必须维护真实 levelization eligibility 和 BaseOut/AuxOut 归属；禁止构造假 payload 或另存 CPU Dual-CSR/timing shadow。

内部上一代 levels 以引用借用；OFF 保留维度、范围、高水位、generation、roots、indegree、processed count、cycle 和 CUDA status 检查。受控 mixed graph 完整 proof 仅 builder 的 ON 位置负责，Kahn 仅证明自己生成的 result，不嵌套公共 graph validator。外部 previous/graph/replay 输入仍完整校验。ON 的 CPU reconstruction oracle 与独立 level 不变量检查不能移入正常性能路径。

GPU reconstruction 计时必须从 CPU build/Kahn/plan 完成后开始，报告 CPU build、Kahn、plan、GPU reconstruction、update、propagation、scatter、batch/process total。完整传播仍是功能成本；当前 propagation kernel 的串行实现不能被描述为已证实加速。

仅真实 old-level order conflict 支持显式 `full_with_record`。重试前释放失败的 detached device candidate，再针对同一健康 owner 执行 full；actual cycle、数值/容量及 CUDA 错误不得伪装 fallback 成功。详细 rejected attempt 只记录已实际发生的失败，默认 Error 拒绝后仍须允许健康批次。损坏 CUDA context 不复用，恢复验收在新的健康进程按实际 mixed 模式重放。

ON 使用 `cuda_targeted_trace_controller.py --strategy incremental` 保留逐 prefix 独立 CPU/full、CUDA/full、level 合法性、winner/source isolation 和恢复等价；OFF 同一入口加 `--performance`，先核验真实 build-info，再仅执行目标 workload。批次数必须绑定请求 trace，generation 连续；不能相信子进程自己缩减后的 prefix。通用 Python session 的未编辑初始化如实记录 baseline_only/full；通用 physical/greedy 集成仍属 Stage 11。

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

Stage 5/6 的每批 functional/structural 只由 published_observations 持有，transaction_receipt 单独保存提交与回滚证明。Stage 5 process v2、Stage 6 process v3、Stage 4 source-bearing probe v2 同步迁移消费者，不保留旧格式包装。生产身份与 OFF 性能格式不变。

大 JSON 直接写入输出流；来源规范化使用只读浅层视图。跨 prefix 只保留后续完整比较实际需要的 observations，及时释放已比较的 fresh、transaction 和来源对象。独立 oracle、事务隔离与真实恢复数据不能因节省内存而删除。
