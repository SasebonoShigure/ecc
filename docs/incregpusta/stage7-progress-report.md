# Stage 7 实施与验收报告

截至 2026-09-08，Stage 7 已完成实际 CUDA full 生产入口、frozen trace 和阶段验收；Stage 8 尚未实现。Stage 0–6 清理的本地提交为 ecc `356fa09`、ecc-tools `4b0398753`，未 push。Stage 7 保留未提交差异。

## 实现与用户行为

`ISTA_ENABLE_CUDA` 默认 OFF，独立于默认 OFF 的 `ECC_INCREGPUSTA_DEBUG_CHECKS`。可选 `ista_cuda` target 提供真实设备 full levelization、dynamic/arrival/required/slack propagation、NLDM 查询和结果恢复。native `cuda/full` 与 Python `ECCToolsModule.run_timing` 已接通，能力从 native 构建读取，缺少构建或设备在创建输出/初始化 session 前明确拒绝。尚未实现的 CUDA incremental 继续明确拒绝。

主要文件和符号位于 ecc-tools 的 `source/module/timing_cuda`（编码、设备布局、kernel、运行时、解码），`interface/STAInterfaceCuda.cpp`（受控导出、计算、scatter 与报告），`StaExecutionContract` / `IncrementalStaSession`（模式及生命周期），`benchmark/dual_csr/CudaFullTraceReplayer`（每批 full 执行和真实 rollback）。这些路径相对于 `src/operation/iSTA`。parent 的 `sta_session.py`、`sta_mode.py`、module/runner 将 CUDA preflight 交给实际 native resolver。

Stage 7 每批完整导出、独立分配和全量 H2D，不复用 targeted device graph。`GraphBuilder::buildStructure` 与 `NativeCandidateExecutor::installAndPrepareGraph` 保留 canonical 安装/回滚但不执行 CPU timing；`TimingAnalyzer::analyzePropagatedTiming` 复用已计算结果。受控内部 scatter 共用 `publishComputedTimingResult`，公共任意输入 scatter 仍完整校验。故障处理先真实清理；cleanup failure、unsupported analysis、计算失败保持各自类型和 poison 行为。

ON 的独立 baseline/frozen-prefix controller 比较完整 timing、快照和报告，保存原始 JSON、日志；OFF 正式 trace 性能入口不产生功能 receipt，不启动 oracle，每个子进程仍加载、执行、清理。ON 在采样前拒绝，未执行的比较为 `not_run`。controller 复用运行目录时删除本轮预期输出，避免读旧 JSON 成功。

## 环境与实际范围

RTX 4070 Laptop GPU，8188 MiB，sm_89；SMI driver 610.43.02 / KMD 610.62，CUDA driver 13.3。锁定 nixpkgs `f4b140d5b253f5e2a1ff4e5506edbf8267724bde`，GCC 14.3.0，nvcc 12.8.93、cudart 12.8.90；未升级依赖、驱动或 lock。

独立 Release 构建：ecc-tools 下 `build-incregpusta-cuda-off` / `build-incregpusta-cuda-on`，均开启 CUDA，分别关闭/开启开发检查。有效 CXX Release 命令采用仓库设置的 `-O3 -Wall -Werror=return-type`，CUDA target 另有严格警告及 `-ffp-contract=off`；CUDA 使用 `-O3 -DNDEBUG --fmad=false -Xcompiler=-Wall,-Wextra,-Werror`。不要将 cache 中的 CXX `-DNDEBUG` 当成实际生效参数；诊断开关不依赖它。运行需 WSL driver 库 `/usr/lib/wsl/lib`；实际绑定为 Python 3.11，独立 ON/OFF 包保存在相应构建目录 `python/ecc_tools_bin`。

两个计算 kernel 当前各为 `<<<1,1>>>`，是确定性串行 GPU 正确性基线，不声称并行加速。D2H 时间包含状态回传和 host 同步等待，不是纯 copy 带宽。支持范围与当前 CSR backend 一致；CRPR/register/propagated clocks 等仍明确 unsupported。本轮没有强制 OOM 测试，不声称覆盖它。

## 验收证据

日志位于本机 `/tmp`，构建产物位于上述 ecc-tools 构建目录，均未纳入 Git。它们是本次实际运行证据，不能视为已发布的跨机器 artifact。

| 验收 | 结果与证据 |
|---|---|
| 最终 CUDA ON | `ista_cuda` 标签 5 项通过，包括核心逐字段差分、表、native baseline、两个 frozen trace；`/tmp/incregpusta-stage7-cuda-trace-finish-on-test.log` |
| 最终 CUDA OFF | 标签 3 项通过，核心及两个正式性能 trace；`/tmp/incregpusta-stage7-cuda-trace-finish-off-test.log` |
| 核心错误语义 | 空/不连通/inactive/unreachable、cycle、malformed、数值失败；新增 scalar/path/required/slack overflow 使用有效输入和字面失败分类，并在失败后健康调用 GPU |
| 实际第二批失败 | 首批 GPU 成功，第二批缺失 cell 被拒；精确恢复 baseline 后同一 authority 健康重放，两条 trace 均通过 |
| Sanitizer | OFF core memcheck、ON core initcheck、ON 两批 trace memcheck、ON 第二批失败/重试 memcheck 均 0 errors；`/tmp/incregpusta-stage7-cuda-{off-memcheck,on-initcheck,trace-memcheck,trace-rollback-memcheck}.log`；core initcheck 早于新增 overflow case，不宣称所有新增 case 都执行了 initcheck |
| 默认 CPU | 受影响 native 严格构建及 9 项 timing 合约/属性回归；`/tmp/incregpusta-current-cpu-off-{build,test}.log`；默认 mode 合约通过且无 CUDA 链接；未声称重新运行全部 native suite |
| 现有 CPU golden | chain/diamond 各三次 fresh process 通过；`/tmp/incregpusta-stage7-cpu-native-golden.log` |
| 真实 Python ON/OFF | chain/diamond 各重复两次；完整 QOR/path 等于独立 CPU 与跨构建结果；no-device 拒绝、真实 case_analysis unsupported/poison/close 后健康新 session；`/tmp/incregpusta-stage7-python-{real,off}-matrix.json` |
| wrapper 回归 | 360 passed；`/tmp/incregpusta-stage7-python-route-final-all-ecc.log`；fake native 合约不替代前述真实 binding 验证 |
| parent 非 PDK | 1677 passed、6 skipped、4 deselected、13 xfailed，2 条 deprecation warnings；`/tmp/incregpusta-stage7-parent-regression.log` |
| OFF 性能 subprocess audit | build-info、一次预热、三个样本，无 fresh 子进程/receipt，保留每批原始遥测与 rollback；`/tmp/incregpusta-stage7-cuda-trace-off-process-audit.json` |
| ON 性能拒绝及旧产物 canary | ON 仅 build-info 后拒绝；exit 0 但不写输出的 child 不能借旧 warmup 成功；`/tmp/incregpusta-stage7-cuda-trace-{on-rejection,stale-canary}.json` |
| Ruff / native 格式和差异 | 本轮修改 Python Ruff 通过；C++ 改动范围格式检查/修正，最终 ON/OFF probe 重建通过；`/tmp/incregpusta-stage7-final-python-lint.log` 与 `...cuda-trace-format-{on,off}-build.log` |
| 类型检查 | parent 所选文件仍失败：28 项 module/runner 诊断，`/tmp/incregpusta-stage7-final-parent-type.log`；controller 所选文件 exit 0，但既有 `run_baseline.py:335` 有 1 条 possibly-missing-attribute 警告，`/tmp/incregpusta-stage7-final-native-controller-type.log`；不宣称全仓通过 |

代表性调用剖析使用实际 OFF binary，非源码字符串门禁：

- `build-incregpusta-cuda-off/python-call-profile-fixed/verified-profile.json`：真实 Python baseline GPU compute 2 次；CPU compute/FIFO、native timing order、完整 scatter 诊断均 0，6 类断点解析成功。未剥符号重链接文件重新 strip 后 SHA256 与正式 OFF binding 相同，链接命令保留在该目录。
- `build-incregpusta-cuda-off/cuda-trace-call-profile/`：11 个地址解析成功，无 pending；GPU compute 3 次（baseline 1 + 两批 2），CPU compute/FIFO/native order/full scatter 诊断 0。两批 generation 0→1→2，实际各 2 launches、20 allocations，H2D 10212/15812 bytes，D2H 7900/12060 bytes，rollback 成功、fallback 0。GDB 耗时不作为性能样本。

正式原始性能样本在 OFF 构建的 `src/operation/iSTA/test/cuda-full-traces/{synthetic_two_batch,real_buffer_fanout}/performance.json`。每个样本执行两批 full GPU，并包括加载/清理；没有从微型 case 推断速度收益。

独立设计审查和最终独立代码审查已通过；最终 reviewer 未参与实现，并额外执行上述 OFF trace 剖析。检查范围、未运行项和局限保留在此，不以成功性能样本替代正确性。

## 实际失败与修复

先前 snapshot helper 暗含 CPU FIFO，改为直接导出及受控 scatter 后，真实调用剖析确认删除。native 缺失 TimingSemanticKey/Arc include 和构建状态常量误名已修复；旧测试无条件拒绝 CUDA/full，改为验证实际能力和仍未支持的 incremental。系统 Python 3.12 配合 3.11 PYTHONHOME 的失败改为明确 3.11；相对输出误入 fixture 目录改为绝对路径，生成物移到构建目录保存。rollback 输入缺少 operator== 改用 canonical bytes 与身份比较。复用目录旧结果 canary 揭示 controller 缺陷，现已修复。首次 GDB 符号 namespace 错误、debugger 自身 PYTHONHOME 错配均保留失败日志，修正后重新得到有实际断点的证据。类型失败如上，未扩大改动至无关接口。

自动审批此前认为 Stage 7–8 超出可见授权并拒绝生产集成；被拒操作未执行。用户随后明确授权包括生产 CUDA 路径，当前无该授权阻塞。后续审批超时仅按工具允许重试，不作为测试失败或通过证据。

## 后续边界

Stage 8 先做独立设计审查，再实现设备 Base/Aux targeted 更新及生产 native 图局部编辑；不能把 Stage 7 全量导出/构建或 CPU Dual-CSR shadow 包装成 targeted。保留通用 README、用户 CLAUDE 改动和三份用户报告，不 commit/push。

## Stage 8 收尾时的当前复验与证据说明

2026-09-09 已在 Stage 8 最终源码重编两套 CUDA binding/full probe。ON 两条 full trace、实际 Python ON/OFF CUDA 与 CPU/full diamond QOR/paths、unsupported 后健康运行、no-device 拒绝及相关默认 CPU/native/parent 回归重新验证，当前证据见 [Stage 8 报告](stage8-progress-report.md)。Stage 8 已完成独立验收，通用 cuda/incremental 仍属于 Stage 9。

期间 WSL 重启清除了旧 `/tmp` 日志，正文历史执行结果保留，但这些临时日志当前不能读取。Stage 8 的新日志与原始结果均保存在对应 build/stage8-evidence，不将不可读历史日志冒充当前附件。Stage 7 旧“未执行 OOM”是当时范围；Stage 8 已另做实际分配/异步 CUDA 错误实验及 poison 验收，失败和修复完整记录在其报告。

## ECC CI 实际设计补测边界

2026-09-09 补测 ecc-ci-designs 的 xtea（71 cells）、usb（803 cells）、zipdiv（1107 cells）：CPU ON/OFF 各两轮通过且 QOR/paths 一致；CUDA ON/OFF 均因 sequential/clock/timing-check/CRPR/conditional-arc 语义未支持而明确拒绝。这不是实际 CI 设计的 GPU 验收通过；此前小图结果只在已支持语义范围内成立。Stage 8 在这些设计上未执行 targeted 差分或性能测试。完整输入、结果与限制见 [CI 小设计补测报告](ci-design-smoke-report.md)。
