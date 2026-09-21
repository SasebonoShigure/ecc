# Stage 11 实施与验收记录

更新：2026-09-21。状态：功能、事务安全和默认路径剖析验收完成；按用户授权本地提交，未 push。既有类型检查失败单独记录。

基线：ECC `7cd666f`、ecc-tools `fec270b8a`。范围见[详细计划](stage11-detailed-plan.md)。本阶段保持既有 STA 语义与全图传播；Stage 12 并行 kernel 和显著加速门未执行。

## 实现

- canonical Database/Liberty、graph/index/resolver 使用局部 undo；full 重建移动旧派生图与 Net 缓存，保存修改的标量。提交预分配恢复记录并无抛出发布，成功释放 undo；失败、放弃及 poison 保留。
- 删除 CPU incremental baseline 自动 capture/FIFO、每批额外 native full、重复 active mask/levels、旧 Stage 3 授权链及整库 candidate/carrier。ExpectedBeforeBinding 在 apply/扩容前借用；Arc 槽位稳定，候选顺序只维护受影响邻接，历史每批追加一条。
- CUDA Runtime、stream/events、容量、上传区与工作缓冲按会话复用；不可变模型与实例负载分离。稀疏 seed、N×8 行和紧凑 tag payload 保留全部有效身份；扩容、全图传播、工作缓冲重置仍计真实成本。
- status、levels 与 timing 分离。提交不要求完整 host timing，查询按 generation 物化和复用；报告使用 `analyzePropagatedTiming()`。普通准备失败可重试，实际 CUDA/清理失败 poison，pending/poison 不返回旧结果。
- observation 仅 ON 显式读取构建，close 不补建；OFF 连关闭后的缓存入口也不接受诊断 handoff。Runner 每样本 fresh session、正常 close/destroy，不撤销成功提交。
- 协议同步迁移：Stage 5 process v4、Stage 6 process v5/verdict v4、Stage 4 source-bearing probe v3；CUDA process/full verdict/full performance v3、targeted verdict v3/performance v4、通用 OFF performance v3。提交、物化、报告及消费者端到端分别计时。

## 功能验收

服务器在隔离目录顺序构建 Release OFF/ON，使用相同 GCC 14.3、CUDA 12.8 和依赖；保存两份 binding，实际导入路径、SHA-256、CUDA/debug 只读属性均核验。默认无 CUDA binding 也核验为 CUDA=false/debug=false。服务器任务共用 512 GB 硬上限、swap=0，使用空闲 GPU 7；独立失败复跑和早期剖析使用空闲 GPU 4。

| 检查 | 实际结果 |
|---|---|
| 最新相关 iSTA CTest（group99） | OFF 157 通过，24 项开发诊断按配置未执行；ON 185 通过。故意设备错误 ON 4 项另行通过；OFF 不注册故障注入 |
| 默认无 CUDA（group100） | 34 项相关测试通过；真实 no-CUDA binding 核验通过 |
| CPU ASan+UBSan（group99） | 10 项事务、恢复、属性及生命周期测试通过；已有 logger ODR 冲突的精确抑制见下文 |
| full 中途失败补测（group105） | Release OFF/ON、ASan+UBSan 均通过；ON 在建图后和传播后抛错，恢复旧图/缓存/标量/原始身份，随后同批成功提交 |
| CUDA memcheck/initcheck（group99） | mixed、fallback 四次检查均为 0 errors；硬件故障用例不混入此结果 |
| Parent 回归 | `test/tools/ecc` 364 passed（group93）；其后没有修改 parent Python 行为 |

xtea、usb、zipdiv 沿用原 ICS55 post-synthesis、无 SPEF 输入与 Q/D 两批 frozen traces。group96 的完整值输出完成 42 组 OFF/ON 对照，全部一致。group100 汇总公开 QOR/paths：CPU incremental 的 full/mixed 分层路径 48 项、CUDA incremental 的 full/mixed 分层路径 48 项、真正 CUDA/full 完整重建 24 项，均与 group97 新运行的独立 fresh native CPU/full 完全一致。

这里的“targeted + full levelization”仍是增量图更新，不能记为 native CPU/full 或 CUDA/full。真正 CUDA/full 使用 `CudaFullTraceReplayer`；native CPU/full 使用独立 oracle。真实多批次、恢复后继续提交、winner/时序检查及 level 合法性分别由跨构建回放、恢复测试和 ON controller 验证。group107 最终六组 CPU mixed/fresh、六组 CUDA incremental/full/fresh 独立对照全部通过，每组均检查 prefix 1/2。CPU mixed 的 full-levelizer 与 fallback 均为零，各对照使用独立进程。

测试覆盖连续提交不查询、首次/重复查询、查询后编辑与扩容、完整报告、失败重试、malformed/stale/owner/unsupported/cycle/numeric、部分 patch 失败、放弃与真实 rollback、history 预分配失败，以及并行弧、epsilon、多 clock/tag、同模型不同负载和路径域增长。独立审查发现的 full 中途失败缺口已补测。

## 默认路径剖析

同一 xtea Q trace、两批、Release OFF，以基线和当前实现分别执行相同消费者请求。以下是调用栈、分配和 CUDA API 的实际观测，包含启动与初始加载；不是性能采样或 Stage 12 加速结论。

| 观测 | 基线 → 当前 |
|---|---|
| CPU：Database 复制调用栈下的分配次数 | 4,706,056 → 0 |
| CPU：批次执行内 GraphBuilder / native propagation 调用栈下的分配 | 61,398 / 59,996 → 0 / 0；正常 baseline 仍存在 |
| CPU：整个进程分配次数 | 55,510,699 → 47,910,252 |
| CUDA：Database 复制调用栈下的分配次数 | 2,385,349 → 0 |
| CUDA：cudaMalloc / stream create / event create | 106 / 4 / 32 → 61 / 1 / 8 |
| CUDA：两批总 D2D / H2D / D2H 字节 | 4,489,712 / 2,811,668 / 3,265,048 → 371,504 / 643,232 / 1,715,012 |
| CUDA：第二批 D2D | 1,931,800 → 4,256 字节；仍有必要 levels 和扩容迁移 |
| CUDA：heaptrack 峰值 heap | 968.29 → 967.67 MB；启动时 Liberty 解析仍占主要成本 |

CPU 数据使用冻结的实际可执行文件、原始 heaptrack allocation event 与 ELF 符号范围解析；数值是调用栈下的分配次数，不是函数调用次数。CUDA 数据来自 heaptrack 与 Nsight Systems。当前第二批仍有 9 次容量增长分配；当前 kernel launch / stream synchronize 从 16 / 18 增为 28 / 34，不掩盖这些剩余成本。propagation、full levelizer 和 CSR patch 仍存在单线程 kernel，交给 Stage 12。

额外 Nsight `--lazy-sequence` 记录了 baseline、连续三次不查询提交、首次/重复查询、再提交并查询：前三代只出现 status/count/levels 回传；timing payload 与完整 order 在第一次查询才回传，重复查询无传输/重传播，新 generation 重新回传。模型复用、不同负载独立结果、实际分配与扩容由对应运行测试补充验证。

OFF smoke 产生原始 warmup/sample，结果不含完整诊断 receipt，不运行对照 oracle；ON 性能入口在 build-info 检查处拒绝，目录中没有 warmup/sample 子进程产物。默认预热 5/采样 30；本轮短 smoke 明示，不作为 Stage 12 性能验收。

## 实际失败与修复

- 独立审查修复了 replay baseline 绑定遗漏、真实恢复入口迁移遗漏、OFF order 多余 D2H、受控 export→CUDA 重复全检。保留 exporter 必要输入检查；mixed 尺寸检查改为读取必要状态，不依赖延迟的 host order。
- snapshot binding 测试仍假设 OFF 有 observation，并在解释器销毁后格式化 Python 异常；已修正 fixture、双模式预期和异常生命周期。另补 OFF closed observation 防线。
- 真设计 reference replay 的 generation-zero anchor 曾因 caps 的两种合法排序拒绝；改为按唯一 NodeId 比较完整记录，保留值、缺项、重复项 canary；其他有序字段不放宽。
- ON winner 验证器反复扫描全图与完整延迟 SoA，usb 第一批诊断持续超过十分钟。改为保序全局 arc 入弧索引、循环前一次 SoA 全检；独立 targeted/fresh 候选计算保留，交错 sink、graph 优先、IO 回退及非法 presence canary 通过。旧运行中止并保留原始结果，使用 group107 重跑全部通过。
- 最初 sanitizer Release/O3 构建触发 GCC14 STL array-bounds 的 Werror；改用独立 Debug ASan+UBSan。Nix Fortify 与 O0 不兼容，只在此 sanitizer 配置移除 Fortify。启动时又遇 `libidb.so/libtcl.so` 既有 `_log_instance` 重复全局；仅按该符号抑制 ODR，保留 leak detection、其余 ASan/UBSan 检查，不宣称无条件首次通过。
- CPU heaptrack 完整符号解析触及共同 cgroup 上限被杀；停止另一份同类解析，改用有 64 GB 子上限的流式原始事件解析。服务器共同上限始终生效。早期解析使用了后续重建的 binary，结果作废；最终 group103 冻结 binary 后重新采集与解析。CUDA heaptrack 的进程结束未释放量为 76.20→76.50 MB，未据此宣称全进程无泄漏。
- group99 xtea Q 的一次 CUDA child 初始化报错，无成功结果；相同 binary 在空闲 GPU 4 的 group102 重跑通过，group107 同项也通过，不将首次失败抹去。
- 构建/验收准备中的缺失 include、旧测试 helper、漏构建 oracle、Python ABI/PYTHONHOME 和旧 schema 消费者问题已逐项修复并复跑；原日志保留。剖析启动器曾直接比较合法不同的 levels，修正为复用 controller 的 timing/level 分离入口。
- 本轮 28 个 Python 文件 Ruff 通过。Mypy 为 238 errors / 21 files：原 26 文件范围的 230 errors 与前次诊断一致；新增纳入检查的两个 winner 文件有 8 个错误，原版本逐项复验相同。此前原 24 文件基线为 232 errors；不宣称类型检查通过。全仓检查因既有 `rmst_wl copy` 非法包目录中止。首次收集 lint 文件误纳用户 overview 产物，随后按本轮修改源文件收敛，未修改这些产物。

独立审查覆盖 host 事务、设备/诊断边界、seed、消费者、恢复及模块结构。`CsrReferenceTransferContractTest.cpp` 与 `BufferTraceProductionFreshProbe.cpp` 仅因原有完整用例的必要断言略超 700 行，保留就近；其余本轮明显增长的模块已按职责拆分。

## 证据位置

本地：`chipcompiler/thirdparty/ecc-tools/build-stage11-work/20260917-160546/`。服务器：`/home/qianhan/code/stage11-20260917-160546/`；保留 baseline/current/sanitizer 隔离代码、版本清单、命令脚本、原始 JSON、日志与退出状态。

主要入口：`logs/group99-*`（构建/CTest/CUDA 检查）、`logs/group100-comparison.json`（42 组跨构建和公开结果）、`logs/group96-profiling/comparison.json`、`logs/group103-cpu-profiling/raw-native-stack-comparison-final.json`、`logs/group101-lazy-profile.json`（实际剖析）、`logs/group105-*`（full 故障门）、`logs/group107-*`（最终独立对照）、`logs/group110-final-audit.json`（最终源码与退出状态汇总）。失败、被中止及未执行项保留在各自原运行目录。
