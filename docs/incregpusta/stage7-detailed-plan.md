# Stage 7：CUDA full baseline 详细计划

状态：已完成实现、真实 ON/OFF GPU 验证及独立代码审查。实际结果、失败修复和限制见 [Stage 7 实施与验收报告](stage7-progress-report.md)。改动保留工作区差异，未 commit/push。以下保留经审查的详细设计，实际文件拆分与测量限制以报告为准。

## 范围与结构

新增独立 `source/module/timing_cuda`，公开 `CsrCudaBackend::computeWithTelemetry(const CsrReferenceInput&)` 返回现有 `CsrComputationResult` 与 CUDA 运行遥测。CPU 公共数据结构不含 CUDA 类型。独立 `ista_cuda` target 仅 `ISTA_ENABLE_CUDA=ON` 时启用 CUDA 语言、查找 toolkit 和链接 runtime；默认 CPU target 不新增 runtime 依赖。CPU 不可用构建继续明确拒绝 CUDA 请求，启用后的 native capability 和 Python preflight 读取同一个编译状态。能力检测不得把 cuda/incremental 提前报告为完成。

文件职责：`CsrCudaBackend.hpp` 定义入口与阶段遥测；`CsrCudaDeviceTypes.cuh` 是固定尺寸 POD 和扁平数组的私有设备布局；`CsrCudaPacking.cpp` 做已验证输入的编码和结果布局恢复；`CsrCudaRuntime.cu` 管理 buffer、stream、event、提交与同步；设备 arc/table、forward、required、levelization 实现在各自 cohesive 模块，不把任何文件从不足 700 行推过该阈值。`CMakeLists.txt` 和构建配置头传播只读能力。测试位于 iSTA test 的 CUDA 边界，生产 session 路由位于既有 native 执行边界。

## 数据流和语义

每次 full 调用重新验证外部输入的必要结构，完整编码并创建独立 device state，全量 H2D；不保存上一批 device 图。host 只做语义编码、seed/ideal-clock 初态和字符串 ID 映射，不调用 CPU levelization、arc transfer、forward 或 required propagation。允许复用 CPU 的 seed/result 初始化机械代码；它只初始化约束与空结果，不能计算 arc delay 或最终 timing。

设备保存节点/arc 稳定 ID、active mask、正反邻接、roots/starts/ends、完整 arc eligibility、output load、child sense/trigger/单位比例及 NLDM 表。表保留 absent/present-empty/0D/1D/2D 区别。节点输出、所有 clock/data-slew 字段、arc scalar/transition/IO/graph/child-cache 字段全部返回；path 使用 node × analysis × source × transition × clock-tag 的 checked dense storage，保留 presence、predecessor、launch、start、slew；输出按行和 tag 压缩。超出容量明确失败，不截断 tag。CPU 当前不支持的 CRPR/register/propagated-clock 等维持相同 unsupported 分类，不能静默丢弃。

GPU 完整 FIFO levelization 保留 roots 顺序和 outgoing 顺序；基线先用确定性设备 FIFO，避免 atomic ready queue 改变 winner。动态 slew 全图 pass 完成后，再运行 arrival/path 全图 pass，最后 endpoint required、逆向 required 与 slack。每个 level 的 sink 并行，sink 内按 source timing_order 和原 outgoing 顺序遍历候选；如果顺序证明尚未实现，先使用串行设备遍历作为正确性基线并在报告中明确实际并行度，不宣称加速。

精确复刻 CPU 顺序：scalar epsilon 1e-9，path/slew/graph epsilon 1e-6；first-winner 不用 atomic max/min 替代；path round 1e15；max 后 min 的 transition-type 覆盖；单位换算包含 ceil 与边界；CUDA 禁止 fast-math，使用 --fmad=false。对 finite、cycle、capacity、unsupported 和 view failure 始终检查。独立 ON oracle 不能与 GPU 共享实际计算。

## 生命周期与生产路由

full frozen trace 每批从 canonical native edit 安装后的对象完整导出 CSR，运行 GPU，再 scatter。将 `NativeCandidateExecutor` 的 canonical 安装/准备与现有 CPU 四阶段执行拆成受控入口，保持 `InstalledNativeDatabase` RAII 与实际失败回滚。不得先调用整个 CPU DualCsrTraceReplayer 再附加 GPU 结果。初始化与每批执行继续验证 owner/session/generation；成功同步、必要 D2H 和 scatter 前不发布 generation。CUDA runtime 错误携带实际调用与错误文本；异步错误同步后使失败状态不可继续使用，释放 staged buffers，旧状态或明确 poisoned 状态保留。

Python 入口和 native execution contract 必须同步支持实际已实现的模式；默认 cpu/full/error 不变，CUDA 未编译/设备不可用为明确错误。无 mutation 的 incremental 请求保留 baselineOnly 的诚实语义，Stage 8 前不能声称 device targeted 已执行。

## 遥测与检查归属

同步端到端 steady clock 覆盖编码、分配、传输、kernels、D2H 与结果恢复；CUDA events 分别计量 H2D、levelization、propagation、D2H；记录实际 bytes、allocation、launch、device/driver/runtime 和 requested/executed mode。full 每批 trace 必须证明完整 export/H2D。详细诊断与图 decode 仅 ECC_INCREGPUSTA_DEBUG_CHECKS=ON；正式性能入口 ON 采样前拒绝。没有执行的证明标记 not_run。

## 验收、失败记录和回滚

独立 Release/OFF 与 Release/ON 构建，相同 GCC 14.3 与锁定依赖。真实设备 RTX 4070 Laptop GPU sm_89，锁定 nixpkgs 提供 CUDA 12.8.93；不改 lock、不升级驱动。已有 device preflight 成功仅证明环境，不是 Stage 7 验收。

分组测试：空图/chain/fork/reconvergence/disconnected/inactive；all active；多 clock-tag、max/min/rise/fall、epsilon-chain 和 parallel arc；nonunate/sense/trigger；空/退化/2D NLDM、单位 ceil、fallback cache；unreachable infinities、numeric overflow、cycle、malformed 与 unsupported。ON 对所有 result presence/value、predecessor、level/order 比较 CPU oracle，cold/warm 重复；frozen trace 每 prefix 独立 fresh cpu/full。compute-sanitizer memcheck/initcheck 覆盖实际 kernels。CPU native 严格构建、相关 parent 回归、改动文件 lint/type 与差异检查。正式 OFF smoke 只执行 GPU 目标，记录原始样本与加载/清理。失败保留日志和输入，修复后重复受影响检查。

设计由独立 subagent 审查后实现，代码由未参与实现的独立 reviewer 审查。若设备或语义验收未通过，标记 not verified；不以 mock、skip 或编译成功完成阶段。失败实现保持显式不可用并保留可审阅差异，不能自动退回 CPU 却标 cuda。Stage 7 完成后再对 Stage 8 详细方案独立审查。
