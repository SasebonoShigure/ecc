# Stage 8 实施与验收报告

截至 2026-09-09。用户明确授权 Stage 7–8 及生产 CUDA 集成。本阶段已完成实现、独立设计/代码审查和真实 GPU 验收；保留可审阅差异，未 commit/push。前置结果见 [Stage 7 报告](stage7-progress-report.md)，范围见 [详细计划](stage8-detailed-plan.md)。

## 实现与边界

生产 frozen trace 通过 `CudaTargetedTraceReplayer` 执行 `cuda/targeted-full-levelization`：native detached candidate 局部编辑生成 remove/change/reverse-change、append、payload/metadata patch，GPU 持久维护 Base∪Aux，每批重置 seed 后执行完整 GPU levelization/propagation，准备真实 native scatter，再联合发布。`cuda/incremental` 通用入口仍明确 unsupported，属于 Stage 9；本阶段没有提前宣称 mixed GPU levelization 已完成。

`CudaDualCsrSession` 是具体设备 owner。候选绑定真实 origin owner/session/generation；foreign、stale、重复发布和计算失败均被拒绝。共享 origin 生命周期防止悬空与 ABA。全部可抛准备在正式发布之前，device publish 成功后只做 noexcept scatter、metadata 和 owner 转移。首批 owner 保留 DB0，后续 owner 只保留上一代；失败恢复实际 native database，最终恢复 DB0，不保存每代数据库链。

每批 native 仍有一次完整 Database 事务隔离复制及 library-arc 指针重绑；Arc 显式 noexcept move 避免排列时复制 timing maps。canonical Arc 排列 O(E log E)，adjacency、stable rank、predecessor 重映也有全量表示成本。这些是正确事务/winner/load 顺序的成本，不能归为诊断或称为全程 O(D)。局部构造复用 GraphBuilder canonical helper、raw insertion 和 resolver 私有实现；不调用完整 GraphBuilder、CPU timing/FIFO 或 CPU Dual-CSR updater。

设备候选采用 D2D 隔离，保留 O(N+E+timing storage) 复制成本。H2D 为本批变化及 metadata；所有分配、传输和 launch 都计实际值。GPU 算法保持 Stage 7 的串行 kernel 配置；本次证明正确性和路径，不宣称获得加速。

## 检查归属与诊断输出

session/generation/high-water、局部 expected、双向 incidence/重复写、table/seed 域、容量/finite/cycle、CUDA API/sync、poison 和真实 rollback 始终保留。受控 scatter 从纯 `CsrTimingValues` 与真实 stable targets 准备，shape/presence/ID 检查融入实际消费循环，不伪造 reference identity。

ON 才生成 canonical input observation、完整 device readback、详细四 pass Aux visits、完整 timing projection/receipt、source isolation 和 fresh oracle。OFF 不分配这些观察对象，不调用 debugState，不生成完整功能 receipt。跨构建实际设备读回通过具体测试 friend 实现，仅链接测试程序；不改变 OFF debugState 拒绝，不增加生产开关。

新 process/controller schema 为 `ista-cuda-targeted-trace/1.0.0`、`ista-cuda-targeted-verdict/1.0.0` 和 `ista-cuda-targeted-performance/1.0.0`。Stage 5/6 既有 schema 不变。每个诊断 prefix 独立启动 targeted、CUDA/full、fresh CPU/full，比较所有功能 timing 字段及实际图；不同计算路径只共享机械编码。

性能 controller 只接受 Release/OFF，每样本仍完成加载和清理；输出 `correctness_comparison=not_run`。实际进程审计只见 build-info、一次预热和三次目标采样。ON 在采样前拒绝，仅启动 build-info。正式性能样本不启动 oracle、不产生 receipt。

## 初始化计量细化

实测整个加载阶段有 **两次完整 export、两次 pack**：既有 Stage 7 baseline 先建立分析后的 native DB 与合法 BaselineExecuted/authority；guard 内导出该 baseline，再构造 Stage 8 持久设备 owner。总计划没有要求整个加载只做一次，详细计划此前“一次”表述已修正，并于 2026-09-09 经独立设计审查 APPROVE。

`initialization.scope=persistent_device_session_only` 仅表示第二个设备生命周期的初始化；controller `process_ms` 包含完整加载、分析、逐批执行和清理。没有删减加载成本或宣称初始化最优。每批 full export/pack 为零的限制保持。

## 构建与实测

两套 CUDA 构建为子仓库 `build-incregpusta-cuda-on` / `build-incregpusta-cuda-off`，均为 Release，同一 pinned Nix/GCC 14.3、nvcc 12.8.93/cudart 12.8.90，RTX 4070 Laptop sm89。CUDA 与新 native target 严格警告构建通过，浮点收缩关闭。默认 CPU 构建为 `build-incregpusta-off`，未启 CUDA；实际 ldd 未引用 CUDA。配置和诊断开关事实由 native 只读状态报告，未升级依赖或工具链。

下表路径相对子仓库，各目录中的 `stage8-evidence/` 保存原始证据。

| 验收 | 实际结果与可读证据 |
|---|---|
| ON 设备、真实硬件错误及生产/父级消费者最终回归 | 13/13 通过；`build-incregpusta-cuda-on/stage8-evidence/final-core-trace-parent-tests.log`。包括 core、allocation/debug-context/stage-context 三种硬件错误、Stage 4 fresh/source isolation/empty/one-shot、两条 CUDA/full 和两条 targeted trace |
| Native targeted / scatter / CPU backend 默认回归 | 23/23 通过；`build-incregpusta-off/stage8-evidence/final-affected-tests.log`。连续 native 编辑、完整 fresh graph、双槽排序、指针生命周期、clock/disabled/stale 拒绝；CPU properties 和 scatter contract/atomicity/properties |
| session 与公开头补充 | 3 项通过、1 项按已有配置 Disabled；`build-incregpusta-off/stage8-evidence/final-session-tests.log`。`ista_incremental_session_test` 在默认 OFF 属诊断测试，未将其记为通过；实际默认会话另由 Python smoke/生产 trace 覆盖 |
| OFF 生产 trace 与实际恢复 | 两条性能 CTest 通过；`build-incregpusta-cuda-off/stage8-evidence/production-traces.log`。最终第二批实际错误后恢复并健康重放通过 `final-off-rollback.log/json` |
| ON/OFF 实际设备图与 timing | 同输入 generations 0/1/2 的 Base/Aux/offset/mapping/active/roots/ends 和完整 timing 逐字段一致；两目录 `cross-build.json`、ON `cross-build-verdict.json`、OFF `final-acceptance.json` |
| Aux overflow 与 omission | 自然容量溢出的边是唯一有限 endpoint 路径，下一批 reverse-change/Aux clear；四 pass 实际访问 Aux。test-only 将候选设备 mapping 真正 H2D 清空后重跑 GPU，得到 Cycle、不能发布，原 owner 全值/generation 保留，后续健康候选成功；ON `gpu-omission-test.log` |
| sanitizer | ON core/GPU omission 的 memcheck、initcheck 均 0 errors：`gpu-omission-memcheck.log` / `gpu-omission-initcheck.log`；OFF core `device-memcheck.log` 为 0 errors；真实生产第二批失败+重放 `sanitized-production-rollback.log` 为 0 errors |
| Python 生产路径 | 重编并分别保存 ON/OFF binding。ON CUDA、OFF CUDA、OFF CPU/full 的 diamond QOR/paths 全值一致；ON unsupported case-analysis 失败后健康运行两次，OFF no-device preflight 拒绝；OFF `final-acceptance.json` 和 `python-*.log`，ON `python-diamond-final.log` |
| 性能入口和坏值 canary | ON 只 build-info 即拒绝；OFF 只 warmup+3 目标 samples，无 oracle/receipt。真实子进程结果经 timing/device/missing-batch 破坏均被拒绝，旧 verdict 不复用；两目录 `controller-behavior-audit.json`、ON `controller-behavior-audit-fixed.log` |
| parent 非 PDK | 1677 passed、6 skipped、4 deselected、13 xfailed、2 dependency deprecation warnings；ON `parent-non-pdk.log` |
| lint / type / diff | 修改的 14 个 Python 文件 Ruff 通过；parent 所选 module/runner 等仍有 28 项 type diagnostics，controller 检查 exit 0 但既有 run_baseline.py:335 有 1 条警告；ON `changed-python-ruff.log`、`parent-type.log`、`controllers-type.log`。两仓 git diff --check 通过，不宣称全仓类型检查通过 |

## 实际调用、分配与传输剖析

OFF `stage8-evidence/targeted-call-profile/` 保存当前 probe hash、实际解析地址、GDB 脚本、调用栈、原始 workload 和 profile。断点命中真实 `cudaMalloc`、`cudaMemcpyAsync`、`cudaLaunchKernel`，后者按实际函数地址识别五个 kernel；未使用源码清单或固定返回计数证明执行路径。剖析中的耗时不是性能结果。

在 synthetic_two_batch 两批及清理区间：native prepare / graph-preserving candidate copy / GPU stage 各 2 次；全量 GraphBuilder、CSR export、input pack、CPU reference compute/FIFO、CPU Dual-CSR updater、Stage 7 full backend、debugState、完整 scatter diagnostic 均为 0。remove/change/reverse-change/levelize/propagate 各实际 launch 2 次。

| 批次 | H2D bytes | D2H bytes | D2D bytes | allocations | grown buffers | launches |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 2616 | 8220 | 10448 | 28 | 18 | 5 |
| 2 | 6096 | 13156 | 15064 | 30 | 18 | 5 |

真实 API 合计 58 次 malloc、82 次 memcpy，H2D/D2H/D2D 分别 8712/21376/25512 bytes，与 workload telemetry 精确一致。加载区间另有 44 次 malloc、4 次 compute kernel launch、2 次 export/pack；这些未冒充每批成本。完整证据范围限本机代表 trace，不外推所有电路性能。

## 实际失败、修复与审查

- 受控 scatter 初审发现 required presence/配对可能被忽略，补齐检查及 malformed/inactive predecessor 测试；第一次测试编译漏 include，补齐后通过。
- 设备审查发现双向 incidence/重复写、typed transfer/seed 域及候选 CUDA error 向真实 origin poison 传播的缺口，已修；共享 origin 同时解决 lifetime/ABA。
- 独立 CPU Dual oracle 首次未填 active-edge metadata，修正测试输入后才得到有效比较。新增 cell 数值用例误取 arc 0（实际为 net）导致 host SIGSEGV；GDB 定位后按 ArcKind 找到真实 cell。
- 硬件测试最初以 C++ 包含 split-toolkit CUDA header 失败，改独立 .cu，并补 test include。`cudaMalloc(total_device_bytes+1)` 在 WSL 共享内存下可成功，不能作为 OOM 成功证据；最终巨大实际分配请求返回 CUDA allocation error。
- 对活跃 stream 执行 cudaDeviceReset 后，WSL driver 在 cuMemcpyDtoHAsync 内崩溃；该实验保留为失败，不冒称应用 poison 通过。改用隔离 ON 进程实际非法设备地址 kernel→同步 IllegalAddress，验证 stage/debug 捕获 CUDA 错误、poison 原 owner 并拒绝 sibling。最终 `hardware-fixed-test.log` 4/4 通过，旧 `hardware-fault-gdb.log` 保留。
- Native canonical 排列审查发现 unbound fallback Arc 应保原 pin-list 次序；补保序及原生表示回归。该乱序 pin fixture 不在合法 CSR reference 域，测试未伪称它为 CUDA baseline。下游组合 clock net 编辑根据 baseline 不可变 clock ArcId 身份明确拒绝。
- 最初只有 CPU 删除 Aux 的 canary，最终补真实 GPU omission，上述二者分别记录，不以 CPU 注入代替 GPU 行为。
- 行为审计脚本初次捕错类型误用 ValueError，修正为实际 ControllerError；GDB 初次在被内联的 stub 上计数为零、参数寄存器取错，改为真实 cudaLaunchKernel 函数地址及 ABI 正确参数后，实际 API 与 telemetry 一致。失败日志与修复后日志保留。

独立设计审查、scatter 修复复审、device/native/runtime 各组审查及最终全阶段代码审查均已执行；最终无未修代码阻断。不是仅以性能 sample 成功代替正确性验收。

## 复现与证据保存

从 ecc 根使用 bare flake，固定 Linux PATH 避免 Windows PATH 经 p9 文件检查造成数分钟 CMake 延迟。`nix --extra-experimental-features nix-command --extra-experimental-features flakes develop --command cmake --build chipcompiler/thirdparty/ecc-tools/build-incregpusta-cuda-on --target ista_cuda_targeted_trace_probe ista_cuda_full_trace_probe ista_cuda_dual_csr_session_test ista_cuda_dual_csr_hardware_fault_test -j 3`；OFF 对应目录省去仅 ON 硬件故障 target。运行 CUDA 设置 `LD_LIBRARY_PATH=/usr/lib/wsl/lib`，Python 绑定使用实际 Python 3.11 和对应 build/python 包。

正常 ON controller 使用 `src/operation/iSTA/test/timing_dual_csr/cuda_targeted_trace_controller.py --probe <ON targeted probe> --full-probe <ON CUDA full probe> --trace <frozen trace> --run-root <output>`；OFF 使用 `--probe <OFF targeted probe> --performance --samples 3`，不传 oracle。`core --cross-build-output <file>` 仅用于开发验收。

WSL 重启清除了此前 `/tmp` 日志；Stage 7 和本阶段第一组历史结果当时真实执行，但临时日志当前不可读。当前报告引用的最终 Stage 8 证据均存 build/stage8-evidence，关键受影响回归已重跑。保留历史报告，不修改通用 README、用户 CLAUDE.md 修改或三份既有报告，不升级依赖，不 commit/push。

## ECC CI 实际设计补测边界

2026-09-09 补测 ecc-ci-designs 的 xtea（71 cells）、usb（803 cells）、zipdiv（1107 cells）：CPU ON/OFF 各两轮通过且 QOR/paths 一致；CUDA ON/OFF 均因 sequential/clock/timing-check/CRPR/conditional-arc 语义未支持而明确拒绝。这不是实际 CI 设计的 GPU 验收通过；此前小图结果只在已支持语义范围内成立。Stage 8 在这些设计上未执行 targeted 差分或性能测试。完整输入、结果与限制见 [CI 小设计补测报告](ci-design-smoke-report.md)。
